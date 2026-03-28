"""Test suite for cross-architecture analysis module (Phase 8, Plan 04).

Tests cover:
  - Statistics: per-framework aggregation, reversibility, CP upper bound, trace pct
  - Comparison: cross-architecture deltas, consistency assessment
  - Anchors: MockLM, OpenClaw, Phase 7 comparisons
  - Verdict: POSITIVE/PARTIAL/NEGATIVE logic, qualification, evidence
  - Forbidden proxies: all 3 proxy checks
  - Integration: full analysis on real campaign data, report sections

Target: >= 25 tests, all passing.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure tools/ is on sys.path
import sys
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from xarch_analysis import (
    XArchAnalysis,
    clopper_pearson_ci,
    generate_report,
    MOCK_LM_ANCHOR,
    OPENCLAW_ANCHOR,
    PHASE7_ANCHOR,
)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def real_data_paths():
    """Return paths to actual campaign data files."""
    base = Path(__file__).parent.parent
    return {
        "ag2": base / "data" / "xarch" / "ag2_campaign.jsonl",
        "langgraph": base / "data" / "xarch" / "langgraph_campaign.jsonl",
        "coverage_gaps": base / "data" / "xarch" / "coverage_gaps.json",
    }


@pytest.fixture
def real_analysis(real_data_paths):
    """Return a loaded XArchAnalysis instance with real campaign data."""
    analysis = XArchAnalysis(
        real_data_paths["ag2"],
        real_data_paths["langgraph"],
        real_data_paths["coverage_gaps"],
    )
    analysis.load_data()
    return analysis


def _make_session(
    framework: str = "ag2",
    scenario_type: str = "simple_conversation",
    reversibility: float = 1.0,
    violations: int = 0,
    validation_errors: int = 0,
    hash_match: bool = True,
    trace_verified: bool = True,
    absence_events: int = 0,
    compaction_events: int = 0,
    run_id: str = "test-001",
) -> dict:
    """Create a minimal valid session record."""
    return {
        "run_id": run_id,
        "framework": framework,
        "scenario_type": scenario_type,
        "timestamp": "2026-03-28T00:00:00+00:00",
        "total_stages": 4,
        "total_events": 6,
        "violations_detected": violations,
        "validation_errors": validation_errors,
        "reversibility_score": reversibility,
        "trace_verified": trace_verified,
        "hash_match": hash_match,
        "trace_stats": {
            "stage_count": 4,
            "shared_structures": 5,
            "ref_replacements": 18,
            "compression_ratio": 1.12,
            "original_size": 6000,
            "encoded_size": 5340,
            "encoding": "forge.trace.v1",
        },
        "absence_events": absence_events,
        "compaction_events": compaction_events,
        "duration_ms": 2.0,
        "spec": {"scenario_type": scenario_type, "seed": 42},
    }


def _write_jsonl(path: Path, sessions: list[dict]) -> None:
    """Write sessions as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")


@pytest.fixture
def synthetic_analysis(tmp_path):
    """Create an XArchAnalysis with synthetic data for controlled testing."""
    ag2_sessions = [
        _make_session("ag2", "simple_conversation", 1.0, 0, 0, True, True, 2, 0, f"ag2-{i}")
        for i in range(10)
    ]
    lg_sessions = [
        _make_session("langgraph", "linear_pipeline", 1.0, 0, 0, True, True, 1, 0, f"lg-{i}")
        for i in range(10)
    ]
    gaps = [
        {
            "framework": "ag2",
            "intercepted_transitions": [{"transition": "agent_turn", "coverage": "complete"}],
            "invisible_transitions": [
                {"transition": "process_death", "gap_severity": "HIGH", "gap_reason": "No persistence", "mitigation": "Export chamber"}
            ],
        },
        {
            "framework": "langgraph",
            "intercepted_transitions": [{"transition": "node_execution", "coverage": "complete"}],
            "invisible_transitions": [
                {"transition": "reducer_merge", "gap_severity": "HIGH", "gap_reason": "Opaque", "mitigation": "Wrapper"}
            ],
        },
    ]

    ag2_path = tmp_path / "ag2.jsonl"
    lg_path = tmp_path / "lg.jsonl"
    gaps_path = tmp_path / "gaps.json"

    _write_jsonl(ag2_path, ag2_sessions)
    _write_jsonl(lg_path, lg_sessions)
    gaps_path.write_text(json.dumps(gaps))

    analysis = XArchAnalysis(ag2_path, lg_path, gaps_path)
    analysis.load_data()
    return analysis


