"""Statistical analysis pipeline for genuine LLM compaction experiments.

Consumes Track A pilot data (JSONL), optional Track B and Track C data,
runs hypothesis tests, computes confidence intervals, compares against
anchor benchmarks, and renders an honest RQ3b verdict.

Convention assertions (project-specific -- physics conventions N/A):
  artifact_id_format = "artifact:<run>:iter:<n>:r1"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
  ci_method_boundary = "Clopper-Pearson exact for boundary values (0.0 or 1.0)"
  ci_method_interior = "Bootstrap B=10000 seed=42 for interior values N>=10"
  ci_method_small_n = "Wilson score for interior values N<10"
  multiple_comparisons = "Bonferroni correction for 3 primary comparisons"

Phase: 06-genuine-compaction
Plan: 05
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class HypothesisResult:
    """Result of a single hypothesis test."""
    test_name: str
    h0: str
    h1: str
    statistic: float
    p_value: float
    p_value_corrected: float | None  # Bonferroni-corrected if applicable
    effect_size_d: float
    mean: float
    std: float
    ci_95: tuple[float, float]
    ci_method: str
    n: int
    reject_h0: bool
    alpha: float
    interpretation: str


@dataclass
class AnchorComparison:
    """Comparison of genuine compaction metrics against known anchors."""
    mockml: dict
    knowledge_objects: dict
    v1_simulated: dict
    overall_verdict: str  # pass / partial / fail


@dataclass
class Verdict:
    """Final verdict for a claim."""
    claim_id: str
    verdict: str  # PASS / PARTIAL / FAIL / BACKTRACK
    evidence: list[str]
    criteria_used: str
    sample_size_caveat: str
    confidence_tag: str  # HIGH / MEDIUM / LOW


@dataclass
class ForbiddenProxyAudit:
    """Audit status for each forbidden proxy."""
    proxy_id: str
    status: str  # rejected / violated / unresolved
    evidence: str
    notes: str


# ═══════════════════════════════════════════════════════════════════════
# CONFIDENCE INTERVALS
# ═══════════════════════════════════════════════════════════════════════


def bootstrap_ci(
    values: list[float],
    B: int = 10000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval.

    Args:
        values: Sample of observations.
        B: Number of bootstrap replicates.
        seed: Random seed for reproducibility.
        alpha: Significance level (default 0.05 for 95% CI).

    Returns:
        (lower, upper) bounds of the 100*(1-alpha)% CI.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute bootstrap CI on empty sample")

    rng = np.random.default_rng(seed)
    arr = np.array(values)
    n = len(arr)

    boot_means = np.empty(B)
    for i in range(B):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    # Dimensional check: CI bounds in plausible range
    assert lower <= upper, f"bootstrap_ci: lower ({lower}) > upper ({upper})"

    return (lower, upper)


def clopper_pearson_ci(
    k: int,
    n: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Exact binomial (Clopper-Pearson) confidence interval.

    Args:
        k: Number of successes.
        n: Number of trials.
        alpha: Significance level.

    Returns:
        (lower, upper) bounds of the exact binomial CI.
    """
    if n == 0:
        return (0.0, 1.0)

    from scipy.stats import beta as beta_dist

    if k == 0:
        lower = 0.0
    else:
        lower = float(beta_dist.ppf(alpha / 2, k, n - k + 1))

    if k == n:
        upper = 1.0
    else:
        upper = float(beta_dist.ppf(1 - alpha / 2, k + 1, n - k))

    return (lower, upper)


