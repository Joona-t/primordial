"""Tests for compaction_analysis.py — Phase 6, Plan 05.

Tests CI computation on known data, hypothesis tests on known
rejection/non-rejection scenarios, anchor comparisons, verdict
rendering, forbidden proxy audits, and cross-track summarization.

Target: at least 12 test functions covering all major components.
"""

import json
import math
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from compaction_analysis import (
    CompactionAnalysis,
    HypothesisResult,
    AnchorComparison,
    Verdict,
    ForbiddenProxyAudit,
    bootstrap_ci,
    clopper_pearson_ci,
    wilson_ci,
    select_ci,
    test_reachability_hypothesis as run_reachability_test,
    test_instruction_delta as run_instruction_delta_test,
    cross_reference_anchors,
    render_verdict,
    audit_forbidden_proxies,
    summarize_tracks,
    generate_report,
    _extract_metric,
    _compute_aggregate_metrics,
)


# ═══════════════════════════════════════════════════════════════════════
# CI TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestBootstrapCI:
    """Tests for bootstrap_ci."""

    def test_constant_values_narrow_interval(self):
        """Bootstrap on [0.5]*100 should produce narrow CI around 0.5."""
        values = [0.5] * 100
        lower, upper = bootstrap_ci(values, B=10000, seed=42)
        assert abs(lower - 0.5) < 0.01
        assert abs(upper - 0.5) < 0.01

    def test_spread_values_wider_interval(self):
        """Bootstrap on spread values should produce wider CI."""
        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        lower, upper = bootstrap_ci(values, B=10000, seed=42)
        assert lower < 0.5
        assert upper > 0.5
        assert lower >= 0.0
        assert upper <= 1.0

    def test_deterministic_with_seed(self):
        """Same seed should produce identical CIs."""
        values = [0.2, 0.4, 0.6, 0.8]
        ci1 = bootstrap_ci(values, seed=42)
        ci2 = bootstrap_ci(values, seed=42)
        assert ci1 == ci2

    def test_different_seeds_different_cis(self):
        """Different seeds produce different CIs (with high probability)."""
        # Use enough spread values that resampling variance is non-trivial
        values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        ci1 = bootstrap_ci(values, seed=42)
        ci2 = bootstrap_ci(values, seed=999)
        # With 10 spread values and different seeds, CIs should differ
        assert ci1[0] != ci2[0] or ci1[1] != ci2[1]

    def test_empty_raises(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            bootstrap_ci([])

    def test_single_value(self):
        """Single value should produce point CI."""
        lower, upper = bootstrap_ci([0.7], B=10000, seed=42)
        assert abs(lower - 0.7) < 1e-10
        assert abs(upper - 0.7) < 1e-10

    def test_ci_width_decreases_with_n(self):
        """CI width should decrease approximately as 1/sqrt(N)."""
        import numpy as np
        rng = np.random.default_rng(42)
        # N=10
        values_10 = rng.uniform(0.3, 0.7, size=10).tolist()
        lo10, hi10 = bootstrap_ci(values_10, seed=42)
        width_10 = hi10 - lo10

        # N=40 (4x sample)
        values_40 = values_10 + rng.uniform(0.3, 0.7, size=30).tolist()
        lo40, hi40 = bootstrap_ci(values_40, seed=42)
        width_40 = hi40 - lo40

        # Width should decrease (not necessarily by exactly sqrt(4)=2x, but should be narrower)
        assert width_40 < width_10


class TestClopperPearsonCI:
    """Tests for clopper_pearson_ci."""

    def test_zero_successes(self):
        """0/10 should give upper bound near 0.31."""
        lower, upper = clopper_pearson_ci(0, 10)
        assert lower == 0.0
        assert abs(upper - 0.3085) < 0.01  # Exact: ~0.3085

    def test_all_successes(self):
        """10/10 should give lower bound near 0.69."""
        lower, upper = clopper_pearson_ci(10, 10)
        assert abs(lower - 0.6915) < 0.01  # Exact: ~0.6915
        assert upper == 1.0

    def test_half_successes(self):
        """5/10 should be roughly symmetric around 0.5."""
        lower, upper = clopper_pearson_ci(5, 10)
        assert lower < 0.5
        assert upper > 0.5
        # Should be roughly symmetric
        assert abs((lower + upper) / 2 - 0.5) < 0.05

    def test_n_zero(self):
        """n=0 should give (0.0, 1.0)."""
        lower, upper = clopper_pearson_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0


class TestWilsonCI:
    """Tests for wilson_ci."""

    def test_zero_successes(self):
        """0/5 should give lower bound 0.0."""
        lower, upper = wilson_ci(0, 5)
        assert lower == 0.0
        assert upper > 0.0

    def test_all_successes(self):
        """5/5 should give upper bound 1.0."""
        lower, upper = wilson_ci(5, 5)
        assert lower < 1.0
        assert upper == 1.0

    def test_half_successes(self):
        """3/6 should be roughly centered on 0.5."""
        lower, upper = wilson_ci(3, 6)
        assert lower < 0.5
        assert upper > 0.5


class TestSelectCI:
    """Tests for select_ci method dispatch."""

    def test_all_ones_uses_clopper_pearson(self):
        """All 1.0 values should use Clopper-Pearson."""
        ci, method = select_ci([1.0, 1.0, 1.0])
        assert method == "clopper_pearson"
        assert ci[1] == 1.0

    def test_all_zeros_uses_clopper_pearson(self):
        """All 0.0 values should use Clopper-Pearson."""
        ci, method = select_ci([0.0, 0.0, 0.0])
        assert method == "clopper_pearson"
        assert ci[0] == 0.0

    def test_interior_large_n_uses_bootstrap(self):
        """Interior values with N>=10 should use bootstrap."""
        values = [0.5] * 15
        ci, method = select_ci(values)
        assert method == "bootstrap"

    def test_small_n_continuous(self):
        """Small N continuous values should use bootstrap_small_n."""
        values = [0.3, 0.5, 0.7]
        ci, method = select_ci(values)
        assert method == "bootstrap_small_n"

    def test_empty_returns_full_range(self):
        """Empty input should return (0, 1)."""
        ci, method = select_ci([])
        assert ci == (0.0, 1.0)
        assert method == "empty"


# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS TEST TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestReachabilityHypothesis:
    """Tests for test_reachability_hypothesis."""

    def _make_data(self, values, **kwargs):
        """Create trial dicts from metric values."""
        return [
            {"aggregate_metrics": {"structural_reachability": v, **kwargs}}
            for v in values
        ]

    def test_rejects_when_clearly_above(self):
        """Values clearly above threshold should reject H0."""
        data = self._make_data([0.7, 0.8, 0.6, 0.75, 0.65])
        result = run_reachability_test(data, threshold=0.5)
        assert result.reject_h0 == True
        assert result.p_value < 0.05
        assert result.effect_size_d > 0

    def test_fails_to_reject_when_below(self):
        """Values below threshold should fail to reject H0."""
        data = self._make_data([0.4, 0.5, 0.3, 0.45, 0.35])
        result = run_reachability_test(data, threshold=0.5)
        assert result.reject_h0 == False
        assert result.p_value > 0.05

    def test_single_sample_insufficient(self):
        """Single sample should be insufficient for test."""
        data = self._make_data([0.9])
        result = run_reachability_test(data, threshold=0.5)
        assert result.reject_h0 == False
        assert result.n == 1
        assert "Insufficient" in result.interpretation

    def test_effect_size_sign(self):
        """Effect size should be positive when mean > threshold."""
        data = self._make_data([0.7, 0.8, 0.9])
        result = run_reachability_test(data, threshold=0.5)
        assert result.effect_size_d > 0

    def test_effect_size_negative(self):
        """Effect size should be negative when mean < threshold."""
        data = self._make_data([0.2, 0.3, 0.1])
        result = run_reachability_test(data, threshold=0.5)
        assert result.effect_size_d < 0

    def test_custom_metric_key(self):
        """Should work with different metric keys."""
        data = [
            {"aggregate_metrics": {"artifact_id_survival": v}}
            for v in [0.7, 0.8, 0.9, 0.85]
        ]
        result = run_reachability_test(
            data, metric_key="artifact_id_survival", threshold=0.5
        )
        assert result.reject_h0 == True
        assert "artifact_id_survival" in result.test_name


class TestInstructionDelta:
    """Tests for test_instruction_delta."""

    def _make_data(self, values, provenance_aware=True):
        return [
            {"aggregate_metrics": {"artifact_id_survival": v}, "provenance_aware": provenance_aware}
            for v in values
        ]

    def test_significant_difference(self):
        """Large difference should be significant."""
        data_aware = self._make_data([0.8, 0.9, 0.85, 0.87, 0.92])
        data_default = self._make_data([0.3, 0.4, 0.35, 0.32, 0.38], provenance_aware=False)
        result = run_instruction_delta_test(data_aware, data_default)
        assert result.mean > 0  # delta is positive
        assert result.p_value < 0.05

    def test_no_difference(self):
        """Identical values should not be significant."""
        data_aware = self._make_data([0.5, 0.5, 0.5, 0.5, 0.5])
        data_default = self._make_data([0.5, 0.5, 0.5, 0.5, 0.5], provenance_aware=False)
        result = run_instruction_delta_test(data_aware, data_default)
        assert abs(result.mean) < 1e-10
        assert result.reject_h0 == False

    def test_bonferroni_correction(self):
        """Corrected p should be 3x raw p (capped at 1.0)."""
        data_aware = self._make_data([0.7, 0.8, 0.75, 0.72, 0.78])
        data_default = self._make_data([0.5, 0.6, 0.55, 0.52, 0.58], provenance_aware=False)
        result = run_instruction_delta_test(data_aware, data_default, n_comparisons=3)
        expected_corrected = min(result.p_value * 3, 1.0)
        assert abs(result.p_value_corrected - expected_corrected) < 1e-10

    def test_bonferroni_caps_at_one(self):
        """Corrected p should be capped at 1.0."""
        # Use identical data so raw p is near 1.0
        data_aware = self._make_data([0.5, 0.5, 0.5])
        data_default = self._make_data([0.5, 0.5, 0.5], provenance_aware=False)
        result = run_instruction_delta_test(data_aware, data_default)
        assert result.p_value_corrected <= 1.0

    def test_insufficient_data(self):
        """Single sample per group should be insufficient."""
        data_aware = self._make_data([0.8])
        data_default = self._make_data([0.3], provenance_aware=False)
        result = run_instruction_delta_test(data_aware, data_default)
        assert result.reject_h0 == False
        assert "Insufficient" in result.interpretation


# ═══════════════════════════════════════════════════════════════════════
# ANCHOR COMPARISON TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestAnchorComparison:
    """Tests for cross_reference_anchors."""

    def test_mockml_gap_non_negative(self):
        """Gap from MockLM ceiling should be non-negative."""
        metrics = {
            "structural_reachability": 0.7,
            "artifact_id_survival": 0.6,
            "semantic_fidelity": 0.5,
            "degraded_fraction": 0.1,
            "compression_ratio": 150.0,
        }
        result = cross_reference_anchors(metrics)
        assert result.mockml["gap_reachability"] >= 0
        assert result.mockml["gap_survival"] >= 0

    def test_mockml_gap_is_complement(self):
        """Gap should be 1.0 - measured."""
        metrics = {"structural_reachability": 0.3, "artifact_id_survival": 0.4}
        result = cross_reference_anchors(metrics)
        assert abs(result.mockml["gap_reachability"] - 0.7) < 1e-6
        assert abs(result.mockml["gap_survival"] - 0.6) < 1e-6

    def test_knowledge_objects_above_threshold(self):
        """Survival > 0.4 should beat Knowledge Objects."""
        metrics = {"structural_reachability": 0.6, "artifact_id_survival": 0.5}
        result = cross_reference_anchors(metrics)
        assert result.knowledge_objects["structured_beats_unstructured"] == True

    def test_knowledge_objects_below_threshold(self):
        """Survival < 0.4 should not beat Knowledge Objects."""
        metrics = {"structural_reachability": 0.3, "artifact_id_survival": 0.3}
        result = cross_reference_anchors(metrics)
        assert result.knowledge_objects["structured_beats_unstructured"] == False

    def test_overall_pass(self):
        """Both reach > 0.5 and survival > 0.4 should give pass."""
        metrics = {"structural_reachability": 0.7, "artifact_id_survival": 0.5}
        result = cross_reference_anchors(metrics)
        assert result.overall_verdict == "pass"

    def test_overall_partial(self):
        """Only one criterion met should give partial."""
        metrics = {"structural_reachability": 0.7, "artifact_id_survival": 0.3}
        result = cross_reference_anchors(metrics)
        assert result.overall_verdict == "partial"

    def test_overall_fail(self):
        """Neither criterion met should give fail."""
        metrics = {"structural_reachability": 0.3, "artifact_id_survival": 0.3}
        result = cross_reference_anchors(metrics)
        assert result.overall_verdict == "fail"

    def test_v1_simulated_loaded(self):
        """v1.0 simulated data should be loaded from compaction-report.json."""
        metrics = {"structural_reachability": 0.7, "artifact_id_survival": 0.5}
        result = cross_reference_anchors(metrics)
        # Should have v1_at_50pct_deletion if the file exists
        if result.v1_simulated.get("status") != "data_not_found":
            assert result.v1_simulated.get("v1_at_50pct_deletion") is not None


# ═══════════════════════════════════════════════════════════════════════
# VERDICT RENDERING TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestVerdictRendering:
    """Tests for render_verdict."""

    def test_pass_verdict(self):
        """Should render PASS when reachability > 0.5 with p < 0.05."""
        analysis = {
            "data_mode": "live",
            "hypothesis_tests": {
                "structural_reachability": {
                    "n": 30,
                    "mean": 0.75,
                    "p_value": 0.001,
                    "reject_h0": True,
                    "effect_size_d": 1.5,
                },
                "instruction_delta": {
                    "n": 15,
                    "mean": 0.2,
                    "p_value": 0.01,
                    "p_value_corrected": 0.03,
                    "reject_h0": True,
                    "effect_size_d": 0.8,
                },
            },
        }
        verdicts = render_verdict(analysis)
        assert verdicts["claim-compaction-survival"].verdict == "PASS"
        assert verdicts["claim-compaction-survival"].confidence_tag in ("HIGH", "MEDIUM")

    def test_partial_dry_run(self):
        """Should render PARTIAL for dry-run data."""
        analysis = {
            "data_mode": "dry-run",
            "hypothesis_tests": {
                "structural_reachability": {
                    "n": 6,
                    "mean": 0.25,
                    "p_value": 0.99,
                    "reject_h0": False,
                    "effect_size_d": -1.0,
                },
                "instruction_delta": {
                    "n": 3,
                    "mean": 0.0,
                    "p_value": 1.0,
                    "p_value_corrected": 1.0,
                    "reject_h0": False,
                    "effect_size_d": 0.0,
                },
            },
        }
        verdicts = render_verdict(analysis)
        assert verdicts["claim-compaction-survival"].verdict == "PARTIAL"
        assert "dry-run" in verdicts["claim-compaction-survival"].evidence[0].lower()

    def test_backtrack_verdict(self):
        """Should render BACKTRACK when all conditions fail."""
        analysis = {
            "data_mode": "live",
            "hypothesis_tests": {
                "structural_reachability": {
                    "n": 30,
                    "mean": 0.3,
                    "p_value": 0.95,
                    "reject_h0": False,
                    "effect_size_d": -1.0,
                },
                "instruction_delta": {
                    "n": 15,
                    "mean": -0.1,
                    "p_value": 0.9,
                    "p_value_corrected": 1.0,
                    "reject_h0": False,
                    "effect_size_d": -0.3,
                },
            },
            "track_c": {},  # No conditions exceed threshold
        }
        verdicts = render_verdict(analysis)
        assert verdicts["claim-compaction-survival"].verdict == "BACKTRACK"

    def test_partial_with_some_conditions_pass(self):
        """Should render PARTIAL when some Track C conditions exceed threshold."""
        analysis = {
            "data_mode": "live",
            "hypothesis_tests": {
                "structural_reachability": {
                    "n": 30,
                    "mean": 0.45,
                    "p_value": 0.3,
                    "reject_h0": False,
                    "effect_size_d": -0.3,
                },
                "instruction_delta": {
                    "n": 15,
                    "mean": 0.05,
                    "p_value": 0.2,
                    "p_value_corrected": 0.6,
                    "reject_h0": False,
                    "effect_size_d": 0.2,
                },
            },
            "track_c": {
                "per_condition": {
                    "cond_1": {"structural_reachability": {"mean": 0.6}},
                    "cond_2": {"structural_reachability": {"mean": 0.3}},
                },
            },
        }
        verdicts = render_verdict(analysis)
        assert verdicts["claim-compaction-survival"].verdict == "PARTIAL"

    def test_instruction_effect_pass(self):
        """Should render PASS for instruction effect when significant."""
        analysis = {
            "data_mode": "live",
            "hypothesis_tests": {
                "structural_reachability": {
                    "n": 30, "mean": 0.75, "p_value": 0.001,
                    "reject_h0": True, "effect_size_d": 1.5,
                },
                "instruction_delta": {
                    "n": 15, "mean": 0.2, "p_value": 0.01,
                    "p_value_corrected": 0.03, "reject_h0": True,
                    "effect_size_d": 0.8,
                },
            },
        }
        verdicts = render_verdict(analysis)
        assert verdicts["claim-instruction-effect"].verdict == "PASS"


# ═══════════════════════════════════════════════════════════════════════
# FORBIDDEN PROXY AUDIT TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestForbiddenProxyAudit:
    """Tests for audit_forbidden_proxies."""

    def test_dry_run_violates_simulated_only(self):
        """Dry-run data should violate fp-simulated-only."""
        data = [{"mode": "dry-run", "track": "A", "task_category": "coding",
                 "provenance_aware": False, "compaction_events": [{"event": 1}]}]
        audits = audit_forbidden_proxies(data)
        sim_audit = [a for a in audits if a.proxy_id == "fp-simulated-only"][0]
        assert sim_audit.status == "violated"

    def test_live_data_rejects_simulated_only(self):
        """Live data should reject fp-simulated-only."""
        data = [{"mode": "live", "track": "A", "task_category": "coding",
                 "provenance_aware": True, "compaction_events": [{"event": 1}]}]
        audits = audit_forbidden_proxies(data)
        sim_audit = [a for a in audits if a.proxy_id == "fp-simulated-only"][0]
        assert sim_audit.status == "rejected"

    def test_no_compaction_violates_short_tasks(self):
        """No compaction events should violate fp-short-tasks."""
        data = [{"mode": "live", "track": "A", "task_category": "coding",
                 "compaction_events": []}]
        audits = audit_forbidden_proxies(data)
        short_audit = [a for a in audits if a.proxy_id == "fp-short-tasks"][0]
        assert short_audit.status == "violated"

    def test_all_compaction_rejects_short_tasks(self):
        """All trials with compaction should reject fp-short-tasks."""
        data = [
            {"mode": "live", "track": "A", "task_category": "coding",
             "compaction_events": [{"event": 1}]},
            {"mode": "live", "track": "A", "task_category": "debugging",
             "compaction_events": [{"event": 1}]},
        ]
        audits = audit_forbidden_proxies(data)
        short_audit = [a for a in audits if a.proxy_id == "fp-short-tasks"][0]
        assert short_audit.status == "rejected"

    def test_cherry_picked_always_rejected(self):
        """fp-cherry-picked should always be rejected (all conditions reported)."""
        data = [
            {"track": "A", "task_category": "coding", "provenance_aware": False,
             "mode": "live", "compaction_events": []},
            {"track": "A", "task_category": "debugging", "provenance_aware": True,
             "mode": "live", "compaction_events": []},
        ]
        audits = audit_forbidden_proxies(data)
        cherry_audit = [a for a in audits if a.proxy_id == "fp-cherry-picked"][0]
        assert cherry_audit.status == "rejected"


# ═══════════════════════════════════════════════════════════════════════
# TRACK SUMMARY TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestTrackSummary:
    """Tests for summarize_tracks."""

    def _make_trial(self, track="A", mode="live", survival=0.5, reachability=0.6,
                    category="coding", compaction_events=1, provenance_aware=False):
        return {
            "track": track,
            "mode": mode,
            "task_category": category,
            "provenance_aware": provenance_aware,
            "aggregate_metrics": {
                "structural_reachability": reachability,
                "artifact_id_survival": survival,
                "semantic_fidelity": 0.4,
                "degraded_fraction": 0.1,
                "compression_ratio": 100.0,
            },
            "compaction_events": [{"event": i} for i in range(compaction_events)],
        }

    def test_track_a_only(self):
        """Should summarize Track A when only Track A data provided."""
        data_a = [self._make_trial() for _ in range(5)]
        result = summarize_tracks(data_a)
        assert result["track_a"]["n"] == 5
        assert result["track_b"]["status"] == "no_data"
        assert result["track_c"]["status"] == "no_data"

    def test_multi_track(self):
        """Should summarize all tracks when all provided."""
        data_a = [self._make_trial(track="A") for _ in range(5)]
        data_b = [self._make_trial(track="B") for _ in range(3)]
        data_c = [self._make_trial(track="C") for _ in range(4)]
        result = summarize_tracks(data_a, data_b, data_c)
        assert result["track_a"]["n"] == 5
        assert result["track_b"]["n"] == 3
        assert result["track_c"]["n"] == 4

    def test_compaction_events_counted(self):
        """Should count compaction events per trial."""
        data_a = [self._make_trial(compaction_events=2) for _ in range(3)]
        result = summarize_tracks(data_a)
        assert result["track_a"]["compaction_events"]["total"] == 6
        assert result["track_a"]["compaction_events"]["mean_per_trial"] == 2.0

    def test_cross_track_consistency(self):
        """Should check cross-track consistency when both A and B present."""
        data_a = [self._make_trial(track="A", reachability=0.7) for _ in range(5)]
        data_b = [self._make_trial(track="B", reachability=0.65) for _ in range(5)]
        result = summarize_tracks(data_a, data_b)
        consistency = result["cross_track_consistency"]
        assert consistency["compatible"] == True  # gap = 0.05 < 0.2

    def test_data_mode_detection(self):
        """Should detect dry-run vs live mode."""
        data_dry = [self._make_trial(mode="dry-run") for _ in range(3)]
        result = summarize_tracks(data_dry)
        assert result["track_a"]["data_mode"] == "dry-run"

        data_live = [self._make_trial(mode="live") for _ in range(3)]
        result = summarize_tracks(data_live)
        assert result["track_a"]["data_mode"] == "live"


# ═══════════════════════════════════════════════════════════════════════
# FULL ANALYSIS INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════


class TestCompactionAnalysisIntegration:
    """Integration test using actual pilot data."""

    def test_loads_pilot_data(self):
        """Should load pilot JSONL data."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        assert len(analysis.all_data) >= 6

    def test_track_a_filter(self):
        """Should filter Track A data."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        track_a = analysis.load_track_data("A")
        assert len(track_a) == 6
        assert all(d["track"] == "A" for d in track_a)

    def test_full_analysis_runs(self):
        """Full analysis should run without errors on pilot data."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        results = analysis.run_full_analysis()

        # Required top-level keys
        assert "rq3b_verdict" in results
        assert "hypothesis_tests" in results
        assert "anchors" in results
        assert "verdicts" in results
        assert "forbidden_proxy_audit" in results
        assert "aggregate_metrics" in results

    def test_dry_run_verdict_is_partial(self):
        """Dry-run data should produce PARTIAL verdict."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        results = analysis.run_full_analysis()
        assert results["rq3b_verdict"] == "PARTIAL"
        assert results["data_mode"] == "dry-run"

    def test_json_serializable(self):
        """Full analysis results should be JSON-serializable."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        results = analysis.run_full_analysis()
        serialized = json.dumps(results, default=str)
        assert len(serialized) > 100  # Non-trivial output

    def test_report_generation(self):
        """Report generation should produce valid Markdown."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        results = analysis.run_full_analysis()
        report = generate_report(results)

        # Required sections
        assert "RQ3b" in report
        assert "MockLM" in report
        assert "Knowledge Objects" in report
        assert "v1.0 Simulated" in report
        assert "Track A" in report
        assert "Forbidden Proxy" in report
        assert "Limitations" in report
        assert "Recommendations" in report

    def test_all_three_anchors_present(self):
        """All three anchor comparisons must be present."""
        data_dir = Path(__file__).parent.parent / "data" / "compaction" / "genuine"
        if not (data_dir / "pilot-results.jsonl").exists():
            pytest.skip("Pilot data not available")
        analysis = CompactionAnalysis(data_dir=str(data_dir))
        results = analysis.run_full_analysis()
        anchors = results["anchors"]
        assert "mockml" in anchors
        assert "knowledge_objects" in anchors
        assert "v1_simulated" in anchors


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════


class TestHelpers:
    """Tests for helper functions."""

    def test_extract_metric(self):
        """Should extract metric values from trial dicts."""
        data = [
            {"aggregate_metrics": {"x": 0.5}},
            {"aggregate_metrics": {"x": 0.7}},
            {"aggregate_metrics": {"y": 0.9}},  # Missing x
        ]
        values = _extract_metric(data, "x")
        assert values == [0.5, 0.7]

    def test_compute_aggregate_metrics(self):
        """Should compute aggregate statistics."""
        data = [
            {"aggregate_metrics": {"structural_reachability": 0.6, "artifact_id_survival": 0.5}},
            {"aggregate_metrics": {"structural_reachability": 0.8, "artifact_id_survival": 0.7}},
        ]
        agg = _compute_aggregate_metrics(data)
        assert abs(agg["structural_reachability"] - 0.7) < 1e-6
        assert abs(agg["artifact_id_survival"] - 0.6) < 1e-6

    def test_compute_aggregate_empty(self):
        """Should return empty dict for empty data."""
        agg = _compute_aggregate_metrics([])
        assert agg == {}