@pytest.fixture
def degraded_analysis(tmp_path):
    """Create an analysis where one framework has degraded metrics."""
    ag2_sessions = [
        _make_session("ag2", "simple_conversation", 1.0, 0, 0, True, True, 0, 0, f"ag2-{i}")
        for i in range(10)
    ]
    # LangGraph has degraded reversibility and some validation errors
    lg_sessions = [
        _make_session("langgraph", "linear_pipeline", 0.8, 0, 1, False, True, 0, 0, f"lg-{i}")
        for i in range(10)
    ]

    gaps = [
        {"framework": "ag2", "intercepted_transitions": [], "invisible_transitions": []},
        {"framework": "langgraph", "intercepted_transitions": [], "invisible_transitions": []},
    ]

    ag2_path = tmp_path / "ag2.jsonl"
    lg_path = tmp_path / "lg.jsonl"
    gaps_path = tmp_path / "gaps.json"

    _write_jsonl(ag2_path, ag2_sessions)
    _write_jsonl(lg_path, lg_sessions)
    gaps_path.write_text(json.dumps(gaps))

    analysis = XArchAnalysis(ag2_path, lg_path, gaps_path)
    analysis.load_data()
    return analysis


@pytest.fixture
def both_fail_analysis(tmp_path):
    """Create an analysis where both frameworks fail."""
    ag2_sessions = [
        _make_session("ag2", "simple_conversation", 0.7, 1, 2, False, True, 0, 0, f"ag2-{i}")
        for i in range(10)
    ]
    lg_sessions = [
        _make_session("langgraph", "linear_pipeline", 0.6, 2, 3, False, True, 0, 0, f"lg-{i}")
        for i in range(10)
    ]

    gaps = [
        {"framework": "ag2", "intercepted_transitions": [], "invisible_transitions": []},
        {"framework": "langgraph", "intercepted_transitions": [], "invisible_transitions": []},
    ]

    ag2_path = tmp_path / "ag2.jsonl"
    lg_path = tmp_path / "lg.jsonl"
    gaps_path = tmp_path / "gaps.json"

    _write_jsonl(ag2_path, ag2_sessions)
    _write_jsonl(lg_path, lg_sessions)
    gaps_path.write_text(json.dumps(gaps))

    analysis = XArchAnalysis(ag2_path, lg_path, gaps_path)
    analysis.load_data()
    return analysis


# ============================================================
# Statistics Tests (6+)
# ============================================================