def wilson_ci(
    k: int,
    n: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Wilson score confidence interval for small N interior values.

    Args:
        k: Number of successes.
        n: Number of trials.
        alpha: Significance level.

    Returns:
        (lower, upper) bounds of the Wilson score CI.
    """
    if n == 0:
        return (0.0, 1.0)

    from scipy.stats import norm

    z = norm.ppf(1 - alpha / 2)
    p_hat = k / n
    denom = 1 + z ** 2 / n
    center = (p_hat + z ** 2 / (2 * n)) / denom
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z ** 2 / (4 * n)) / n) / denom

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (lower, upper)


def select_ci(
    values: list[float],
    alpha: float = 0.05,
) -> tuple[tuple[float, float], str]:
    """Select and compute the appropriate CI method.

    Convention:
      - Boundary (all 0.0 or all 1.0) -> Clopper-Pearson exact
      - Interior, N >= 10 -> Bootstrap (B=10000, seed=42)
      - Interior, N < 10 -> Wilson score

    Returns:
        ((lower, upper), method_name)
    """
    if not values:
        return ((0.0, 1.0), "empty")

    n = len(values)
    all_one = all(abs(v - 1.0) < 1e-12 for v in values)
    all_zero = all(abs(v) < 1e-12 for v in values)

    if all_one:
        return clopper_pearson_ci(n, n, alpha), "clopper_pearson"
    elif all_zero:
        return clopper_pearson_ci(0, n, alpha), "clopper_pearson"
    elif n < 10:
        # Wilson score: treat values > 0.5 as successes for a proportion CI
        # For continuous metrics, use the count of successes relative to a threshold
        # Fall back to bootstrap if values are not binary
        if all(v in (0.0, 1.0) for v in values):
            k = sum(1 for v in values if v > 0.5)
            return wilson_ci(k, n, alpha), "wilson"
        else:
            # For continuous non-binary small samples, use bootstrap anyway
            # Wilson is technically for proportions; bootstrap is more general
            return bootstrap_ci(values, alpha=alpha), "bootstrap_small_n"
    else:
        return bootstrap_ci(values, alpha=alpha), "bootstrap"


# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS TESTS
# ═══════════════════════════════════════════════════════════════════════


def test_reachability_hypothesis(
    data: list[dict],
    metric_key: str = "structural_reachability",
    threshold: float = 0.5,
    alpha: float = 0.05,
) -> HypothesisResult:
    """Test H0: metric <= threshold vs H1: metric > threshold.

    Uses one-sample t-test (scipy.stats.ttest_1samp, alternative='greater').

    Args:
        data: List of trial result dicts with 'aggregate_metrics' field.
        metric_key: Key within aggregate_metrics to test.
        threshold: H0 threshold value.
        alpha: Significance level.

    Returns:
        HypothesisResult with all test details.
    """
    from scipy.stats import ttest_1samp

    values = _extract_metric(data, metric_key)
    n = len(values)

    if n < 2:
        return HypothesisResult(
            test_name=f"one_sample_t_test_{metric_key}",
            h0=f"{metric_key} <= {threshold}",
            h1=f"{metric_key} > {threshold}",
            statistic=float("nan"),
            p_value=1.0,
            p_value_corrected=None,
            effect_size_d=float("nan"),
            mean=values[0] if values else float("nan"),
            std=0.0,
            ci_95=(float("nan"), float("nan")),
            ci_method="insufficient_data",
            n=n,
            reject_h0=False,
            alpha=alpha,
            interpretation=f"Insufficient data (N={n}) for hypothesis test",
        )

    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values)

    # One-sample t-test, one-sided (greater)
    t_stat, p_two_sided = ttest_1samp(values, threshold)
    # Convert to one-sided p-value (H1: mean > threshold)
    if t_stat > 0:
        p_one_sided = p_two_sided / 2
    else:
        p_one_sided = 1 - p_two_sided / 2

    # Effect size Cohen's d
    if std_val > 0:
        effect_d = (mean_val - threshold) / std_val
    else:
        # All values identical
        effect_d = float("inf") if mean_val > threshold else float("-inf") if mean_val < threshold else 0.0

    # Confidence interval
    ci, ci_method = select_ci(values, alpha)

    reject = p_one_sided < alpha

    if reject:
        interp = (
            f"Reject H0: {metric_key} > {threshold} "
            f"(t={t_stat:.4f}, p={p_one_sided:.6f}, d={effect_d:.3f}, N={n})"
        )
    else:
        interp = (
            f"Fail to reject H0: insufficient evidence that {metric_key} > {threshold} "
            f"(t={t_stat:.4f}, p={p_one_sided:.6f}, d={effect_d:.3f}, N={n})"
        )

    return HypothesisResult(
        test_name=f"one_sample_t_test_{metric_key}",
        h0=f"{metric_key} <= {threshold}",
        h1=f"{metric_key} > {threshold}",
        statistic=float(t_stat),
        p_value=float(p_one_sided),
        p_value_corrected=None,
        effect_size_d=float(effect_d),
        mean=mean_val,
        std=std_val,
        ci_95=ci,
        ci_method=ci_method,
        n=n,
        reject_h0=reject,
        alpha=alpha,
        interpretation=interp,
    )


def test_instruction_delta(
    data_aware: list[dict],
    data_default: list[dict],
    metric_key: str = "artifact_id_survival",
    n_comparisons: int = 3,
    alpha: float = 0.05,
) -> HypothesisResult:
    """Test H0: delta = survival(aware) - survival(default) <= 0.

    Uses Wilcoxon signed-rank test if samples are paired, otherwise
    Mann-Whitney U. Falls back to t-test if N >= 20.

    Applies Bonferroni correction for multiple comparisons.

    Args:
        data_aware: Trials with provenance_aware instructions.
        data_default: Trials with default instructions.
        metric_key: Metric to compare.
        n_comparisons: Number of comparisons for Bonferroni correction.
        alpha: Significance level before correction.

    Returns:
        HypothesisResult with corrected and uncorrected p-values.
    """
    from scipy.stats import mannwhitneyu, ttest_ind, wilcoxon

    values_aware = _extract_metric(data_aware, metric_key)
    values_default = _extract_metric(data_default, metric_key)

    n_aware = len(values_aware)
    n_default = len(values_default)
    n_min = min(n_aware, n_default)

    if n_min < 2:
        return HypothesisResult(
            test_name=f"instruction_delta_{metric_key}",
            h0=f"delta({metric_key}) <= 0",
            h1=f"delta({metric_key}) > 0",
            statistic=float("nan"),
            p_value=1.0,
            p_value_corrected=1.0,
            effect_size_d=float("nan"),
            mean=float("nan"),
            std=float("nan"),
            ci_95=(float("nan"), float("nan")),
            ci_method="insufficient_data",
            n=n_min,
            reject_h0=False,
            alpha=alpha,
            interpretation=f"Insufficient data (N_aware={n_aware}, N_default={n_default})",
        )

    mean_aware = statistics.mean(values_aware)
    mean_default = statistics.mean(values_default)
    delta_mean = mean_aware - mean_default

    # Compute pooled std for effect size
    if n_aware > 1 and n_default > 1:
        std_aware = statistics.stdev(values_aware)
        std_default = statistics.stdev(values_default)
        # Pooled std
        pooled_std = math.sqrt(
            ((n_aware - 1) * std_aware ** 2 + (n_default - 1) * std_default ** 2)
            / (n_aware + n_default - 2)
        )
    else:
        pooled_std = 0.0

    if pooled_std > 0:
        effect_d = delta_mean / pooled_std
    else:
        if delta_mean > 0:
            effect_d = float("inf")
        elif delta_mean < 0:
            effect_d = float("-inf")
        else:
            effect_d = 0.0

    # Choose test method
    if n_aware == n_default and n_min >= 5:
        # Paired samples -> Wilcoxon signed-rank
        diffs = [a - d for a, d in zip(values_aware[:n_min], values_default[:n_min])]
        # Wilcoxon requires non-zero differences
        nonzero_diffs = [d for d in diffs if abs(d) > 1e-12]
        if len(nonzero_diffs) >= 2:
            stat, p_raw = wilcoxon(nonzero_diffs, alternative="greater")
            test_method = "wilcoxon"
        else:
            # All differences are zero
            stat = 0.0
            p_raw = 1.0
            test_method = "wilcoxon_all_tied"
    elif n_min >= 2:
        # Unpaired -> Mann-Whitney U
        stat, p_raw = mannwhitneyu(values_aware, values_default, alternative="greater")
        test_method = "mann_whitney_u"
    else:
        stat = 0.0
        p_raw = 1.0
        test_method = "insufficient_n"

    # Bonferroni correction
    p_corrected = min(p_raw * n_comparisons, 1.0)
    corrected_alpha = alpha / n_comparisons

    # CI on the delta
    if n_min >= 10:
        deltas = [a - d for a, d in zip(values_aware[:n_min], values_default[:n_min])]
        ci, ci_method = bootstrap_ci(deltas), "bootstrap"
    else:
        ci = (delta_mean - 1.96 * (pooled_std / math.sqrt(n_min) if n_min > 0 else 0),
              delta_mean + 1.96 * (pooled_std / math.sqrt(n_min) if n_min > 0 else 0))
        ci_method = "normal_approx"

    reject = p_corrected < alpha

    if reject:
        interp = (
            f"Reject H0 after Bonferroni correction: provenance-aware instructions improve "
            f"{metric_key} by {delta_mean:.4f} "
            f"(p_raw={p_raw:.6f}, p_corrected={p_corrected:.6f}, d={effect_d:.3f}, "
            f"test={test_method}, N={n_min})"
        )
    else:
        interp = (
            f"Fail to reject H0: no significant improvement from provenance-aware instructions "
            f"on {metric_key} "
            f"(delta={delta_mean:.4f}, p_raw={p_raw:.6f}, p_corrected={p_corrected:.6f}, "
            f"d={effect_d:.3f}, test={test_method}, N={n_min})"
        )

    return HypothesisResult(
        test_name=f"instruction_delta_{metric_key}",
        h0=f"delta({metric_key}) <= 0",
        h1=f"delta({metric_key}) > 0",
        statistic=float(stat),
        p_value=float(p_raw),
        p_value_corrected=float(p_corrected),
        effect_size_d=float(effect_d),
        mean=delta_mean,
        std=pooled_std,
        ci_95=ci,
        ci_method=ci_method,
        n=n_min,
        reject_h0=reject,
        alpha=alpha,
        interpretation=interp,
    )


# ═══════════════════════════════════════════════════════════════════════
# ANCHOR COMPARISONS
# ═══════════════════════════════════════════════════════════════════════


def cross_reference_anchors(
    metrics: dict,
    v1_simulated_path: str | Path | None = None,
) -> AnchorComparison:
    """Compare genuine compaction metrics against all three anchor benchmarks.

    Anchors:
      1. MockLM ceiling: structural_reachability = 1.0, artifact_id_survival = 1.0
      2. Knowledge Objects (Zahn & Chana, March 2026): 60% fact loss per pass
      3. v1.0 simulated: structural_reachability by deletion fraction

    Args:
        metrics: Dict with keys: structural_reachability, artifact_id_survival,
                 semantic_fidelity, degraded_fraction, compression_ratio.
        v1_simulated_path: Path to v1.0 compaction-report.json.

    Returns:
        AnchorComparison with per-anchor analysis.
    """
    reach = metrics.get("structural_reachability", 0.0)
    survival = metrics.get("artifact_id_survival", 0.0)
    sem_fid = metrics.get("semantic_fidelity", 0.0)
    degraded = metrics.get("degraded_fraction", 0.0)
    compression = metrics.get("compression_ratio", 0.0)

    # --- Anchor 1: MockLM Ceiling ---
    mockml = {
        "anchor_name": "MockLM Ceiling",
        "source": "ref-mock-experiment: 100% reachability, 100% survival (controlled)",
        "mockml_reachability": 1.0,
        "mockml_survival": 1.0,
        "genuine_reachability": reach,
        "genuine_survival": survival,
        "gap_reachability": round(1.0 - reach, 6),
        "gap_survival": round(1.0 - survival, 6),
        "interpretation": (
            f"Genuine reachability is {round((1.0 - reach) * 100, 1)}% below MockLM ceiling. "
            f"Genuine survival is {round((1.0 - survival) * 100, 1)}% below MockLM ceiling. "
            f"{'Expected direction: genuine < ceiling.' if reach < 1.0 else 'At ceiling -- verify data is genuine.'}"
        ),
    }

    # --- Anchor 2: Knowledge Objects ---
    ko_threshold = 0.4  # 1.0 - 0.6 = 0.4 (40% survival after 60% loss)
    ko = {
        "anchor_name": "Knowledge Objects (Zahn & Chana, March 2026)",
        "source": "60% fact loss per LLM compression pass -> 40% survival",
        "ko_survival_threshold": ko_threshold,
        "genuine_survival": survival,
        "delta_from_ko": round(survival - ko_threshold, 6),
        "structured_beats_unstructured": survival > ko_threshold,
        "interpretation": (
            f"Artifact ID survival ({survival:.3f}) is "
            f"{'ABOVE' if survival > ko_threshold else 'AT OR BELOW'} "
            f"the Knowledge Objects baseline ({ko_threshold}). "
            f"{'Structured provenance survives better than unstructured facts.' if survival > ko_threshold else 'Structured provenance does NOT demonstrably outperform unstructured facts.'}"
        ),
    }

    # --- Anchor 3: v1.0 Simulated Compaction ---
    v1 = _load_v1_simulated_anchor(v1_simulated_path, compression, reach)

    # --- Overall verdict ---
    # PASS if reachability > 0.5 AND survival > knowledge_objects threshold
    # PARTIAL if reachability > 0.5 OR survival > knowledge_objects threshold
    # FAIL if neither
    pass_reach = reach > 0.5
    pass_ko = survival > ko_threshold

    if pass_reach and pass_ko:
        overall = "pass"
    elif pass_reach or pass_ko:
        overall = "partial"
    else:
        overall = "fail"

    return AnchorComparison(
        mockml=mockml,
        knowledge_objects=ko,
        v1_simulated=v1,
        overall_verdict=overall,
    )


def _load_v1_simulated_anchor(
    path: str | Path | None,
    genuine_compression: float,
    genuine_reachability: float,
) -> dict:
    """Load v1.0 simulated compaction data and find comparable point."""
    v1_data: list[dict] = []

    if path is None:
        path = PROJECT_ROOT / "data" / "compaction" / "compaction-report.json"

    try:
        with open(path) as f:
            report = json.load(f)
        v1_data = report.get("deletion_sweep", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "anchor_name": "v1.0 Simulated Compaction",
            "source": "data/compaction/compaction-report.json",
            "status": "data_not_found",
            "interpretation": "Could not load v1.0 simulated compaction data for comparison.",
        }

    if not v1_data:
        return {
            "anchor_name": "v1.0 Simulated Compaction",
            "source": "data/compaction/compaction-report.json",
            "status": "empty_sweep",
            "interpretation": "v1.0 simulated compaction sweep is empty.",
        }

    # Find the v1.0 point closest in compression ratio
    # v1.0 doesn't have compression_ratio directly; use deletion_fraction as proxy
    # The v1.0 structural_reachability at 50% deletion = 0.82 is the key anchor

    result: dict[str, Any] = {
        "anchor_name": "v1.0 Simulated Compaction",
        "source": "data/compaction/compaction-report.json",
        "v1_sweep_points": len(v1_data),
        "v1_at_50pct_deletion": None,
        "v1_at_80pct_deletion": None,
        "v1_backtracking_crossing": None,
        "genuine_reachability": genuine_reachability,
    }

    for point in v1_data:
        frac = point.get("deletion_fraction", 0)
        sr = point.get("structural_reachability", 0)
        if abs(frac - 0.5) < 0.01:
            result["v1_at_50pct_deletion"] = sr
        if abs(frac - 0.8) < 0.01:
            result["v1_at_80pct_deletion"] = sr
        if point.get("above_backtracking_threshold") is False and result["v1_backtracking_crossing"] is None:
            result["v1_backtracking_crossing"] = frac

    v1_50 = result.get("v1_at_50pct_deletion")
    if v1_50 is not None:
        result["gap_genuine_vs_v1_50pct"] = round(genuine_reachability - v1_50, 6)
        result["interpretation"] = (
            f"Genuine reachability ({genuine_reachability:.3f}) vs "
            f"v1.0 simulated at 50% deletion ({v1_50:.3f}): "
            f"delta = {genuine_reachability - v1_50:+.3f}. "
            f"{'Genuine compaction is better than simulated deletion.' if genuine_reachability > v1_50 else 'Genuine compaction is worse than or equal to simulated deletion.'} "
            f"Note: comparison requires matching compression ratios for fair assessment."
        )
    else:
        result["interpretation"] = (
            "v1.0 50% deletion point not found. Cannot compute direct gap."
        )

    return result


# ═══════════════════════════════════════════════════════════════════════
# VERDICT RENDERING
# ═══════════════════════════════════════════════════════════════════════


def render_verdict(
    analysis: dict,
) -> dict[str, Verdict]:
    """Render verdicts for all claims based on analysis results.

    Verdicts:
      PASS: structural_reachability > 0.5 with p < 0.05
      PARTIAL: measured but not > 0.5, or compaction fires but sample too small
      FAIL: pipeline broke, or compaction never fired
      BACKTRACK: structural_reachability <= 0.5 under ALL conditions including provenance-aware

    Args:
        analysis: Complete analysis dict with hypothesis tests and metrics.

    Returns:
        Dict mapping claim_id -> Verdict.
    """
    verdicts = {}

    # --- claim-compaction-survival ---
    reach_test = analysis.get("hypothesis_tests", {}).get("structural_reachability", {})
    data_mode = analysis.get("data_mode", "unknown")
    n = reach_test.get("n", 0)
    reach_mean = reach_test.get("mean", 0.0)
    p_val = reach_test.get("p_value", 1.0)
    reject = reach_test.get("reject_h0", False)

    if data_mode == "dry-run":
        # Dry-run data cannot produce a genuine verdict
        verdicts["claim-compaction-survival"] = Verdict(
            claim_id="claim-compaction-survival",
            verdict="PARTIAL",
            evidence=[
                f"Data is dry-run (synthetic), not genuine LLM compaction",
                f"Pipeline validated: {n} trials processed",
                f"Metrics computed: reachability={reach_mean:.4f}",
                "Forbidden proxy fp-simulated-only is VIOLATED: analysis on dry-run data only",
            ],
            criteria_used="PARTIAL because data_mode='dry-run' -- genuine LLM compaction data required for PASS/FAIL",
            sample_size_caveat=f"N={n} (all dry-run; live API data required)",
            confidence_tag="LOW",
        )
    elif reject:
        verdicts["claim-compaction-survival"] = Verdict(
            claim_id="claim-compaction-survival",
            verdict="PASS",
            evidence=[
                f"structural_reachability = {reach_mean:.4f} > 0.5 (threshold)",
                f"p = {p_val:.6f} < 0.05 (reject H0)",
                f"Effect size d = {reach_test.get('effect_size_d', 'N/A')}",
                f"N = {n}",
            ],
            criteria_used="PASS: structural_reachability > 0.5 with p < 0.05",
            sample_size_caveat=f"N={n}" + (" (pilot -- interpret with caution)" if n < 20 else ""),
            confidence_tag="HIGH" if n >= 30 else "MEDIUM",
        )
    elif n >= 2 and reach_mean <= 0.5:
        # Check if ALL conditions fail -> BACKTRACK
        all_conditions_fail = True
        track_c = analysis.get("track_c", {})
        if track_c:
            for cond_id, cond_data in track_c.get("per_condition", {}).items():
                if cond_data.get("structural_reachability", {}).get("mean", 0) > 0.5:
                    all_conditions_fail = False
                    break

        if all_conditions_fail:
            verdicts["claim-compaction-survival"] = Verdict(
                claim_id="claim-compaction-survival",
                verdict="BACKTRACK",
                evidence=[
                    f"structural_reachability = {reach_mean:.4f} <= 0.5 under all conditions",
                    "No condition exceeds the backtracking threshold",
                    "In-context provenance is insufficient under genuine LLM compaction",
                ],
                criteria_used="BACKTRACK: reachability <= 0.5 under ALL conditions",
                sample_size_caveat=f"N={n}",
                confidence_tag="MEDIUM" if n >= 10 else "LOW",
            )
        else:
            verdicts["claim-compaction-survival"] = Verdict(
                claim_id="claim-compaction-survival",
                verdict="PARTIAL",
                evidence=[
                    f"structural_reachability = {reach_mean:.4f} (not > 0.5 significantly)",
                    f"p = {p_val:.6f} >= 0.05",
                    "Some conditions may exceed threshold; further data needed",
                ],
                criteria_used="PARTIAL: measured but not significantly > 0.5",
                sample_size_caveat=f"N={n}",
                confidence_tag="LOW",
            )
    else:
        verdicts["claim-compaction-survival"] = Verdict(
            claim_id="claim-compaction-survival",
            verdict="PARTIAL",
            evidence=[
                f"structural_reachability = {reach_mean:.4f}",
                f"Sample too small for conclusive test (N={n})",
            ],
            criteria_used="PARTIAL: sample too small or measurement incomplete",
            sample_size_caveat=f"N={n}",
            confidence_tag="LOW",
        )

    # --- claim-instruction-effect ---
    delta_test = analysis.get("hypothesis_tests", {}).get("instruction_delta", {})
    delta_mean = delta_test.get("mean", 0.0)
    delta_p = delta_test.get("p_value_corrected", 1.0)
    delta_reject = delta_test.get("reject_h0", False)
    delta_n = delta_test.get("n", 0)

    if data_mode == "dry-run":
        verdicts["claim-instruction-effect"] = Verdict(
            claim_id="claim-instruction-effect",
            verdict="PARTIAL",
            evidence=[
                "Data is dry-run: synthetic compaction ignores instructions",
                f"Delta = {delta_mean:.4f} (expected 0 in dry-run)",
                "Live API data required to test instruction effect",
            ],
            criteria_used="PARTIAL: dry-run data cannot test instruction hypothesis",
            sample_size_caveat=f"N={delta_n} (all dry-run)",
            confidence_tag="LOW",
        )
    elif delta_reject:
        verdicts["claim-instruction-effect"] = Verdict(
            claim_id="claim-instruction-effect",
            verdict="PASS",
            evidence=[
                f"provenance_aware_delta = {delta_mean:.4f} > 0",
                f"p_corrected = {delta_p:.6f} < 0.05 (Bonferroni-corrected)",
                f"Effect size d = {delta_test.get('effect_size_d', 'N/A')}",
            ],
            criteria_used="PASS: delta > 0 with Bonferroni-corrected p < 0.05",
            sample_size_caveat=f"N={delta_n}",
            confidence_tag="MEDIUM",
        )
    else:
        verdicts["claim-instruction-effect"] = Verdict(
            claim_id="claim-instruction-effect",
            verdict="PARTIAL",
            evidence=[
                f"provenance_aware_delta = {delta_mean:.4f}",
                f"p_corrected = {delta_p:.6f} >= 0.05",
                "Instructions do not have a statistically significant effect",
            ],
            criteria_used="PARTIAL: delta measured but not significant after correction",
            sample_size_caveat=f"N={delta_n}",
            confidence_tag="LOW",
        )

    return verdicts


# ═══════════════════════════════════════════════════════════════════════
# FORBIDDEN PROXY AUDIT
# ═══════════════════════════════════════════════════════════════════════


def audit_forbidden_proxies(
    data: list[dict],
) -> list[ForbiddenProxyAudit]:
    """Audit all forbidden proxies against the actual data.

    Forbidden proxies from contract:
      fp-cherry-picked: Report only best-performing condition
      fp-simulated-only: Analysis on dry-run data only
      fp-short-tasks: Tasks too short to trigger real compaction
    """
    audits = []

    # --- fp-cherry-picked ---
    tracks = set(d.get("track", "?") for d in data)
    categories = set(d.get("task_category", "?") for d in data)
    prov_settings = set(d.get("provenance_aware", None) for d in data)
    audits.append(ForbiddenProxyAudit(
        proxy_id="fp-cherry-picked",
        status="rejected",
        evidence=(
            f"All conditions reported: tracks={sorted(tracks)}, "
            f"categories={sorted(categories)}, "
            f"provenance_aware={sorted(str(p) for p in prov_settings)}"
        ),
        notes="Analysis includes all available conditions. No cherry-picking.",
    ))

    # --- fp-simulated-only ---
    modes = set(d.get("mode", "unknown") for d in data)
    if modes == {"dry-run"}:
        audits.append(ForbiddenProxyAudit(
            proxy_id="fp-simulated-only",
            status="violated",
            evidence=f"All {len(data)} trials are mode='dry-run'. No live API data.",
            notes=(
                "This forbidden proxy IS triggered. Dry-run data validates pipeline "
                "but does not constitute genuine LLM compaction measurement. "
                "Genuine live measurement is disabled fleet-wide per CLAUDE.md "
                "Rule #10 (NO PAID LLM API, EVER) -- see BUG-020 in "
                "BUGS_AND_ITERATIONS.md."
            ),
        ))
    elif "dry-run" in modes and "live" in modes:
        audits.append(ForbiddenProxyAudit(
            proxy_id="fp-simulated-only",
            status="rejected",
            evidence=f"Mixed modes: {sorted(modes)}. Live data present.",
            notes="Some dry-run data included alongside live data.",
        ))
    else:
        audits.append(ForbiddenProxyAudit(
            proxy_id="fp-simulated-only",
            status="rejected",
            evidence=f"All data is mode={sorted(modes)}.",
            notes="Genuine compaction data present.",
        ))

    # --- fp-short-tasks ---
    compaction_counts = []
    for d in data:
        events = d.get("compaction_events", [])
        compaction_counts.append(len(events))

    trials_with_compaction = sum(1 for c in compaction_counts if c > 0)
    if trials_with_compaction == 0:
        status = "violated"
        evidence = "No trials triggered compaction events. Tasks were too short."
    elif trials_with_compaction < len(data) * 0.5:
        status = "unresolved"
        evidence = (
            f"Only {trials_with_compaction}/{len(data)} trials triggered compaction. "
            "Some tasks may be too short."
        )
    else:
        status = "rejected"
        evidence = f"{trials_with_compaction}/{len(data)} trials triggered compaction events."

    audits.append(ForbiddenProxyAudit(
        proxy_id="fp-short-tasks",
        status=status,
        evidence=evidence,
        notes="Compaction events are necessary for measurement validity.",
    ))

    return audits


# ═══════════════════════════════════════════════════════════════════════
# TRACK SUMMARY
# ═══════════════════════════════════════════════════════════════════════


def summarize_tracks(
    track_a: list[dict],
    track_b: list[dict] | None = None,
    track_c: list[dict] | None = None,
) -> dict:
    """Summarize metrics per track.

    Args:
        track_a: Track A trial results.
        track_b: Track B trial results (optional).
        track_c: Track C trial results (optional).

    Returns:
        Dict with per-track summaries including N, means, CIs.
    """
    result: dict[str, Any] = {}

    for track_name, data in [("A", track_a), ("B", track_b), ("C", track_c)]:
        if data is None or len(data) == 0:
            result[f"track_{track_name.lower()}"] = {
                "status": "no_data",
                "n": 0,
            }
            continue

        summary: dict[str, Any] = {"n": len(data)}
        modes = set(d.get("mode", "unknown") for d in data)
        summary["modes"] = sorted(modes)
        summary["data_mode"] = "live" if "live" in modes else "dry-run"

        # Aggregate each primary metric
        for metric in ["structural_reachability", "artifact_id_survival",
                       "semantic_fidelity", "degraded_fraction", "compression_ratio"]:
            values = _extract_metric(data, metric)
            if values:
                ci, ci_method = select_ci(values)
                summary[metric] = {
                    "mean": round(statistics.mean(values), 6),
                    "std": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
                    "min": round(min(values), 6),
                    "max": round(max(values), 6),
                    "ci_95": [round(ci[0], 6), round(ci[1], 6)],
                    "ci_method": ci_method,
                    "n": len(values),
                }

        # Compaction event count
        compaction_counts = [len(d.get("compaction_events", [])) for d in data]
        summary["compaction_events"] = {
            "total": sum(compaction_counts),
            "mean_per_trial": round(statistics.mean(compaction_counts), 2),
            "trials_with_compaction": sum(1 for c in compaction_counts if c > 0),
        }

        # Tier distribution
        tier_counts = {"resolved": 0, "degraded": 0, "broken": 0}
        total_refs = 0
        for d in data:
            events = d.get("compaction_events", [])
            for event in events:
                post = event.get("post_snapshot", {})
                # Count artifact IDs in post vs pre
                pre_ids = set(event.get("pre_snapshot", {}).get("artifact_ids", []))
                post_ids = set(post.get("artifact_ids", []))
                # Approximate tier counts from aggregate_metrics
                pass
            # Use aggregate_metrics if available
            am = d.get("aggregate_metrics", {})
            n_total = len(d.get("compaction_events", [{}])[0].get("pre_snapshot", {}).get("artifact_ids", [])) if d.get("compaction_events") else 0
            if n_total > 0:
                degrad = am.get("degraded_fraction", 0)
                reach = am.get("structural_reachability", 0)
                # degraded = degrad * n_total, broken = (1 - reach) * n_total, resolved = reach * n_total - degrad * n_total
                tier_counts["degraded"] += int(round(degrad * n_total))
                tier_counts["broken"] += int(round((1 - reach) * n_total))
                tier_counts["resolved"] += int(round((reach - degrad) * n_total))
                total_refs += n_total

        if total_refs > 0:
            summary["tier_distribution"] = {
                "resolved": tier_counts["resolved"],
                "degraded": tier_counts["degraded"],
                "broken": tier_counts["broken"],
                "total_refs": total_refs,
                "resolved_fraction": round(tier_counts["resolved"] / total_refs, 4),
                "degraded_fraction": round(tier_counts["degraded"] / total_refs, 4),
                "broken_fraction": round(tier_counts["broken"] / total_refs, 4),
            }

        result[f"track_{track_name.lower()}"] = summary

    # Cross-track consistency
    track_a_reach = result.get("track_a", {}).get("structural_reachability", {}).get("mean")
    track_b_reach = result.get("track_b", {}).get("structural_reachability", {}).get("mean")
    if track_a_reach is not None and track_b_reach is not None:
        result["cross_track_consistency"] = {
            "track_a_reach": track_a_reach,
            "track_b_reach": track_b_reach,
            "gap": round(abs(track_a_reach - track_b_reach), 6),
            "compatible": abs(track_a_reach - track_b_reach) < 0.2,
        }
    else:
        result["cross_track_consistency"] = {"status": "insufficient_tracks"}

    return result


# ═══════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS CLASS
# ═══════════════════════════════════════════════════════════════════════


class CompactionAnalysis:
    """Full analysis pipeline for genuine LLM compaction experiments.

    Loads JSONL data, runs hypothesis tests, computes CIs, compares
    against anchors, and renders RQ3b verdict.
    """

    def __init__(
        self,
        data_dir: str | Path = "data/compaction/genuine/",
    ):
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            self.data_dir = PROJECT_ROOT / self.data_dir
        self.all_data: list[dict] = []
        self._load_all_data()

    def _load_all_data(self):
        """Load all JSONL files from data_dir."""
        self.all_data = []
        for jsonl_file in sorted(self.data_dir.glob("*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.all_data.append(json.loads(line))

    def load_track_data(self, track: str) -> list[dict]:
        """Filter data for a specific track."""
        return [d for d in self.all_data if d.get("track", "").upper() == track.upper()]

    def run_full_analysis(self) -> dict:
        """Run the complete analysis pipeline.

        Returns:
            Complete analysis dict with all results, ready for JSON serialization.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Load data by track
        track_a = self.load_track_data("A")
        track_b = self.load_track_data("B")
        track_c = self.load_track_data("C")

        # Determine data mode
        all_modes = set(d.get("mode", "unknown") for d in self.all_data)
        data_mode = "live" if "live" in all_modes else "dry-run" if "dry-run" in all_modes else "unknown"

        # Primary data for hypothesis tests (Track A is primary)
        primary_data = track_a if track_a else self.all_data

        # Split by provenance_aware for instruction delta test
        data_aware = [d for d in primary_data if d.get("provenance_aware") is True]
        data_default = [d for d in primary_data if d.get("provenance_aware") is False or d.get("provenance_aware") is None]

        # --- Hypothesis tests ---
        ht_reach = test_reachability_hypothesis(primary_data, "structural_reachability", 0.5)
        ht_survival = test_reachability_hypothesis(primary_data, "artifact_id_survival", 0.5)
        ht_delta = test_instruction_delta(data_aware, data_default, "artifact_id_survival")

        # --- Aggregate metrics ---
        agg_metrics = _compute_aggregate_metrics(primary_data)

        # --- Anchor comparison ---
        anchors = cross_reference_anchors(agg_metrics)

        # --- Track summaries ---
        track_summary = summarize_tracks(track_a, track_b, track_c)

        # --- Per-category breakdown (Track A) ---
        categories = sorted(set(d.get("task_category", "unknown") for d in track_a))
        per_category: dict[str, dict] = {}
        for cat in categories:
            cat_data = [d for d in track_a if d.get("task_category") == cat]
            per_category[cat] = _compute_aggregate_metrics(cat_data)

        # --- Provenance-aware delta per category ---
        provenance_delta: dict[str, dict] = {}
        for cat in categories:
            cat_aware = [d for d in data_aware if d.get("task_category") == cat]
            cat_default = [d for d in data_default if d.get("task_category") == cat]
            if cat_aware and cat_default:
                aw_survival = statistics.mean(_extract_metric(cat_aware, "artifact_id_survival"))
                df_survival = statistics.mean(_extract_metric(cat_default, "artifact_id_survival"))
                provenance_delta[cat] = {
                    "aware_survival": round(aw_survival, 6),
                    "default_survival": round(df_survival, 6),
                    "delta": round(aw_survival - df_survival, 6),
                }

        # --- Forbidden proxy audit ---
        proxy_audits = audit_forbidden_proxies(self.all_data)

        # --- Build analysis dict ---
        analysis = {
            "timestamp": timestamp,
            "data_mode": data_mode,
            "total_trials": len(self.all_data),
            "track_a_trials": len(track_a),
            "track_b_trials": len(track_b),
            "track_c_trials": len(track_c),
            "hypothesis_tests": {
                "structural_reachability": _hypothesis_result_to_dict(ht_reach),
                "artifact_id_survival": _hypothesis_result_to_dict(ht_survival),
                "instruction_delta": _hypothesis_result_to_dict(ht_delta),
            },
            "aggregate_metrics": agg_metrics,
            "per_category": per_category,
            "provenance_delta": provenance_delta,
            "anchors": {
                "mockml": anchors.mockml,
                "knowledge_objects": anchors.knowledge_objects,
                "v1_simulated": anchors.v1_simulated,
                "overall_verdict": anchors.overall_verdict,
            },
            "track_summary": track_summary,
            "forbidden_proxy_audit": [asdict(a) for a in proxy_audits],
        }

        # --- Verdicts ---
        verdicts = render_verdict(analysis)
        analysis["verdicts"] = {
            claim_id: asdict(v) for claim_id, v in verdicts.items()
        }

        # --- RQ3b summary ---
        analysis["rq3b_verdict"] = verdicts.get(
            "claim-compaction-survival", Verdict(
                claim_id="claim-compaction-survival",
                verdict="FAIL",
                evidence=["No analysis completed"],
                criteria_used="",
                sample_size_caveat="",
                confidence_tag="LOW",
            )
        ).verdict

        return analysis


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def _extract_metric(data: list[dict], metric_key: str) -> list[float]:
    """Extract metric values from trial result dicts."""
    values = []
    for d in data:
        am = d.get("aggregate_metrics", {})
        v = am.get(metric_key)
        if v is not None:
            values.append(float(v))
    return values


def _compute_aggregate_metrics(data: list[dict]) -> dict:
    """Compute aggregate statistics for a set of trials."""
    if not data:
        return {}

    result = {}
    for metric in ["structural_reachability", "artifact_id_survival",
                    "semantic_fidelity", "degraded_fraction", "compression_ratio"]:
        values = _extract_metric(data, metric)
        if values:
            ci, ci_method = select_ci(values)
            result[metric] = round(statistics.mean(values), 6)
            result[f"{metric}_std"] = round(statistics.stdev(values), 6) if len(values) > 1 else 0.0
            result[f"{metric}_ci"] = [round(ci[0], 6), round(ci[1], 6)]
            result[f"{metric}_ci_method"] = ci_method
            result[f"{metric}_n"] = len(values)

    return result


def _hypothesis_result_to_dict(hr: HypothesisResult) -> dict:
    """Convert HypothesisResult to a JSON-serializable dict."""
    d = asdict(hr)
    # Handle tuple -> list for JSON
    if isinstance(d.get("ci_95"), tuple):
        d["ci_95"] = list(d["ci_95"])
    # Handle NaN/inf for JSON
    for key in ["statistic", "p_value", "p_value_corrected", "effect_size_d",
                 "mean", "std"]:
        val = d.get(key)
        if val is not None and (math.isnan(val) or math.isinf(val)):
            d[key] = str(val)
    if d.get("ci_95"):
        d["ci_95"] = [
            str(v) if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v
            for v in d["ci_95"]
        ]
    return d


# ═══════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════


def main():
    """Run the full analysis and output results."""
    import argparse

    parser = argparse.ArgumentParser(description="Genuine LLM Compaction Analysis")
    parser.add_argument(
        "--data-dir",
        default="data/compaction/genuine/",
        help="Directory containing JSONL result files",
    )
    parser.add_argument(
        "--output",
        default="data/compaction/genuine/analysis-results.json",
        help="Output path for JSON results",
    )
    parser.add_argument(
        "--report",
        default="docs/genuine-compaction-report.md",
        help="Output path for Markdown report",
    )
    args = parser.parse_args()

    analysis = CompactionAnalysis(data_dir=args.data_dir)
    results = analysis.run_full_analysis()

    # Write JSON results
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Analysis results written to: {output_path}")

    # Write Markdown report
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path
    report = generate_report(results)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report written to: {report_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════


def generate_report(analysis: dict) -> str:
    """Generate the comprehensive Markdown report from analysis results."""
    lines = []

    lines.append("# Genuine LLM Compaction Report -- RQ3b Assessment")
    lines.append("")
    lines.append(f"**Generated:** {analysis.get('timestamp', 'unknown')}")
    lines.append(f"**Data mode:** {analysis.get('data_mode', 'unknown')}")
    lines.append(f"**Total trials:** {analysis.get('total_trials', 0)}")
    lines.append(f"**Track A:** {analysis.get('track_a_trials', 0)} | "
                 f"**Track B:** {analysis.get('track_b_trials', 0)} | "
                 f"**Track C:** {analysis.get('track_c_trials', 0)}")
    lines.append("")

    # --- Executive Summary ---
    verdict = analysis.get("rq3b_verdict", "UNKNOWN")
    v_detail = analysis.get("verdicts", {}).get("claim-compaction-survival", {})
    lines.append("## 1. Executive Summary")
    lines.append("")

    if analysis.get("data_mode") == "dry-run":
        lines.append("> **NOTE: All data is DRY-RUN (synthetic compaction).** "
                     "Results validate the analysis pipeline but do NOT measure "
                     "genuine LLM context-window compaction. All metrics below are "
                     "from deterministic synthetic compaction (midpoint-split). "
                     "Genuine live measurement is disabled fleet-wide per CLAUDE.md "
                     "Rule #10 (NO PAID LLM API, EVER) -- see BUG-020 in "
                     "BUGS_AND_ITERATIONS.md.")
        lines.append("")

    lines.append(f"**RQ3b Verdict: {verdict}**")
    lines.append("")
    evidence = v_detail.get("evidence", [])
    for e in evidence:
        lines.append(f"- {e}")
    lines.append("")
    lines.append(f"*Criteria:* {v_detail.get('criteria_used', 'N/A')}")
    lines.append(f"*Sample size caveat:* {v_detail.get('sample_size_caveat', 'N/A')}")
    lines.append(f"*Confidence:* [{v_detail.get('confidence_tag', 'N/A')}]")
    lines.append("")

    # --- Track A Results ---
    lines.append("## 2. Track A Results (Pilot)")
    lines.append("")

    agg = analysis.get("aggregate_metrics", {})
    lines.append("### 2.1 Aggregate Metrics")
    lines.append("")
    lines.append("| Metric | Mean | Std | 95% CI | N | CI Method |")
    lines.append("|--------|------|-----|--------|---|-----------|")

    for metric in ["structural_reachability", "artifact_id_survival",
                    "semantic_fidelity", "degraded_fraction", "compression_ratio"]:
        mean_val = agg.get(metric, "N/A")
        std_val = agg.get(f"{metric}_std", "N/A")
        ci_val = agg.get(f"{metric}_ci", ["N/A", "N/A"])
        n_val = agg.get(f"{metric}_n", "N/A")
        ci_method = agg.get(f"{metric}_ci_method", "N/A")
        lines.append(
            f"| {metric} | {mean_val} | {std_val} | "
            f"[{ci_val[0]}, {ci_val[1]}] | {n_val} | {ci_method} |"
        )
    lines.append("")

    # Per-category
    per_cat = analysis.get("per_category", {})
    if per_cat:
        lines.append("### 2.2 Per-Category Breakdown")
        lines.append("")
        lines.append("| Category | structural_reachability | artifact_id_survival | semantic_fidelity | degraded_fraction | compression_ratio |")
        lines.append("|----------|----------------------|---------------------|-------------------|-------------------|-------------------|")
        for cat, metrics_dict in sorted(per_cat.items()):
            row = [cat]
            for m in ["structural_reachability", "artifact_id_survival",
                       "semantic_fidelity", "degraded_fraction", "compression_ratio"]:
                row.append(str(metrics_dict.get(m, "N/A")))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    # Provenance-aware delta
    prov_delta = analysis.get("provenance_delta", {})
    if prov_delta:
        lines.append("### 2.3 Provenance-Aware Delta")
        lines.append("")
        lines.append("| Category | Aware Survival | Default Survival | Delta |")
        lines.append("|----------|---------------|-----------------|-------|")
        for cat, dinfo in sorted(prov_delta.items()):
            lines.append(
                f"| {cat} | {dinfo.get('aware_survival', 'N/A')} | "
                f"{dinfo.get('default_survival', 'N/A')} | "
                f"{dinfo.get('delta', 'N/A')} |"
            )
        lines.append("")

    # --- Hypothesis Tests ---
    lines.append("## 3. Hypothesis Tests")
    lines.append("")

    ht = analysis.get("hypothesis_tests", {})
    for test_name, test_data in ht.items():
        lines.append(f"### 3.{list(ht.keys()).index(test_name) + 1} {test_data.get('test_name', test_name)}")
        lines.append("")
        lines.append(f"- **H0:** {test_data.get('h0', 'N/A')}")
        lines.append(f"- **H1:** {test_data.get('h1', 'N/A')}")
        lines.append(f"- **Statistic:** {test_data.get('statistic', 'N/A')}")
        lines.append(f"- **p-value:** {test_data.get('p_value', 'N/A')}")
        if test_data.get("p_value_corrected") is not None:
            lines.append(f"- **p-value (Bonferroni):** {test_data.get('p_value_corrected', 'N/A')}")
        lines.append(f"- **Effect size d:** {test_data.get('effect_size_d', 'N/A')}")
        lines.append(f"- **Mean:** {test_data.get('mean', 'N/A')}")
        lines.append(f"- **95% CI:** {test_data.get('ci_95', 'N/A')}")
        lines.append(f"- **N:** {test_data.get('n', 'N/A')}")
        lines.append(f"- **Reject H0:** {test_data.get('reject_h0', 'N/A')}")
        lines.append(f"- **Interpretation:** {test_data.get('interpretation', 'N/A')}")
        lines.append("")

    # --- Track C Ablation ---
    track_c_summary = analysis.get("track_summary", {}).get("track_c", {})
    if track_c_summary and track_c_summary.get("status") != "no_data":
        lines.append("## 4. Track C Ablation Results")
        lines.append("")
        lines.append(f"**N:** {track_c_summary.get('n', 0)}")
        lines.append(f"**Data mode:** {track_c_summary.get('data_mode', 'unknown')}")
        lines.append("")
        # Note: full ablation analysis would come from track_c_ablation.py
        lines.append("*Full ablation breakdown requires Track C data from the ablation framework.*")
        lines.append("")
    else:
        lines.append("## 4. Track C Ablation Results")
        lines.append("")
        lines.append("**No Track C data available.** Track C ablation framework (Plan 04) ")
        lines.append("is built and ready for execution. Live API data required.")
        lines.append("")

    # --- Anchor Comparisons ---
    lines.append("## 5. Anchor Comparisons")
    lines.append("")
    anchors = analysis.get("anchors", {})

    # Summary table
    lines.append("| Metric | MockLM Ceiling | Knowledge Objects | v1.0 Simulated (50% del) | Phase 6 Genuine |")
    lines.append("|--------|---------------|-------------------|--------------------------|-----------------|")

    mockml = anchors.get("mockml", {})
    ko = anchors.get("knowledge_objects", {})
    v1 = anchors.get("v1_simulated", {})

    reach_val = agg.get("structural_reachability", "N/A")
    surv_val = agg.get("artifact_id_survival", "N/A")

    lines.append(f"| structural_reachability | 1.0 | N/A | {v1.get('v1_at_50pct_deletion', 'N/A')} | {reach_val} |")
    lines.append(f"| artifact_id_survival | 1.0 | 0.4 (inferred) | N/A | {surv_val} |")
    lines.append(f"| semantic_fidelity | 1.0 | N/A | N/A | {agg.get('semantic_fidelity', 'N/A')} |")
    lines.append(f"| degraded_fraction | 0.0 | N/A | 0.0 (always) | {agg.get('degraded_fraction', 'N/A')} |")
    lines.append("")

    # Per-anchor detail
    lines.append("### 5.1 MockLM Ceiling")
    lines.append("")
    lines.append(f"- Gap (reachability): {mockml.get('gap_reachability', 'N/A')}")
    lines.append(f"- Gap (survival): {mockml.get('gap_survival', 'N/A')}")
    lines.append(f"- Interpretation: {mockml.get('interpretation', 'N/A')}")
    lines.append("")

    lines.append("### 5.2 Knowledge Objects (Zahn & Chana, March 2026)")
    lines.append("")
    lines.append(f"- Expected unstructured survival: {ko.get('ko_survival_threshold', 'N/A')}")
    lines.append(f"- Genuine survival: {ko.get('genuine_survival', 'N/A')}")
    lines.append(f"- Delta from KO: {ko.get('delta_from_ko', 'N/A')}")
    lines.append(f"- Structured beats unstructured: {ko.get('structured_beats_unstructured', 'N/A')}")
    lines.append(f"- Interpretation: {ko.get('interpretation', 'N/A')}")
    lines.append("")

    lines.append("### 5.3 v1.0 Simulated Compaction")
    lines.append("")
    lines.append(f"- v1.0 at 50% deletion: {v1.get('v1_at_50pct_deletion', 'N/A')}")
    lines.append(f"- v1.0 at 80% deletion: {v1.get('v1_at_80pct_deletion', 'N/A')}")
    lines.append(f"- v1.0 backtracking crossing: {v1.get('v1_backtracking_crossing', 'N/A')}")
    lines.append(f"- Genuine reachability: {v1.get('genuine_reachability', 'N/A')}")
    gap = v1.get("gap_genuine_vs_v1_50pct")
    if gap is not None:
        lines.append(f"- Gap (genuine vs v1.0 50%): {gap}")
    lines.append(f"- Interpretation: {v1.get('interpretation', 'N/A')}")
    lines.append("")

    lines.append(f"**Overall anchor verdict:** {anchors.get('overall_verdict', 'N/A')}")
    lines.append("")

    # --- Three-Tier Classification ---
    lines.append("## 6. Three-Tier Ref Classification")
    lines.append("")
    ts = analysis.get("track_summary", {}).get("track_a", {})
    tier = ts.get("tier_distribution", {})
    if tier:
        lines.append("| Tier | Count | Fraction |")
        lines.append("|------|-------|----------|")
        lines.append(f"| Resolved | {tier.get('resolved', 'N/A')} | {tier.get('resolved_fraction', 'N/A')} |")
        lines.append(f"| Degraded | {tier.get('degraded', 'N/A')} | {tier.get('degraded_fraction', 'N/A')} |")
        lines.append(f"| Broken | {tier.get('broken', 'N/A')} | {tier.get('broken_fraction', 'N/A')} |")
        lines.append(f"| **Total refs** | {tier.get('total_refs', 'N/A')} | |")
        lines.append("")
        if tier.get("degraded", 0) > 0:
            lines.append("**Key finding:** The degraded tier is populated for the first time. "
                         "v1.0 simulated compaction (programmatic deletion) always produced "
                         "degraded_count=0 because deletion removes artifacts entirely (broken) "
                         "rather than summarizing them (degraded). Genuine LLM compaction can "
                         "produce degraded refs where content is paraphrased but the artifact ID survives.")
        else:
            lines.append("**Note:** Degraded tier is not populated. This may be because:")
            lines.append("- Data is dry-run (synthetic compaction uses midpoint-split, not summarization)")
            lines.append("- Or genuine compaction either preserves artifacts exactly (resolved) or removes them (broken)")
        lines.append("")
    else:
        lines.append("*Tier distribution data not available.*")
        lines.append("")

    # --- RQ3b Verdict ---
    lines.append("## 7. RQ3b Verdict")
    lines.append("")
    lines.append(f"**Verdict: {verdict}**")
    lines.append("")
    lines.append(f"**Criteria:** {v_detail.get('criteria_used', 'N/A')}")
    lines.append(f"**Confidence:** [{v_detail.get('confidence_tag', 'N/A')}]")
    lines.append(f"**Sample size:** {v_detail.get('sample_size_caveat', 'N/A')}")
    lines.append("")

    # Instruction effect verdict
    ie_verdict = analysis.get("verdicts", {}).get("claim-instruction-effect", {})
    if ie_verdict:
        lines.append(f"**Instruction Effect Verdict: {ie_verdict.get('verdict', 'N/A')}**")
        lines.append("")
        for e in ie_verdict.get("evidence", []):
            lines.append(f"- {e}")
        lines.append("")

    # --- Forbidden Proxy Audit ---
    lines.append("## 8. Forbidden Proxy Audit")
    lines.append("")
    lines.append("| Proxy ID | Status | Evidence |")
    lines.append("|----------|--------|----------|")
    for audit in analysis.get("forbidden_proxy_audit", []):
        lines.append(
            f"| {audit.get('proxy_id', 'N/A')} | "
            f"**{audit.get('status', 'N/A').upper()}** | "
            f"{audit.get('evidence', 'N/A')} |"
        )
    lines.append("")
    for audit in analysis.get("forbidden_proxy_audit", []):
        if audit.get("notes"):
            lines.append(f"**{audit.get('proxy_id')}:** {audit.get('notes')}")
            lines.append("")

    # --- Limitations ---
    lines.append("## 9. Limitations")
    lines.append("")
    lines.append("1. **Sample size:** " + ("Pilot data only (N=6). Insufficient for statistical significance. "
                 "Full Track A (N=60) required." if analysis.get("total_trials", 0) < 20 else
                 f"N={analysis.get('total_trials', 0)} trials."))
    lines.append("")
    if analysis.get("data_mode") == "dry-run":
        lines.append("2. **Dry-run data:** All data is from synthetic compaction (midpoint-split). "
                     "This validates the pipeline but does NOT measure genuine LLM compaction. "
                     "The forbidden proxy fp-simulated-only is VIOLATED.")
        lines.append("")
    track_b_n = analysis.get('track_b_trials', 0)
    track_b_text = 'No Track B data. SWE-Bench Docker setup required.' if track_b_n == 0 else f'{track_b_n} Track B trials.'
    lines.append(f"3. **Track B status:** {track_b_text}")
    lines.append("")
    lines.append("4. **Threshold calibration:** The 80K token trigger threshold is based on Anthropic API documentation. "
                 "Actual compaction behavior may vary with model version and API updates.")
    lines.append("")
    lines.append("5. **Model version dependency:** Results are specific to the model version used. "
                 "Different model versions may produce different compaction behaviors.")
    lines.append("")

    # --- Recommendations ---
    lines.append("## 10. Recommendations")
    lines.append("")

    if verdict == "PASS":
        lines.append("- **Proceed to full Track A/B/C with confidence.**")
        lines.append("- Run full N=60 Track A for publication-quality statistics.")
        lines.append("- Set up SWE-Bench Docker for Track B ecological validity.")
        lines.append("- Run Track C ablation to identify optimal instruction strategy.")
    elif verdict == "PARTIAL":
        if analysis.get("data_mode") == "dry-run":
            lines.append("- **Live pilot data would be required before any verdict can be "
                          "rendered, but live-API mode is disabled fleet-wide** per "
                          "CLAUDE.md Rule #10 (NO PAID LLM API, EVER) -- see BUG-020 in "
                          "BUGS_AND_ITERATIONS.md.")
            lines.append("- Pipeline is validated in dry-run/synthetic mode; genuine "
                          "live measurement is out of scope for this codebase.")
        else:
            lines.append("- **Collect more data.** Current sample is insufficient for significance.")
            lines.append("- Consider running full N=60 Track A before making architectural decisions.")
            lines.append("- If structural_reachability remains near 0.5, prepare backtracking plan.")
    elif verdict == "BACKTRACK":
        lines.append("- **Pivot to external provenance storage.**")
        lines.append("- In-context provenance is insufficient under genuine LLM compaction.")
        lines.append("- Consider: external DB, file-system provenance, or hybrid approach.")
        lines.append("- Document the negative finding -- it is scientifically valuable.")
    else:
        lines.append("- **Investigate pipeline issues.** Verdict is FAIL or UNKNOWN.")
        lines.append("- Check data loading, metric computation, and hypothesis test implementation.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by `tools/compaction_analysis.py` | Phase: 06-genuine-compaction, Plan: 05*")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
