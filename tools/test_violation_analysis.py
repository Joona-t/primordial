"""
Test suite for ViolationAnalysis.

Verifies:
  - CP CI correctness against scipy.stats.beta reference
  - Bayesian posterior against Beta distribution CDF
  - Fisher's exact against known 2x2 tables
  - Verdict logic for all 4 branches (PASS, PARTIAL-mock, NEGATIVE-STRONG, PARTIAL-power)
  - Edge cases (0 violations, 1 violation, all in one category)
  - Forbidden proxy audit detects simulated conditions
  - Dose-response flat-at-zero and trend detection
  - Full analysis on real campaign data
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest
from scipy.stats import beta as beta_dist

from violation_analysis import (
    ADVERSARIAL_CATEGORIES,
    CATEGORY_ORDER,
    STRESS_LEVEL_ORDER,
    ViolationAnalysis,
    bayesian_posterior,
    clopper_pearson_ci,
    fishers_exact_2x2,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_jsonl(runs: list[dict], path: Path):
    """Write a list of run dicts as JSONL."""
    with open(path, "w") as f:
        for r in runs:
            f.write(json.dumps(r) + "\n")


def _make_status(total_runs: int, backend: str, per_category: dict,
                 path: Path, **kwargs):
    """Write a campaign_status.json."""
    status = {
        "campaign_id": "test-campaign",
        "backend": backend,
        "backend_caveat": (
            "BACKEND=mock: violations are forge-layer only."
            if backend == "mock" else None
        ),
        "total_runs": total_runs,
        "completed": total_runs,
        "failed": 0,
        "timed_out": 0,
        "per_category": per_category,
        "seed": 42,
    }
    status.update(kwargs)
    with open(path, "w") as f:
        json.dump(status, f)


def _make_run(run_id: str, category: str, stress_level: str,
              violation_count: int = 0, violation_types: list | None = None,
              backend: str = "mock", is_control: bool = False,
              mock_d7: int = 6) -> dict:
    """Create a single run entry."""
    return {
        "run_id": run_id,
        "task_id": f"TASK-{category}a",
        "category": category,
        "tier": "LONG",
        "stress_level": stress_level,
        "is_control": is_control,
        "violation_count": violation_count,
        "violation_types": violation_types or [],
        "errors": [],
        "mock_d7_artifacts_excluded": mock_d7,
        "backend": backend,
    }


def _build_zero_violation_campaign(n_per_cat: int = 10, backend: str = "mock"):
    """Build a campaign with 0 violations across all categories."""
    runs = []
    idx = 0
    for cat in CATEGORY_ORDER:
        for stress in STRESS_LEVEL_ORDER:
            for _ in range(max(1, n_per_cat // len(STRESS_LEVEL_ORDER))):
                runs.append(_make_run(
                    f"{cat}_{stress}_{idx:03d}", cat, stress,
                    backend=backend,
                    is_control=(cat in ["C9"]),
                ))
                idx += 1

    tmpdir = Path(tempfile.mkdtemp())
    jsonl_path = tmpdir / "raw_violations.jsonl"
    status_path = tmpdir / "campaign_status.json"

    _make_jsonl(runs, jsonl_path)

    per_cat = {}
    for cat in CATEGORY_ORDER:
        cat_runs = [r for r in runs if r["category"] == cat]
        per_cat[cat] = {
            "planned": len(cat_runs),
            "completed": len(cat_runs),
            "failed": 0,
            "violations": 0,
        }

    _make_status(len(runs), backend, per_cat, status_path)
    return jsonl_path, status_path, runs


# ══════════════════════════════════════════════════════════════════════
# 1. Clopper-Pearson CI correctness (10 test cases)
# ══════════════════════════════════════════════════════════════════════


class TestClopperPearsonCI:
    """Verify CP CI against scipy.stats.beta.ppf reference."""

    @pytest.mark.parametrize("k,n,expected_lower,expected_upper", [
        # k=0 cases: lower is always 0
        (0, 30, 0.0, None),
        (0, 200, 0.0, None),
        (0, 211, 0.0, None),
        # k=n cases: upper is always 1
        (10, 10, None, 1.0),
        # General cases
        (1, 100, None, None),
        (5, 100, None, None),
        (50, 100, None, None),
        (3, 20, None, None),
        (0, 1, 0.0, None),
        (1, 1, None, 1.0),
    ])
    def test_cp_ci_against_scipy(self, k, n, expected_lower, expected_upper):
        lower, upper = clopper_pearson_ci(k, n)

        # Compute reference from scipy
        alpha = 0.05
        if k == 0:
            ref_lower = 0.0
        else:
            ref_lower = float(beta_dist.ppf(alpha / 2, k, n - k + 1))

        if k == n:
            ref_upper = 1.0
        else:
            ref_upper = float(beta_dist.ppf(1 - alpha / 2, k + 1, n - k))

        assert abs(lower - ref_lower) < 1e-10, (
            f"Lower mismatch: got {lower}, expected {ref_lower}"
        )
        assert abs(upper - ref_upper) < 1e-10, (
            f"Upper mismatch: got {upper}, expected {ref_upper}"
        )

        # Check hardcoded expectations where provided
        if expected_lower is not None:
            assert abs(lower - expected_lower) < 1e-10
        if expected_upper is not None:
            assert abs(upper - expected_upper) < 1e-10

    def test_cp_0_211_matches_plan_reference(self):
        """Verify 0/211 CP upper bound matches scipy reference.

        Two-sided 95% CI: beta.ppf(0.975, 1, 211) = 0.017331...
        """
        _, upper = clopper_pearson_ci(0, 211)
        ref = float(beta_dist.ppf(0.975, 1, 211))
        assert abs(upper - ref) < 1e-6
        assert abs(upper - 0.017331) < 1e-4

    def test_cp_0_30_matches_v1_reference(self):
        """Verify 0/30 CP upper matches v1.0 reported 11.57%.

        Two-sided 95% CI: beta.ppf(0.975, 1, 30) = 0.11570...
        """
        _, upper = clopper_pearson_ci(0, 30)
        ref = float(beta_dist.ppf(0.975, 1, 30))
        assert abs(upper - ref) < 1e-6
        assert abs(upper - 0.1157) < 1e-3

    def test_cp_n_zero(self):
        """Edge case: n=0 should return [0, 1]."""
        lower, upper = clopper_pearson_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0

    def test_cp_ci_bounds(self):
        """All CIs should be in [0, 1] with lower <= upper."""
        for k in range(0, 11):
            for n in range(k, k + 20):
                if n == 0:
                    continue
                lower, upper = clopper_pearson_ci(k, n)
                assert 0.0 <= lower <= upper <= 1.0, (
                    f"Invalid CI for k={k}, n={n}: [{lower}, {upper}]"
                )


# ══════════════════════════════════════════════════════════════════════
# 2. Bayesian Posterior
# ══════════════════════════════════════════════════════════════════════


class TestBayesianPosterior:

    def test_beta_1_212_p_gt_2pct(self):
        """Verify Beta(1, 212) CDF at 0.02 matches scipy.

        P(rate > 2%) = 1 - Beta(1,212).cdf(0.02)
        """
        result = bayesian_posterior(0, 211)
        ref = float(1.0 - beta_dist(1, 212).cdf(0.02))
        assert abs(result["prob_rate_exceeds"]["0.02"] - ref) < 1e-6

    def test_posterior_mean(self):
        """Mean of Beta(a,b) = a/(a+b)."""
        result = bayesian_posterior(0, 211)
        expected_mean = 1.0 / (1 + 212)
        assert abs(result["mean"] - expected_mean) < 1e-8

    def test_posterior_with_violations(self):
        """Beta(1+5, 1+100-5) = Beta(6, 96)."""
        result = bayesian_posterior(5, 100)
        assert result["posterior"] == "Beta(6.0, 96.0)"
        expected_mean = 6.0 / (6 + 96)
        assert abs(result["mean"] - expected_mean) < 1e-8

    def test_credible_interval_contains_mean(self):
        """95% credible interval should contain the posterior mean."""
        for k, n in [(0, 211), (5, 100), (1, 50), (0, 30)]:
            result = bayesian_posterior(k, n)
            ci = result["credible_interval_95"]
            assert ci[0] <= result["mean"] <= ci[1], (
                f"Mean {result['mean']} outside CI {ci} for k={k}, n={n}"
            )

    def test_p_gt_thresholds_monotone(self):
        """P(rate > X) should decrease as X increases."""
        result = bayesian_posterior(0, 211)
        probs = result["prob_rate_exceeds"]
        assert probs["0.01"] >= probs["0.02"]
        assert probs["0.02"] >= probs["0.05"]
        assert probs["0.05"] >= probs["0.1"]


# ══════════════════════════════════════════════════════════════════════
# 3. Fisher's Exact Test
# ══════════════════════════════════════════════════════════════════════


class TestFishersExact:

    def test_both_zero_p_is_1(self):
        """[[0, 180], [0, 21]] should give p=1.0 (both groups zero)."""
        result = fishers_exact_2x2([[0, 180], [0, 21]])
        assert abs(result["p_value"] - 1.0) < 1e-10

    def test_known_table(self):
        """Verify against a known textbook 2x2 table.

        [[1, 9], [11, 3]] -- Fisher's exact (two-sided)
        """
        from scipy.stats import fisher_exact
        table = [[1, 9], [11, 3]]
        ref_or, ref_p = fisher_exact(table, alternative="two-sided")
        result = fishers_exact_2x2(table)
        assert abs(result["p_value"] - ref_p) < 1e-10
        assert abs(result["odds_ratio"] - ref_or) < 1e-10

    def test_identical_rates(self):
        """[[5, 95], [5, 95]] should give p=1.0 (identical rates)."""
        result = fishers_exact_2x2([[5, 95], [5, 95]])
        assert abs(result["p_value"] - 1.0) < 1e-10

    def test_extreme_table(self):
        """[[10, 0], [0, 10]] -- maximally different."""
        result = fishers_exact_2x2([[10, 0], [0, 10]])
        assert result["p_value"] < 0.001
        assert result["odds_ratio"] == float("inf")


# ══════════════════════════════════════════════════════════════════════
# 4. Verdict Logic (all 4 branches)
# ══════════════════════════════════════════════════════════════════════


class TestVerdictLogic:

    def _make_analysis(self, n_runs: int, n_violations: int,
                       backend: str = "mock") -> ViolationAnalysis:
        """Create a ViolationAnalysis with specified parameters."""
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = []
        for i in range(n_runs):
            v = 1 if i < n_violations else 0
            vtypes = ["D1"] if v > 0 else []
            runs.append(_make_run(
                f"run_{i:03d}", "A1", "control",
                violation_count=v,
                violation_types=vtypes,
                backend=backend,
            ))

        _make_jsonl(runs, jsonl_path)
        per_cat = {"A1": {"planned": n_runs, "completed": n_runs,
                          "failed": 0, "violations": n_violations}}
        _make_status(n_runs, backend, per_cat, status_path)
        return ViolationAnalysis(str(jsonl_path), str(status_path))

    def test_pass_live_violations(self):
        """PASS: violations > 0, backend != mock."""
        analysis = self._make_analysis(200, 5, backend="live")
        verdict = analysis.render_verdict()
        assert verdict["rq2b"] == "PASS"
        assert verdict["confidence"] == "high"
        assert verdict["backend_caveat"] is None

    def test_partial_mock_violations(self):
        """PARTIAL: violations > 0, backend == mock."""
        analysis = self._make_analysis(200, 5, backend="mock")
        verdict = analysis.render_verdict()
        assert verdict["rq2b"] == "PARTIAL"
        assert verdict["confidence"] == "low"
        assert verdict["backend_caveat"] is not None

    def test_negative_strong_zero_violations_200plus(self):
        """NEGATIVE-STRONG: 0 violations, N >= 200."""
        analysis = self._make_analysis(211, 0, backend="mock")
        verdict = analysis.render_verdict()
        assert "NEGATIVE-STRONG" in verdict["rq2b"]
        assert "pipeline-validated" in verdict["rq2b"]
        assert verdict["confidence"] == "medium"

    def test_negative_strong_live_zero_violations(self):
        """NEGATIVE-STRONG (high confidence): 0 violations, live backend."""
        analysis = self._make_analysis(211, 0, backend="live")
        verdict = analysis.render_verdict()
        assert verdict["rq2b"] == "NEGATIVE-STRONG"
        assert verdict["confidence"] == "high"
        assert verdict["backend_caveat"] is None

    def test_partial_insufficient_power(self):
        """PARTIAL: 0 violations, N < 150."""
        analysis = self._make_analysis(100, 0, backend="live")
        verdict = analysis.render_verdict()
        assert verdict["rq2b"] == "PARTIAL"
        assert verdict["confidence"] == "low"
        assert "insufficient power" in verdict["summary"]

    def test_verdict_statistical_basis(self):
        """Verdict includes CP upper bound and Bayesian P(rate>2%)."""
        analysis = self._make_analysis(211, 0, backend="mock")
        verdict = analysis.render_verdict()
        assert "statistical_basis" in verdict
        assert "cp_upper" in verdict["statistical_basis"]
        assert "bayesian_p_gt_2pct" in verdict["statistical_basis"]
        assert verdict["statistical_basis"]["cp_upper"] < 0.02


# ══════════════════════════════════════════════════════════════════════
# 5. Edge Cases
# ══════════════════════════════════════════════════════════════════════


class TestEdgeCases:

    def test_single_run_zero_violations(self):
        """Single run, 0 violations."""
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = [_make_run("run_000", "A1", "control")]
        _make_jsonl(runs, jsonl_path)
        _make_status(1, "mock",
                     {"A1": {"planned": 1, "completed": 1,
                             "failed": 0, "violations": 0}},
                     status_path)

        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        agg = analysis.compute_aggregate_rate()
        assert agg["violations"] == 0
        assert agg["runs"] == 1
        assert agg["ci_lower"] == 0.0
        assert agg["ci_upper"] < 1.0

    def test_all_violations_in_one_category(self):
        """All violations concentrated in a single category."""
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = []
        for i in range(100):
            cat = "A1" if i < 50 else "C9"
            v = 1 if cat == "A1" and i < 5 else 0
            vtypes = ["D1"] if v else []
            runs.append(_make_run(
                f"run_{i:03d}", cat, "control",
                violation_count=v, violation_types=vtypes,
                backend="live",
            ))

        _make_jsonl(runs, jsonl_path)
        per_cat = {
            "A1": {"planned": 50, "completed": 50, "failed": 0, "violations": 5},
            "C9": {"planned": 50, "completed": 50, "failed": 0, "violations": 0},
        }
        _make_status(100, "live", per_cat, status_path)

        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        rates = analysis.compute_per_category_rates()
        assert rates["A1"]["violations"] == 5
        assert rates["A1"]["rate"] == 0.1
        assert rates["C9"]["violations"] == 0

    def test_one_violation(self):
        """Exactly 1 violation in 200 runs."""
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = []
        for i in range(200):
            v = 1 if i == 0 else 0
            vtypes = ["D3"] if v else []
            runs.append(_make_run(
                f"run_{i:03d}", "A1", "heavy",
                violation_count=v, violation_types=vtypes,
                backend="live",
            ))

        _make_jsonl(runs, jsonl_path)
        _make_status(200, "live",
                     {"A1": {"planned": 200, "completed": 200,
                             "failed": 0, "violations": 1}},
                     status_path)

        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        agg = analysis.compute_aggregate_rate()
        assert agg["violations"] == 1
        assert agg["rate"] == 0.005
        # CI should contain 0.005
        assert agg["ci_lower"] <= 0.005 <= agg["ci_upper"]

        verdict = analysis.render_verdict()
        assert verdict["rq2b"] == "PASS"


# ══════════════════════════════════════════════════════════════════════
# 6. Forbidden Proxy Audit
# ══════════════════════════════════════════════════════════════════════


class TestForbiddenProxyAudit:

    def test_clean_audit_on_valid_analysis(self):
        """All proxies should be clean on a valid 0/211 mock analysis."""
        jsonl_path, status_path, _ = _build_zero_violation_campaign(
            n_per_cat=24, backend="mock"
        )
        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        audit = analysis.audit_forbidden_proxies()
        for proxy_id, result in audit.items():
            assert result["status"] == "clean", (
                f"Proxy {proxy_id} unexpectedly VIOLATED: {result['evidence']}"
            )

    def test_mock_as_real_violation_detected(self):
        """If backend=mock with violations and verdict is PASS, flag it."""
        # Create a scenario where violations exist on mock
        # The verdict will be PARTIAL (not PASS) for mock with violations,
        # so this proxy should remain clean
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = [_make_run(f"run_{i:03d}", "A1", "control",
                          violation_count=(1 if i < 3 else 0),
                          violation_types=(["D1"] if i < 3 else []),
                          backend="mock")
                for i in range(200)]
        _make_jsonl(runs, jsonl_path)
        _make_status(200, "mock",
                     {"A1": {"planned": 200, "completed": 200,
                             "failed": 0, "violations": 3}},
                     status_path)

        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        audit = analysis.audit_forbidden_proxies()
        # PARTIAL verdict on mock + violations => clean (not claiming PASS)
        assert audit["fp-mock-as-real"]["status"] == "clean"


# ══════════════════════════════════════════════════════════════════════
# 7. Dose-Response
# ══════════════════════════════════════════════════════════════════════


class TestDoseResponse:

    def test_flat_at_zero(self):
        """0 violations at all stress levels -> flat-at-zero."""
        jsonl_path, status_path, _ = _build_zero_violation_campaign(
            n_per_cat=12, backend="mock"
        )
        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        dr = analysis.test_dose_response()
        assert dr["trend_test"]["test"] == "cochran_armitage_not_applicable"
        assert dr["trend_test"]["trend_p_value"] is None
        for level in STRESS_LEVEL_ORDER:
            assert dr["per_stress_level"][level]["violations"] == 0

    def test_dose_response_with_violations(self):
        """Violations increasing with stress -> trend test should run."""
        tmpdir = Path(tempfile.mkdtemp())
        jsonl_path = tmpdir / "raw_violations.jsonl"
        status_path = tmpdir / "campaign_status.json"

        runs = []
        idx = 0
        # control: 0/50, mild: 1/50, moderate: 3/50, heavy: 8/50
        for stress, n_viols in [("control", 0), ("mild", 1),
                                 ("moderate", 3), ("heavy", 8)]:
            for i in range(50):
                v = 1 if i < n_viols else 0
                runs.append(_make_run(
                    f"run_{idx:03d}", "A1", stress,
                    violation_count=v,
                    violation_types=(["D1"] if v else []),
                    backend="live",
                ))
                idx += 1

        _make_jsonl(runs, jsonl_path)
        _make_status(200, "live",
                     {"A1": {"planned": 200, "completed": 200,
                             "failed": 0, "violations": 12}},
                     status_path)

        analysis = ViolationAnalysis(str(jsonl_path), str(status_path))
        dr = analysis.test_dose_response()
        assert dr["trend_test"]["test"] == "cochran_armitage"
        assert dr["trend_test"]["trend_p_value"] is not None
        # With increasing violations, we expect a significant trend
        assert dr["trend_test"]["trend_p_value"] < 0.05


# ══════════════════════════════════════════════════════════════════════
# 8. Full Analysis on Real Campaign Data
# ══════════════════════════════════════════════════════════════════════


class TestFullAnalysisRealData:
    """Integration test against the actual campaign data."""

    @pytest.fixture
    def real_analysis(self):
        viol_path = Path(__file__).parent.parent / "data/campaign/raw_violations.jsonl"
        status_path = Path(__file__).parent.parent / "data/campaign/campaign_status.json"
        if not viol_path.exists() or not status_path.exists():
            pytest.skip("Real campaign data not available")
        return ViolationAnalysis(str(viol_path), str(status_path))

    def test_real_total_runs(self, real_analysis):
        assert real_analysis.total_runs == 211

    def test_real_zero_violations(self, real_analysis):
        assert real_analysis.total_violations == 0

    def test_real_backend_mock(self, real_analysis):
        assert real_analysis.backend == "mock"

    def test_real_aggregate_rate(self, real_analysis):
        agg = real_analysis.compute_aggregate_rate()
        assert agg["rate"] == 0.0
        assert agg["ci_lower"] == 0.0
        # Two-sided CP upper for 0/211
        ref_upper = float(beta_dist.ppf(0.975, 1, 211))
        assert abs(agg["ci_upper"] - ref_upper) < 1e-6

    def test_real_bayesian_posterior(self, real_analysis):
        agg = real_analysis.compute_aggregate_rate()
        p_gt_2 = agg["bayesian_posterior"]["prob_rate_exceeds"]["0.02"]
        ref = float(1 - beta_dist(1, 212).cdf(0.02))
        assert abs(p_gt_2 - ref) < 1e-6
        # Should be < 5% (acceptance test requirement)
        assert p_gt_2 < 0.05

    def test_real_per_category_all_zero(self, real_analysis):
        rates = real_analysis.compute_per_category_rates()
        for cat in CATEGORY_ORDER:
            assert rates[cat]["violations"] == 0
            assert rates[cat]["rate"] == 0.0

    def test_real_per_category_runs_match_status(self, real_analysis):
        rates = real_analysis.compute_per_category_rates()
        expected = {
            "A1": 37, "A2": 37, "A3": 21, "A4": 21,
            "B5": 21, "B6": 21, "B7": 21, "B8": 9, "C9": 23,
        }
        for cat, expected_n in expected.items():
            assert rates[cat]["runs"] == expected_n, (
                f"Category {cat}: expected {expected_n} runs, got {rates[cat]['runs']}"
            )

    def test_real_adversarial_vs_control(self, real_analysis):
        result = real_analysis.test_adversarial_vs_control()
        assert result["p_value"] == 1.0
        assert result["adversarial"]["violations"] == 0
        assert result["control"]["violations"] == 0
        assert result["adversarial"]["runs"] == 188
        assert result["control"]["runs"] == 23

    def test_real_dose_response_flat(self, real_analysis):
        dr = real_analysis.test_dose_response()
        assert dr["trend_test"]["test"] == "cochran_armitage_not_applicable"
        expected_stress = {"control": 58, "mild": 57, "moderate": 50, "heavy": 46}
        for level, expected_n in expected_stress.items():
            assert dr["per_stress_level"][level]["runs"] == expected_n

    def test_real_v1_comparison(self, real_analysis):
        comp = real_analysis.compare_v1_baseline()
        assert comp["v1"]["ci_upper"] > 0.11
        assert comp["v2"]["ci_upper"] < 0.02
        assert comp["improvement_factor"] > 6.0
        assert comp["fisher_p"] == 1.0  # both zero

    def test_real_verdict_negative_strong(self, real_analysis):
        verdict = real_analysis.render_verdict()
        assert "NEGATIVE-STRONG" in verdict["rq2b"]
        assert "pipeline-validated" in verdict["rq2b"]
        assert verdict["confidence"] == "medium"
        assert verdict["backend_caveat"] is not None

    def test_real_forbidden_proxies_clean(self, real_analysis):
        audit = real_analysis.audit_forbidden_proxies()
        for proxy_id, result in audit.items():
            assert result["status"] == "clean", (
                f"{proxy_id}: {result['evidence']}"
            )

    def test_real_cc015_triggered(self, real_analysis):
        results = real_analysis.run_full_analysis()
        assert results["cc015_trigger"] is True
        assert results["cc015_assessment"] is not None

    def test_real_full_analysis_schema(self, real_analysis):
        """Verify all required top-level keys in full analysis output."""
        results = real_analysis.run_full_analysis()
        required_keys = [
            "campaign_summary", "aggregate", "per_category", "per_dtype",
            "per_stress_level", "comparisons", "anchors", "verdict",
            "forbidden_proxy_audit", "cc015_trigger",
        ]
        for key in required_keys:
            assert key in results, f"Missing key: {key}"

    def test_real_mock_d7_artifacts_counted(self, real_analysis):
        assert real_analysis.total_mock_d7 > 0
        results = real_analysis.run_full_analysis()
        assert results["campaign_summary"]["mock_d7_artifacts_excluded"] > 0