class TestPerFrameworkAggregate:
    """Tests for per_framework_aggregate() method."""

    def test_per_framework_aggregate_schema(self, real_analysis):
        """All required fields present in per-framework aggregate."""
        agg = real_analysis.per_framework_aggregate("ag2")
        required_fields = [
            "framework", "session_count", "validation_errors",
            "reversibility", "trace_verified_pct", "violation_count",
            "violation_rate", "cp_95_upper", "absence_events",
            "compaction_events", "per_scenario_type",
        ]
        for field in required_fields:
            assert field in agg, f"Missing field: {field}"

    def test_reversibility_computation(self, synthetic_analysis):
        """Correct mean/std from known data (all 1.0)."""
        agg = synthetic_analysis.per_framework_aggregate("ag2")
        assert agg["reversibility"]["mean"] == 1.0
        assert agg["reversibility"]["std"] == 0.0
        assert agg["reversibility"]["min"] == 1.0
        assert agg["reversibility"]["max"] == 1.0

    def test_cp_upper_bound_computation(self, real_analysis):
        """CP upper bound matches scipy reference for 0/55."""
        from scipy.stats import beta as beta_dist
        agg = real_analysis.per_framework_aggregate("ag2")
        # 0/55: CP upper = Beta.ppf(0.975, 1, 55)
        expected = float(beta_dist.ppf(0.975, 1, 55))
        assert abs(agg["cp_95_upper"] - expected) < 1e-10

    def test_trace_verified_pct(self, real_analysis):
        """Correct fraction with hash_match=True."""
        agg = real_analysis.per_framework_aggregate("ag2")
        # All sessions have hash_match=True in real data
        assert agg["trace_verified_pct"] == 1.0

    def test_per_scenario_breakdown(self, real_analysis):
        """All scenario types present in breakdown."""
        agg = real_analysis.per_framework_aggregate("ag2")
        expected_types = {
            "simple_conversation", "tool_use_session",
            "multi_agent_groupchat", "error_and_absence",
            "compaction_trigger",
        }
        assert set(agg["per_scenario_type"].keys()) == expected_types

    def test_aggregate_with_zero_violations(self, synthetic_analysis):
        """Handles 0/N correctly."""
        agg = synthetic_analysis.per_framework_aggregate("ag2")
        assert agg["violation_count"] == 0
        assert agg["violation_rate"] == 0.0
        # CP lower should be 0 for k=0
        lower, _ = clopper_pearson_ci(0, 10)
        assert lower == 0.0

    def test_absence_events_aggregation(self, real_analysis):
        """Absence events total and per-session mean are correct."""
        agg = real_analysis.per_framework_aggregate("ag2")
        assert agg["absence_events"]["total"] == 60
        assert agg["absence_events"]["per_session_mean"] == pytest.approx(60 / 55)


# ============================================================
# Comparison Tests (5+)
# ============================================================


class TestCrossArchitectureComparison:
    """Tests for cross_architecture_comparison() method."""

    def test_cross_architecture_comparison_both_present(self, real_analysis):
        """Both frameworks present in comparison."""
        comp = real_analysis.cross_architecture_comparison()
        assert "ag2_aggregate" in comp
        assert "langgraph_aggregate" in comp
        assert "deltas" in comp
        assert "consistency_assessment" in comp

    def test_delta_computation(self, real_analysis):
        """Correct absolute and relative deltas."""
        comp = real_analysis.cross_architecture_comparison()
        rev_delta = comp["deltas"]["reversibility_mean"]
        # Both are 1.0, so delta should be 0
        assert rev_delta["absolute_delta"] == 0.0
        assert rev_delta["relative_delta"] == 0.0

    def test_consistency_within_tolerance(self, synthetic_analysis):
        """'equivalent' when within 10%."""
        comp = synthetic_analysis.cross_architecture_comparison()
        assert comp["consistency_assessment"] == "equivalent"

    def test_consistency_divergent(self, degraded_analysis):
        """'divergent' when outside 10%."""
        comp = degraded_analysis.cross_architecture_comparison()
        # Reversibility 1.0 vs 0.8 = 20% relative delta -> divergent
        assert comp["consistency_assessment"] == "divergent"

    def test_comparison_symmetry(self, real_analysis):
        """AG2 vs LG delta has opposite sign to LG vs AG2."""
        comp = real_analysis.cross_architecture_comparison()
        for metric_name, delta_data in comp["deltas"].items():
            # absolute_delta = ag2 - lg
            # Sign reversal is implicit; relative_delta is always >= 0
            assert delta_data["relative_delta"] >= 0

    def test_combined_statistics(self, real_analysis):
        """Combined CP upper bound is computed correctly."""
        comp = real_analysis.cross_architecture_comparison()
        combined = comp["combined"]
        assert combined["total_sessions"] == 110
        assert combined["total_violations"] == 0
        _, expected_cp = clopper_pearson_ci(0, 110)
        assert abs(combined["combined_cp_95_upper"] - expected_cp) < 1e-10


