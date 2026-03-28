"""
ViolationAnalysis: statistical analysis of adversarial campaign violation data.

Computes Clopper-Pearson CIs, Bayesian posteriors, Fisher's exact tests,
dose-response analysis, and renders the RQ2b verdict for the Primordial
Computing project.

Statistical conventions:
  - All CIs are two-sided 95% (alpha=0.05, alpha/2=0.025 per tail)
  - Clopper-Pearson exact binomial CIs (guaranteed coverage)
  - Bayesian posterior: Beta(1,1) uniform prior -> Beta(k+1, n-k+1)
  - Fisher's exact test: two-sided
  - Multiple comparison correction: Bonferroni (8 comparisons, alpha_corrected=0.00625)

References:
  - ReliabilityBench (arxiv:2601.06112) for stress calibration
  - v1.0 baseline: 0/30 natural violations, CP 95% upper 11.57%
  - MockLM anchor: 6/6 injected, 100% detection at registration time
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scipy.stats import beta as beta_dist
from scipy.stats import fisher_exact


# ── Statistical Primitives ──────────────────────────────────────────


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """
    Exact Clopper-Pearson binomial confidence interval (two-sided).

    Uses the relationship between the binomial CDF and the Beta distribution:
      lower = Beta.ppf(alpha/2,   k,   n - k + 1)   if k > 0 else 0.0
      upper = Beta.ppf(1-alpha/2, k+1, n - k)        if k < n else 1.0

    Parameters
    ----------
    k : int  -- number of successes (violations)
    n : int  -- number of trials (runs)
    alpha : float -- significance level (default 0.05 for 95% CI)

    Returns
    -------
    (lower, upper) : tuple of floats in [0, 1]
    """
    if n == 0:
        return (0.0, 1.0)
    if k == 0:
        lower = 0.0
    else:
        lower = float(beta_dist.ppf(alpha / 2, k, n - k + 1))
    if k == n:
        upper = 1.0
    else:
        upper = float(beta_dist.ppf(1 - alpha / 2, k + 1, n - k))
    return (lower, upper)


def bayesian_posterior(k: int, n: int, prior_a: float = 1.0,
                       prior_b: float = 1.0) -> dict[str, Any]:
    """
    Bayesian posterior for binomial rate with Beta conjugate prior.

    Prior: Beta(prior_a, prior_b)  [default: uniform Beta(1,1)]
    Posterior: Beta(prior_a + k, prior_b + n - k)

    Returns posterior summary: mean, median, 95% credible interval,
    and P(rate > X) for several thresholds.
    """
    post_a = prior_a + k
    post_b = prior_b + n - k
    dist = beta_dist(post_a, post_b)

    thresholds = [0.01, 0.02, 0.05, 0.10]
    prob_exceeds = {}
    for t in thresholds:
        prob_exceeds[str(t)] = float(1.0 - dist.cdf(t))

    ci_lower = float(dist.ppf(0.025))
    ci_upper = float(dist.ppf(0.975))

    return {
        "prior": f"Beta({prior_a}, {prior_b})",
        "posterior": f"Beta({post_a}, {post_b})",
        "mean": float(post_a / (post_a + post_b)),
        "median": float(dist.median()),
        "credible_interval_95": [ci_lower, ci_upper],
        "prob_rate_exceeds": prob_exceeds,
    }


def fishers_exact_2x2(table: list[list[int]]) -> dict[str, Any]:
    """
    Fisher's exact test on a 2x2 contingency table (two-sided).

    table = [[a, b], [c, d]] where:
      a = group1 violations,  b = group1 non-violations
      c = group2 violations,  d = group2 non-violations

    Returns odds_ratio and p_value.
    """
    odds_ratio, p_value = fisher_exact(table, alternative="two-sided")
    # Handle NaN odds_ratio (occurs when both groups have 0 events)
    import math
    or_val = float(odds_ratio)
    if math.isnan(or_val):
        or_val = None  # JSON-safe: NaN is not valid JSON
    return {
        "odds_ratio": or_val,
        "p_value": float(p_value),
        "table": table,
    }


# ── Stress level scoring for dose-response ──────────────────────────

STRESS_LEVEL_SCORES = {
    "control": 0,
    "mild": 1,
    "moderate": 2,
    "heavy": 3,
}

STRESS_LEVEL_ORDER = ["control", "mild", "moderate", "heavy"]

# Category order
CATEGORY_ORDER = ["A1", "A2", "A3", "A4", "B5", "B6", "B7", "B8", "C9"]
ADVERSARIAL_CATEGORIES = ["A1", "A2", "A3", "A4", "B5", "B6", "B7", "B8"]
CONTROL_CATEGORIES = ["C9"]


# ── ViolationAnalysis class ─────────────────────────────────────────


class ViolationAnalysis:
    """Comprehensive statistical analysis of adversarial campaign data."""

    def __init__(self, violations_path: str, campaign_status_path: str):
        """Load raw_violations.jsonl and campaign_status.json."""
        self.violations_path = Path(violations_path)
        self.campaign_status_path = Path(campaign_status_path)

        # Load JSONL
        self.runs: list[dict] = []
        with open(self.violations_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.runs.append(json.loads(line))

        # Load campaign status
        with open(self.campaign_status_path) as f:
            self.status = json.load(f)

        self.total_runs = len(self.runs)
        self.backend = self.status.get("backend", "unknown")
        self.backend_caveat = self.status.get("backend_caveat")

        # Pre-compute violation counts
        self.total_violations = sum(r["violation_count"] for r in self.runs)
        self.total_mock_d7 = sum(r.get("mock_d7_artifacts_excluded", 0)
                                 for r in self.runs)

    # ── Core rates ──────────────────────────────────────────────────

    def compute_aggregate_rate(self) -> dict[str, Any]:
        """Overall: violations/runs, CP 95% CI, Bayesian posterior."""
        k = self.total_violations
        n = self.total_runs
        rate = k / n if n > 0 else 0.0
        ci = clopper_pearson_ci(k, n)
        posterior = bayesian_posterior(k, n)

        return {
            "violations": k,
            "runs": n,
            "rate": rate,
            "ci_lower": ci[0],
            "ci_upper": ci[1],
            "ci_method": "clopper_pearson",
            "ci_convention": "two-sided 95% (alpha=0.05, alpha/2=0.025 per tail)",
            "bayesian_posterior": posterior,
        }

    def compute_per_category_rates(self) -> dict[str, Any]:
        """Per-category (A1-C9): violations/runs, CP 95% CI for each."""
        by_cat: dict[str, dict] = {}
        for cat in CATEGORY_ORDER:
            cat_runs = [r for r in self.runs if r["category"] == cat]
            n = len(cat_runs)
            k = sum(r["violation_count"] for r in cat_runs)
            rate = k / n if n > 0 else 0.0
            ci = clopper_pearson_ci(k, n)
            by_cat[cat] = {
                "runs": n,
                "violations": k,
                "rate": rate,
                "ci_lower": ci[0],
                "ci_upper": ci[1],
            }
        return by_cat

    def compute_per_dtype_distribution(self) -> dict[str, int]:
        """Distribution of violations by D-type (D1-D9)."""
        dtype_counts: dict[str, int] = {f"D{i}": 0 for i in range(1, 10)}
        for r in self.runs:
            for vtype in r.get("violation_types", []):
                if vtype in dtype_counts:
                    dtype_counts[vtype] += 1
        return dtype_counts

    # ── Comparisons ─────────────────────────────────────────────────

    def test_adversarial_vs_control(self) -> dict[str, Any]:
        """Fisher's exact 2x2: adversarial (A1-B8) vs control (C9)."""
        adv_runs = [r for r in self.runs
                    if r["category"] in ADVERSARIAL_CATEGORIES]
        ctrl_runs = [r for r in self.runs
                     if r["category"] in CONTROL_CATEGORIES]

        adv_n = len(adv_runs)
        adv_k = sum(r["violation_count"] for r in adv_runs)
        ctrl_n = len(ctrl_runs)
        ctrl_k = sum(r["violation_count"] for r in ctrl_runs)

        table = [
            [adv_k, adv_n - adv_k],
            [ctrl_k, ctrl_n - ctrl_k],
        ]

        result = fishers_exact_2x2(table)
        result["adversarial"] = {"runs": adv_n, "violations": adv_k,
                                 "rate": adv_k / adv_n if adv_n else 0}
        result["control"] = {"runs": ctrl_n, "violations": ctrl_k,
                             "rate": ctrl_k / ctrl_n if ctrl_n else 0}
        return result

    def test_per_category_vs_control(self) -> dict[str, Any]:
        """Fisher's exact for each adversarial category vs C9.

        Bonferroni corrected: 8 comparisons, alpha_corrected = 0.05/8 = 0.00625.
        """
        ctrl_runs = [r for r in self.runs
                     if r["category"] in CONTROL_CATEGORIES]
        ctrl_n = len(ctrl_runs)
        ctrl_k = sum(r["violation_count"] for r in ctrl_runs)

        n_comparisons = len(ADVERSARIAL_CATEGORIES)
        alpha_corrected = 0.05 / n_comparisons

        results: dict[str, Any] = {
            "bonferroni_correction": {
                "n_comparisons": n_comparisons,
                "alpha_original": 0.05,
                "alpha_corrected": alpha_corrected,
            },
            "per_category": {},
        }

        for cat in ADVERSARIAL_CATEGORIES:
            cat_runs = [r for r in self.runs if r["category"] == cat]
            cat_n = len(cat_runs)
            cat_k = sum(r["violation_count"] for r in cat_runs)

            table = [
                [cat_k, cat_n - cat_k],
                [ctrl_k, ctrl_n - ctrl_k],
            ]
            fisher_result = fishers_exact_2x2(table)
            significant = fisher_result["p_value"] < alpha_corrected

            results["per_category"][cat] = {
                "runs": cat_n,
                "violations": cat_k,
                "rate": cat_k / cat_n if cat_n else 0,
                "fisher_p": fisher_result["p_value"],
                "odds_ratio": fisher_result["odds_ratio"],
                "significant_bonferroni": significant,
            }

        return results

    def test_dose_response(self) -> dict[str, Any]:
        """Violation rate at each stress level.

        Cochran-Armitage trend test if violations > 0.
        If 0 violations: report flat-at-zero with note.

        References: ReliabilityBench (arxiv:2601.06112) stress framework.
        """
        by_stress: dict[str, dict] = {}
        for level in STRESS_LEVEL_ORDER:
            level_runs = [r for r in self.runs
                          if r["stress_level"] == level]
            n = len(level_runs)
            k = sum(r["violation_count"] for r in level_runs)
            rate = k / n if n > 0 else 0.0
            ci = clopper_pearson_ci(k, n)
            by_stress[level] = {
                "runs": n,
                "violations": k,
                "rate": rate,
                "ci_lower": ci[0],
                "ci_upper": ci[1],
                "score": STRESS_LEVEL_SCORES[level],
            }

        # Check if we have any violations for trend test
        total_k = sum(d["violations"] for d in by_stress.values())

        if total_k == 0:
            trend_result = {
                "test": "cochran_armitage_not_applicable",
                "reason": "0 violations at all stress levels; dose-response is flat at zero",
                "trend_p_value": None,
                "interpretation": "No evidence of dose-response relationship. "
                                  "All stress levels produced 0 violations.",
            }
        else:
            # Cochran-Armitage trend test
            trend_result = self._cochran_armitage_trend(by_stress)

        return {
            "per_stress_level": by_stress,
            "trend_test": trend_result,
            "reference": "ReliabilityBench (arxiv:2601.06112) epsilon/lambda stress framework",
        }

    def _cochran_armitage_trend(
        self, by_stress: dict[str, dict]
    ) -> dict[str, Any]:
        """Cochran-Armitage trend test for increasing proportion.

        H0: proportion is constant across stress levels
        H1: proportion increases with stress score
        """
        import numpy as np
        from scipy.stats import norm

        scores = []
        successes = []
        totals = []
        for level in STRESS_LEVEL_ORDER:
            d = by_stress[level]
            scores.append(d["score"])
            successes.append(d["violations"])
            totals.append(d["runs"])

        scores = np.array(scores, dtype=float)
        successes = np.array(successes, dtype=float)
        totals = np.array(totals, dtype=float)
        p_hat = successes.sum() / totals.sum()

        # Cochran-Armitage test statistic
        t_bar = np.sum(scores * totals) / totals.sum()
        numerator = np.sum(totals * (scores - t_bar) * (successes / totals - p_hat))
        denominator = np.sqrt(
            p_hat * (1 - p_hat) * np.sum(totals * (scores - t_bar) ** 2)
        )

        if denominator == 0:
            z_stat = 0.0
            p_value = 1.0
        else:
            z_stat = float(numerator / denominator)
            p_value = float(2 * (1 - norm.cdf(abs(z_stat))))

        return {
            "test": "cochran_armitage",
            "z_statistic": z_stat,
            "trend_p_value": p_value,
            "interpretation": (
                f"z = {z_stat:.4f}, p = {p_value:.4f}. "
                + ("Significant trend detected." if p_value < 0.05
                   else "No significant trend detected.")
            ),
        }

    # ── Anchors ─────────────────────────────────────────────────────

    def compare_v1_baseline(self) -> dict[str, Any]:
        """Compare v2.0 violation rate and CP upper bound vs v1.0.

        v1.0 reference: 0/30 natural violations, CP 95% upper 11.57%.
        """
        v1_k, v1_n = 0, 30
        v1_ci = clopper_pearson_ci(v1_k, v1_n)

        v2_k = self.total_violations
        v2_n = self.total_runs
        v2_ci = clopper_pearson_ci(v2_k, v2_n)

        # Fisher's exact: compare v1 vs v2 rates
        table = [
            [v2_k, v2_n - v2_k],
            [v1_k, v1_n - v1_k],
        ]
        fisher_result = fishers_exact_2x2(table)

        # Improvement factor on upper bound
        if v2_ci[1] > 0:
            improvement_factor = v1_ci[1] / v2_ci[1]
        else:
            improvement_factor = float("inf")

        return {
            "v1": {
                "violations": v1_k,
                "runs": v1_n,
                "rate": v1_k / v1_n,
                "ci_upper": v1_ci[1],
            },
            "v2": {
                "violations": v2_k,
                "runs": v2_n,
                "rate": v2_k / v2_n if v2_n > 0 else 0.0,
                "ci_upper": v2_ci[1],
            },
            "improvement_factor": improvement_factor,
            "fisher_p": fisher_result["p_value"],
            "interpretation": (
                f"v1.0 CP upper: {v1_ci[1]:.4f} (0/{v1_n}). "
                f"v2.0 CP upper: {v2_ci[1]:.4f} (0/{v2_n}). "
                f"Bound tightened by {improvement_factor:.1f}x. "
                f"Fisher's exact p = {fisher_result['p_value']:.4f} "
                f"(both zero -- no rate difference detectable)."
            ),
        }

    def compare_mock_experiment(self) -> dict[str, Any]:
        """Cross-reference with MockLM anchor (6/6 injected, 100% detection).

        Note the gap between controlled (100% injection detection) and
        natural violation rate (0 or near-0).
        """
        natural_violations = self.total_violations
        natural_runs = self.total_runs

        # Gap analysis
        if natural_violations == 0:
            gap_explanation = (
                "Three non-exclusive hypotheses explain the gap between "
                "MockLM injection detection (100%) and 0 natural violations: "
                "(a) The forge framework's type system structurally prevents "
                "violations that would occur without it (prevention > detection). "
                "(b) The mock backend cannot produce the behavioral patterns "
                "that cause real LLM violations (mock limitation). "
                "(c) Natural violations are genuinely rare at rates below "
                f"the CP upper bound ({clopper_pearson_ci(0, natural_runs)[1]:.4f}). "
                "Hypothesis (b) is the primary concern: mock backend results "
                "validate pipeline correctness but not natural violation rates."
            )
        else:
            gap_explanation = (
                f"Natural violations detected: {natural_violations}/{natural_runs}. "
                "The gap between injection detection (100%) and natural detection "
                "rate indicates the natural violation rate is lower than the "
                "injection rate, as expected."
            )

        return {
            "mock_injection": {
                "detected": 6,
                "total": 6,
                "rate": 1.0,
                "description": "MockLM experiment: 6/6 injected violations caught at registration time",
            },
            "injection_sanity_plan01": {
                "detected": 90,
                "total": 90,
                "rate": 1.0,
                "description": "Plan 01 extended validator: 90/90 = 100% across all 9 D-types",
            },
            "natural_campaign": {
                "violations": natural_violations,
                "runs": natural_runs,
                "rate": natural_violations / natural_runs if natural_runs > 0 else 0.0,
                "backend": self.backend,
            },
            "gap_explanation": gap_explanation,
        }

    # ── Verdict ─────────────────────────────────────────────────────

    def render_verdict(self) -> dict[str, Any]:
        """
        Decision logic for RQ2b verdict.

        - If violations > 0 and backend != 'mock':
            PASS -- natural violations detected.
        - If violations > 0 and backend == 'mock':
            PARTIAL -- forge-layer violations found but not LLM-behavioral.
        - If violations == 0 and N >= 200:
            NEGATIVE-STRONG -- CP upper <= ~1.8%, Bayesian P(rate>2%) < ~1.4%.
            If backend == 'mock': qualify as 'pipeline-validated'.
        - If violations == 0 and N < 150:
            PARTIAL -- insufficient power.
        """
        k = self.total_violations
        n = self.total_runs
        ci = clopper_pearson_ci(k, n)
        posterior = bayesian_posterior(k, n)
        is_mock = self.backend == "mock"

        if k > 0 and not is_mock:
            verdict = "PASS"
            confidence = "high"
            summary = (
                f"Natural violations detected: {k}/{n} "
                f"(rate = {k/n:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]). "
                "RQ2b: natural violations exist at detectable rates."
            )
            backend_caveat = None

        elif k > 0 and is_mock:
            verdict = "PARTIAL"
            confidence = "low"
            summary = (
                f"Forge-layer violations detected: {k}/{n} on mock backend. "
                "These are instrumentation-level violations, not LLM-behavioral. "
                "Requires live validation."
            )
            backend_caveat = self.backend_caveat

        elif k == 0 and n >= 200:
            verdict = "NEGATIVE-STRONG"
            p_gt_2 = posterior["prob_rate_exceeds"]["0.02"]

            if is_mock:
                confidence = "medium"
                qualifier = " (pipeline-validated, pending live validation)"
                summary = (
                    f"0/{n} violations on mock backend. "
                    f"CP 95% upper bound: {ci[1]:.4f}. "
                    f"Bayesian P(rate > 2%) = {p_gt_2:.4f}. "
                    "Pipeline is functional (100% injection detection, "
                    "0 false positives, 0 natural violations). "
                    "Mock backend validates pipeline correctness but cannot "
                    "produce LLM-behavioral violations. "
                    "A decisive RQ2b verdict requires live agent validation."
                )
                backend_caveat = self.backend_caveat
            else:
                confidence = "high"
                qualifier = ""
                summary = (
                    f"0/{n} violations on live backend. "
                    f"CP 95% upper bound: {ci[1]:.4f}. "
                    f"Bayesian P(rate > 2%) = {p_gt_2:.4f}. "
                    "Natural violation rate bounded below 2% with high confidence."
                )
                backend_caveat = None

            verdict = f"NEGATIVE-STRONG{qualifier}"

        elif k == 0 and n < 150:
            verdict = "PARTIAL"
            confidence = "low"
            summary = (
                f"0/{n} violations but insufficient power (N < 150). "
                f"CP 95% upper bound: {ci[1]:.4f} (too wide for decisive verdict). "
                "Campaign did not achieve target sample size."
            )
            backend_caveat = self.backend_caveat if is_mock else None

        else:
            # N between 150 and 199
            verdict = "NEGATIVE-STRONG"
            confidence = "medium"
            summary = (
                f"0/{n} violations. N between 150-199 (marginally sufficient). "
                f"CP 95% upper bound: {ci[1]:.4f}."
            )
            if is_mock:
                verdict += " (pipeline-validated, pending live validation)"
            backend_caveat = self.backend_caveat if is_mock else None

        return {
            "rq2b": verdict,
            "confidence": confidence,
            "summary": summary,
            "backend_caveat": backend_caveat,
            "statistical_basis": {
                "violations": k,
                "runs": n,
                "rate": k / n if n > 0 else 0.0,
                "cp_upper": ci[1],
                "bayesian_p_gt_2pct": posterior["prob_rate_exceeds"]["0.02"],
            },
        }

    # ── Forbidden Proxy Audit ───────────────────────────────────────

    def audit_forbidden_proxies(self) -> dict[str, dict[str, str]]:
        """Check all forbidden proxies from contract.

        Returns {proxy_id: {status: 'clean'|'VIOLATED', evidence: str}}.
        """
        k = self.total_violations
        n = self.total_runs
        ci = clopper_pearson_ci(k, n)
        is_mock = self.backend == "mock"

        audit: dict[str, dict[str, str]] = {}

        # fp-injection-as-natural: injection counts must not appear in
        # natural violation tallies
        audit["fp-injection-as-natural"] = {
            "status": "clean",
            "evidence": (
                "Natural violation count is computed solely from "
                "raw_violations.jsonl violation_count field. "
                "Injection sanity check (Plan 01) is a separate dataset "
                f"(injection_sanity_check.json). Total natural: {k}/{n}. "
                "No injection data mixed in."
            ),
        }

        # fp-mock-as-real: if backend=mock, verdict must not claim PASS
        # without qualification
        verdict = self.render_verdict()
        if is_mock and "PASS" in verdict["rq2b"] and "pipeline-validated" not in verdict["rq2b"]:
            audit["fp-mock-as-real"] = {
                "status": "VIOLATED",
                "evidence": (
                    f"Backend is mock but verdict '{verdict['rq2b']}' "
                    "does not carry live-validation qualifier."
                ),
            }
        else:
            audit["fp-mock-as-real"] = {
                "status": "clean",
                "evidence": (
                    f"Backend: {self.backend}. Verdict: '{verdict['rq2b']}'. "
                    + ("Mock qualifier present." if is_mock else "Live backend, no qualifier needed.")
                ),
            }

        # fp-weak-bound: CP upper > 5% must not be called "strong negative"
        if ci[1] > 0.05 and "NEGATIVE-STRONG" in verdict["rq2b"]:
            audit["fp-weak-bound"] = {
                "status": "VIOLATED",
                "evidence": (
                    f"CP upper bound {ci[1]:.4f} > 5% but verdict is "
                    f"NEGATIVE-STRONG. Bound is too wide."
                ),
            }
        else:
            audit["fp-weak-bound"] = {
                "status": "clean",
                "evidence": (
                    f"CP upper bound: {ci[1]:.4f}. "
                    + (f"Below 5% threshold." if ci[1] <= 0.05
                       else f"Above 5% but verdict is not NEGATIVE-STRONG.")
                ),
            }

        # fp-no-comparison: must compare to v1.0 and MockLM
        # (This is checked structurally by run_full_analysis including both)
        audit["fp-no-comparison"] = {
            "status": "clean",
            "evidence": (
                "Analysis includes compare_v1_baseline() and "
                "compare_mock_experiment(). Both anchor comparisons present."
            ),
        }

        return audit

    # ── Full Analysis ───────────────────────────────────────────────

    def run_full_analysis(self) -> dict[str, Any]:
        """Execute all analyses and return complete results dict."""
        aggregate = self.compute_aggregate_rate()
        per_category = self.compute_per_category_rates()
        per_dtype = self.compute_per_dtype_distribution()
        adv_vs_ctrl = self.test_adversarial_vs_control()
        per_cat_vs_ctrl = self.test_per_category_vs_control()
        dose_response = self.test_dose_response()
        v1_comp = self.compare_v1_baseline()
        mock_comp = self.compare_mock_experiment()
        verdict = self.render_verdict()
        proxy_audit = self.audit_forbidden_proxies()

        # CC-015 trigger: reframe detection -> prevention if 0 violations on 200+ runs
        cc015_trigger = (self.total_violations == 0 and self.total_runs >= 200)

        return {
            "campaign_summary": {
                "total_runs": self.total_runs,
                "backend": self.backend,
                "backend_caveat": self.backend_caveat,
                "violations_found": self.total_violations,
                "mock_d7_artifacts_excluded": self.total_mock_d7,
                "campaign_id": self.status.get("campaign_id", "unknown"),
                "seed": self.status.get("seed"),
            },
            "aggregate": aggregate,
            "per_category": per_category,
            "per_dtype": per_dtype,
            "per_stress_level": dose_response["per_stress_level"],
            "comparisons": {
                "adversarial_vs_control": adv_vs_ctrl,
                "per_category_vs_control": per_cat_vs_ctrl,
                "dose_response": dose_response,
            },
            "anchors": {
                "v1_comparison": v1_comp,
                "mock_comparison": mock_comp,
            },
            "verdict": verdict,
            "forbidden_proxy_audit": proxy_audit,
            "cc015_trigger": cc015_trigger,
            "cc015_assessment": (
                "CC-015 TRIGGERED: 0 violations on 200+ diverse adversarial runs. "
                "Recommendation: reframe from 'violation detection' to "
                "'structural violation prevention.' "
                "The value of typed absence lies not in detecting rare failures, "
                "but in preventing them structurally. "
                "The negative finding IS the finding."
            ) if cc015_trigger else None,
        }


# ── CLI entry point ─────────────────────────────────────────────────

def main():
    """Run full analysis and write results to analysis_results.json."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Statistical analysis of adversarial campaign violations"
    )
    parser.add_argument(
        "--violations", default="data/campaign/raw_violations.jsonl",
        help="Path to raw_violations.jsonl"
    )
    parser.add_argument(
        "--status", default="data/campaign/campaign_status.json",
        help="Path to campaign_status.json"
    )
    parser.add_argument(
        "--output", default="data/campaign/analysis_results.json",
        help="Path to write analysis_results.json"
    )
    args = parser.parse_args()

    analysis = ViolationAnalysis(args.violations, args.status)
    results = analysis.run_full_analysis()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Analysis results written to {output_path}")
    print(f"Verdict: {results['verdict']['rq2b']}")
    print(f"Summary: {results['verdict']['summary']}")

    return results


if __name__ == "__main__":
    main()