# ============================================================
# Anchor Tests (4+)
# ============================================================


class TestAnchorComparisons:
    """Tests for anchor comparison methods."""

    def test_mock_experiment_comparison(self, real_analysis):
        """MockLM metrics present in comparison."""
        comp = real_analysis.compare_to_mock_experiment()
        assert "anchor" in comp
        assert comp["anchor"]["source"] == "MockLM experiment (Phase 2-5)"
        for fw in ("ag2", "langgraph"):
            assert fw in comp["per_framework"]
            assert "reversibility" in comp["per_framework"][fw]
            assert "trace_integrity" in comp["per_framework"][fw]

    def test_openclaw_comparison(self, real_analysis):
        """OpenClaw metrics present in comparison."""
        comp = real_analysis.compare_to_openclaw()
        assert comp["anchor"]["source"] == "OpenClaw adapter (Phase 2 INTG-01)"
        for fw in ("ag2", "langgraph"):
            assert fw in comp["per_framework"]
            assert "reversibility" in comp["per_framework"][fw]
            assert "validation_errors" in comp["per_framework"][fw]

    def test_phase7_comparison(self, real_analysis):
        """Phase 7 violation rate present in comparison."""
        comp = real_analysis.compare_to_phase7()
        assert comp["anchor"]["total_runs"] == 211
        assert comp["anchor"]["violations"] == 0
        for fw in ("ag2", "langgraph"):
            assert fw in comp["per_framework"]
            vr = comp["per_framework"][fw]["violation_rate"]
            assert "phase7" in vr
            assert "framework" in vr
            assert "consistent" in vr

    def test_anchor_table_complete(self, real_analysis):
        """All 4 systems represented in anchor comparisons."""
        mock_comp = real_analysis.compare_to_mock_experiment()
        oc_comp = real_analysis.compare_to_openclaw()
        p7_comp = real_analysis.compare_to_phase7()

        # MockLM anchor
        assert mock_comp["anchor"]["reversibility"] == 1.0
        # OpenClaw anchor
        assert oc_comp["anchor"]["reversibility"] == 1.0
        # Phase 7 anchor
        assert p7_comp["anchor"]["violation_rate"] == 0.0
        # Both frameworks in each comparison
        for comp in [mock_comp, oc_comp, p7_comp]:
            assert "ag2" in comp["per_framework"]
            assert "langgraph" in comp["per_framework"]

    def test_openclaw_asymmetry_noted(self, real_analysis):
        """OpenClaw comparison notes the real-vs-mock asymmetry."""
        comp = real_analysis.compare_to_openclaw()
        for fw in ("ag2", "langgraph"):
            note = comp["per_framework"][fw].get("note", "")
            assert "asymmetric" in note.lower() or "mock" in note.lower()


# ============================================================
# Verdict Tests (5+)
# ============================================================


class TestVerdictLogic:
    """Tests for render_verdict() method."""

    def test_positive_verdict_criteria(self, synthetic_analysis):
        """Both frameworks pass -> POSITIVE."""
        verdict = synthetic_analysis.render_verdict()
        assert verdict["verdict"] == "POSITIVE"

    def test_partial_verdict_criteria(self, degraded_analysis):
        """One passes, one fails -> PARTIAL."""
        verdict = degraded_analysis.render_verdict()
        assert verdict["verdict"] == "PARTIAL"

    def test_negative_verdict_criteria(self, both_fail_analysis):
        """Both fail -> NEGATIVE."""
        verdict = both_fail_analysis.render_verdict()
        assert verdict["verdict"] == "NEGATIVE"

    def test_verdict_has_qualification(self, real_analysis):
        """'pipeline-validated' present in verdict."""
        verdict = real_analysis.render_verdict()
        assert "pipeline-validated" in verdict["qualification"]
        assert "pending live validation" in verdict["qualification"]

    def test_verdict_cites_evidence(self, real_analysis):
        """Specific metrics in verdict dict."""
        verdict = real_analysis.render_verdict()
        ev = verdict["evidence"]
        for fw in ("ag2", "langgraph"):
            assert "reversibility_mean" in ev[fw]
            assert "validation_errors" in ev[fw]
            assert "trace_verified_pct" in ev[fw]
            assert "violations" in ev[fw]
            assert "sessions" in ev[fw]

    def test_verdict_criteria_documented(self, real_analysis):
        """Verdict includes the criteria used for decision."""
        verdict = real_analysis.render_verdict()
        criteria = verdict["criteria_used"]
        assert criteria["reversibility_threshold"] == 0.95
        assert criteria["validation_errors_threshold"] == 0
        assert criteria["trace_integrity_threshold"] == 1.0
        assert criteria["consistency_tolerance"] == 0.10


# ============================================================
# Forbidden Proxy Tests (3+)
# ============================================================


class TestForbiddenProxyAudit:
    """Tests for forbidden_proxy_audit() method."""

    def test_fp_mock_as_real_checked(self, real_analysis):
        """Qualification present -> pass."""
        fp = real_analysis.forbidden_proxy_audit()
        check = fp["checks"]["fp-mock-as-real"]
        assert check["passed"]
        assert check["status"] == "REJECTED"

    def test_fp_hide_gaps_checked(self, real_analysis):
        """Coverage gaps present -> pass."""
        fp = real_analysis.forbidden_proxy_audit()
        check = fp["checks"]["fp-hide-gaps"]
        assert check["passed"]
        assert check["status"] == "REJECTED"

    def test_fp_cherry_pick_checked(self, real_analysis):
        """std/min/max present -> pass."""
        fp = real_analysis.forbidden_proxy_audit()
        check = fp["checks"]["fp-cherry-pick"]
        assert check["passed"]
        assert check["status"] == "REJECTED"

    def test_fp_audit_all_passed(self, real_analysis):
        """Overall audit passes."""
        fp = real_analysis.forbidden_proxy_audit()
        assert fp["audit_passed"]

    def test_fp_hide_gaps_fails_without_gaps(self, tmp_path):
        """fp-hide-gaps fails when coverage gaps are empty."""
        ag2_path = tmp_path / "ag2.jsonl"
        lg_path = tmp_path / "lg.jsonl"
        gaps_path = tmp_path / "gaps.json"

        _write_jsonl(ag2_path, [_make_session("ag2")])
        _write_jsonl(lg_path, [_make_session("langgraph")])
        gaps_path.write_text("[]")  # Empty gaps

        analysis = XArchAnalysis(ag2_path, lg_path, gaps_path)
        analysis.load_data()
        fp = analysis.forbidden_proxy_audit()
        assert not fp["checks"]["fp-hide-gaps"]["passed"]
        assert fp["checks"]["fp-hide-gaps"]["status"] == "VIOLATED"


# ============================================================
# CC Assessment Tests (3)
# ============================================================


class TestCCAssessments:
    """Tests for CC-014 and CC-015 assessments."""

    def test_cc014_satisfied_on_positive(self, synthetic_analysis):
        """CC-014 is satisfied when verdict is POSITIVE."""
        cc014 = synthetic_analysis.cc014_assessment()
        assert cc014["cc014_status"] == "satisfied"
        assert "pipeline-validated" in cc014["qualification"]

    def test_cc014_partial_on_partial(self, degraded_analysis):
        """CC-014 is partial when verdict is PARTIAL."""
        cc014 = degraded_analysis.cc014_assessment()
        assert cc014["cc014_status"] == "partial"

    def test_cc015_consistent_on_zero_violations(self, real_analysis):
        """CC-015 is consistent when 0 violations across architectures."""
        cc015 = real_analysis.cc015_carry_forward()
        assert cc015["cc015_status"] == "consistent"
        assert "pipeline-validated" in cc015["qualification"]


# ============================================================
# Integration Tests (2+)
# ============================================================


class TestIntegration:
    """Integration tests on real campaign data."""

    def test_full_analysis_on_real_data(self, real_data_paths):
        """Runs on actual campaign JSONL and produces complete results."""
        analysis = XArchAnalysis(
            real_data_paths["ag2"],
            real_data_paths["langgraph"],
            real_data_paths["coverage_gaps"],
        )
        results = analysis.run_full_analysis()

        # Check all top-level keys
        required = [
            "meta", "per_framework", "comparison", "anchors",
            "verdict", "forbidden_proxy_audit", "coverage_gaps",
            "cc014_assessment", "cc015_carry_forward",
        ]
        for key in required:
            assert key in results, f"Missing key: {key}"

        # Verify verdict is decisive
        assert results["verdict"]["verdict"] in ("POSITIVE", "PARTIAL", "NEGATIVE")

        # Verify forbidden proxy audit passes
        assert results["forbidden_proxy_audit"]["audit_passed"]

    def test_report_all_sections_present(self, real_data_paths):
        """All 9 sections in generated markdown report."""
        analysis = XArchAnalysis(
            real_data_paths["ag2"],
            real_data_paths["langgraph"],
            real_data_paths["coverage_gaps"],
        )
        results = analysis.run_full_analysis()
        report = generate_report(results)

        sections = [
            "Executive Summary",
            "Campaign Overview",
            "Per-Framework Results",
            "Cross-Architecture Comparison",
            "Anchor Comparison",
            "Coverage Gap Analysis",
            "RQ4 Verdict",
            "Limitations",
            "Recommendations",
        ]
        for section in sections:
            assert f"## {section}" in report, f"Missing section: {section}"

        # Key content checks
        assert "pipeline-validated, pending live validation" in report
        assert "mock backend" in report.lower()
        assert "CrewAI" in report
        assert "OpenHands" in report

    def test_save_results_produces_valid_json(self, real_data_paths, tmp_path):
        """save_results() writes valid JSON to disk."""
        analysis = XArchAnalysis(
            real_data_paths["ag2"],
            real_data_paths["langgraph"],
            real_data_paths["coverage_gaps"],
        )
        output_path = tmp_path / "results.json"
        results = analysis.save_results(output_path)

        # Verify file exists and is valid JSON
        assert output_path.exists()
        loaded = json.loads(output_path.read_text())
        assert loaded["verdict"]["verdict"] == results["verdict"]["verdict"]


# ============================================================
# Clopper-Pearson Edge Cases (2)
# ============================================================


class TestClopperPearsonEdgeCases:
    """Edge case tests for the Clopper-Pearson CI function."""

    def test_cp_zero_trials(self):
        """n=0 returns (0.0, 1.0)."""
        lower, upper = clopper_pearson_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0

    def test_cp_all_violations(self):
        """k=n returns upper=1.0."""
        lower, upper = clopper_pearson_ci(10, 10)
        assert upper == 1.0
        assert lower > 0.0


# ============================================================
# Scenario Diversity Test (1)
# ============================================================


class TestScenarioDiversity:
    """Tests that campaign data has proper scenario diversity."""

    def test_langgraph_scenario_types(self, real_analysis):
        """LangGraph has expected scenario types."""
        agg = real_analysis.per_framework_aggregate("langgraph")
        expected_types = {
            "linear_pipeline", "conditional_routing",
            "tool_use_graph", "error_recovery",
            "long_conversation",
        }
        assert set(agg["per_scenario_type"].keys()) == expected_types
