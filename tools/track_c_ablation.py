"""Track C Ablation Framework — Phase 6, Plan 04 of Primordial v2.0.

Systematically varies summarization instructions, trigger thresholds,
and models to identify which factors most affect provenance survival
during genuine LLM compaction.

Ablation condition matrix:
  3 instruction variants x 3 threshold levels = 9 base conditions (Sonnet)
  Optional: 9 additional conditions for Opus model ablation

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import json
import math
import os
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent))

from genuine_compaction_runner import (
    GenuineCompactionRunner,
    RunnerConfig,
    TrialResult,
)
from findings_ledger import FindingsLedger, Finding
from task_templates import CodingTaskTemplate, DebuggingTaskTemplate, SpecificationTaskTemplate


# --- Instruction Variants ---

INSTRUCTION_VARIANTS: dict[str, str | None] = {
    "default": None,  # Use Anthropic's default summarization prompt
    "provenance_aware": (
        "Preserve all artifact IDs (strings matching 'artifact:*:r*'), "
        "all source_ref links between artifacts, and all absence state labels. "
        "These are provenance metadata that must survive summarization intact. "
        "Also preserve task state, next steps, and key decisions."
    ),
    "minimal": "Summarize briefly. Focus on key outcomes only.",
}

# --- Threshold Levels ---

THRESHOLD_LEVELS: list[int] = [50_000, 80_000, 120_000]  # tokens

# --- Model Variants ---

MODEL_VARIANTS: list[str] = ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]

# --- Task Template Cycling ---

TASK_TEMPLATES = [CodingTaskTemplate, DebuggingTaskTemplate, SpecificationTaskTemplate]


def _cycle_task_template(trial_index: int, run_id: str):
    """Cycle through A1/A2/A3 task templates deterministically."""
    cls = TASK_TEMPLATES[trial_index % len(TASK_TEMPLATES)]
    return cls(run_id=run_id)


# --- Ablation Config ---

@dataclass
class AblationConfig:
    """Configuration for a single ablation condition."""
    condition_id: str
    instructions: str | None
    threshold: int
    model: str
    trials_per_condition: int = 10
    task_template_name: str = "cycling"  # cycles through A1/A2/A3

    def to_dict(self) -> dict:
        return asdict(self)


# --- Condition Summary ---

@dataclass
class ConditionSummary:
    """Aggregated results for one ablation condition."""
    condition_id: str
    n_trials: int
    metrics: dict[str, dict[str, float]]  # metric_name -> {mean, std, ci_lower, ci_upper}
    raw_values: dict[str, list[float]]  # metric_name -> [values]

    def to_dict(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "n_trials": self.n_trials,
            "metrics": self.metrics,
        }


# --- Ablation Results ---

@dataclass
class AblationResults:
    """Complete results from a full ablation run."""
    ablation_id: str
    conditions: dict[str, ConditionSummary]
    deltas: dict[str, Any]
    timestamp: str
    config_summary: dict

    def to_dict(self) -> dict:
        return {
            "ablation_id": self.ablation_id,
            "conditions": {k: v.to_dict() for k, v in self.conditions.items()},
            "deltas": self.deltas,
            "timestamp": self.timestamp,
            "config_summary": self.config_summary,
        }


# --- Statistical Utilities ---

def _compute_ci(values: list[float], alpha: float = 0.05) -> tuple[float, float]:
    """Compute confidence interval using bootstrap percentile method.

    For small N, uses t-distribution approximation.
    For N >= 30, uses normal approximation.

    Args:
        values: List of observations.
        alpha: Significance level (default 0.05 for 95% CI).

    Returns:
        (ci_lower, ci_upper) tuple.
    """
    n = len(values)
    if n < 2:
        mean_val = values[0] if values else 0.0
        return (mean_val, mean_val)

    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values)

    # Use t-distribution critical value approximation
    # For df >= 2: t_crit ~ 1.96 + 2.4/df (rough Cornish-Fisher)
    df = n - 1
    if df >= 30:
        t_crit = 1.96  # z-value for large samples
    elif df >= 2:
        # Simple approximation; good enough for df >= 2
        t_crit = 1.96 + 2.4 / df
    else:
        t_crit = 12.71  # df=1, alpha=0.05 two-tailed

    se = std_val / math.sqrt(n)
    ci_lower = mean_val - t_crit * se
    ci_upper = mean_val + t_crit * se
    return (round(ci_lower, 6), round(ci_upper, 6))


def _bootstrap_permutation_test(
    group_a: list[float],
    group_b: list[float],
    n_permutations: int = 10000,
    seed: int = 42,
) -> float:
    """Two-sample permutation test for difference in means.

    Args:
        group_a: Observations from group A.
        group_b: Observations from group B.
        n_permutations: Number of permutation samples.
        seed: Random seed for reproducibility.

    Returns:
        Two-sided p-value.
    """
    import random
    rng = random.Random(seed)

    if not group_a or not group_b:
        return 1.0

    observed_diff = abs(statistics.mean(group_a) - statistics.mean(group_b))
    combined = group_a + group_b
    n_a = len(group_a)

    count_extreme = 0
    for _ in range(n_permutations):
        rng.shuffle(combined)
        perm_a = combined[:n_a]
        perm_b = combined[n_a:]
        perm_diff = abs(statistics.mean(perm_a) - statistics.mean(perm_b))
        if perm_diff >= observed_diff:
            count_extreme += 1

    return count_extreme / n_permutations


def _bonferroni_correct(p_values: list[float], n_comparisons: int = 3) -> list[float]:
    """Apply Bonferroni correction to a list of p-values.

    Args:
        p_values: Raw p-values.
        n_comparisons: Number of comparisons (default 3 for 3 instruction variants).

    Returns:
        Corrected p-values (capped at 1.0).
    """
    return [min(p * n_comparisons, 1.0) for p in p_values]


# --- Ablation Runner ---

class AblationRunner:
    """Orchestrates Track C ablation experiments.

    Generates 9 base conditions (3 instruction variants x 3 thresholds),
    runs N trials per condition, and computes between-condition deltas.

    Usage:
        runner = AblationRunner(dry_run=True)
        conditions = runner.generate_conditions()  # 9 configs
        results = runner.run_full_ablation(n_per_condition=10)
        results.deltas["provenance_aware_delta"]  # instruction effect
    """

    def __init__(
        self,
        dry_run: bool = True,
        model: str = "claude-sonnet-4-20250514",
        include_opus: bool = False,
        output_dir: str = "data/compaction/ablation",
        ledger: FindingsLedger | None = None,
    ):
        self.dry_run = dry_run
        self.base_model = model
        self.include_opus = include_opus
        self.output_dir = output_dir
        self.ledger = ledger

    def generate_conditions(self, model: str | None = None) -> list[AblationConfig]:
        """Generate all ablation conditions for a given model.

        Produces 9 conditions: 3 instruction variants x 3 threshold levels.
        If include_opus is True and model is not specified, also generates
        9 Opus conditions (returned separately via generate_all_conditions).

        Args:
            model: Override model for conditions. Defaults to self.base_model.

        Returns:
            List of 9 AblationConfig instances.
        """
        target_model = model or self.base_model
        conditions = []

        for instr_name, instr_text in INSTRUCTION_VARIANTS.items():
            for threshold in THRESHOLD_LEVELS:
                # Build descriptive condition ID
                model_short = target_model.split("-")[1] if "-" in target_model else target_model
                threshold_short = f"{threshold // 1000}K"
                condition_id = f"C-{instr_name}-{threshold_short}-{model_short}"

                conditions.append(AblationConfig(
                    condition_id=condition_id,
                    instructions=instr_text,
                    threshold=threshold,
                    model=target_model,
                ))

        return conditions

    def generate_all_conditions(self) -> list[AblationConfig]:
        """Generate conditions for all configured models.

        Returns 9 conditions for Sonnet. If include_opus is True,
        also returns 9 conditions for Opus (18 total).
        """
        conditions = self.generate_conditions(self.base_model)
        if self.include_opus:
            conditions.extend(self.generate_conditions("claude-opus-4-20250514"))
        return conditions

    def run_condition(
        self,
        config: AblationConfig,
        n_trials: int | None = None,
    ) -> list[TrialResult]:
        """Run N trials for one ablation condition.

        Args:
            config: The ablation condition configuration.
            n_trials: Override trials per condition (default: config.trials_per_condition).

        Returns:
            List of TrialResult instances.
        """
        trials = n_trials or config.trials_per_condition
        results = []

        runner_config = RunnerConfig(
            model=config.model,
            threshold=config.threshold,
            provenance_aware_instructions=config.instructions,
            dry_run=self.dry_run,
            output_dir=self.output_dir,
            num_iterations=20,
        )

        for trial_idx in range(trials):
            runner = GenuineCompactionRunner(runner_config, self.ledger)

            # Cycle through task templates for diversity
            task_template = _cycle_task_template(trial_idx, run_id=f"{config.condition_id}-t{trial_idx}")

            result = runner.run_trial(task_template)
            results.append(result)

            # Log result to output directory
            runner.log_results(result)

        return results

    def run_full_ablation(
        self,
        n_per_condition: int = 10,
    ) -> AblationResults:
        """Run all conditions sequentially and compute deltas.

        Args:
            n_per_condition: Trials per condition.

        Returns:
            AblationResults with aggregated summaries and deltas.
        """
        ablation_id = f"ablation-{int(time.time())}"
        all_conditions = self.generate_conditions()
        condition_results: dict[str, list[TrialResult]] = {}
        condition_summaries: dict[str, ConditionSummary] = {}

        for config in all_conditions:
            config.trials_per_condition = n_per_condition
            trial_results = self.run_condition(config, n_trials=n_per_condition)
            condition_results[config.condition_id] = trial_results
            condition_summaries[config.condition_id] = self.aggregate_condition(trial_results)

        # Compute deltas
        deltas = self.compute_deltas(condition_summaries)

        # Export results
        results = AblationResults(
            ablation_id=ablation_id,
            conditions=condition_summaries,
            deltas=deltas,
            timestamp=datetime.now(timezone.utc).isoformat(),
            config_summary={
                "n_conditions": len(all_conditions),
                "n_per_condition": n_per_condition,
                "instruction_variants": list(INSTRUCTION_VARIANTS.keys()),
                "threshold_levels": THRESHOLD_LEVELS,
                "model": self.base_model,
                "dry_run": self.dry_run,
            },
        )

        # Export
        self.export_results(results)

        # Log to ledger
        if self.ledger:
            self.ledger.record(Finding(
                phase=6,
                category="compaction",
                rq="RQ3b",
                title=f"Track C ablation complete: {len(all_conditions)} conditions, "
                      f"{n_per_condition} trials each",
                description=(
                    f"Ablation ID: {ablation_id}. "
                    f"provenance_aware_delta at 80K: "
                    f"{deltas.get('instruction_effect', {}).get('provenance_aware_delta', {}).get('80K', 'N/A')}. "
                    f"Threshold effect: "
                    f"{deltas.get('threshold_effect', {}).get('overall_trend', 'N/A')}."
                ),
                evidence=deltas,
                verdict="pending",
                confidence="medium",
                tags=["COMP-04", "track-c", "ablation"],
            ))

        return results

    def aggregate_condition(
        self,
        results: list[TrialResult],
    ) -> ConditionSummary:
        """Compute mean, std, CI for all metrics within one condition.

        Extracts: structural_reachability, artifact_id_survival,
        semantic_fidelity, compression_ratio, degraded_fraction.

        Args:
            results: List of TrialResult from the same condition.

        Returns:
            ConditionSummary with per-metric statistics.
        """
        if not results:
            return ConditionSummary(
                condition_id="empty",
                n_trials=0,
                metrics={},
                raw_values={},
            )

        condition_id = results[0].trial_id.rsplit("-t", 1)[0] if results else "unknown"

        # Collect metric names we track
        metric_names = [
            "structural_reachability",
            "artifact_id_survival",
            "semantic_fidelity",
            "compression_ratio",
            "degraded_fraction",
        ]

        raw_values: dict[str, list[float]] = {m: [] for m in metric_names}
        for result in results:
            metrics = result.aggregate_metrics
            for m in metric_names:
                val = metrics.get(m)
                if val is not None:
                    raw_values[m].append(float(val))

        # Compute statistics
        computed_metrics: dict[str, dict[str, float]] = {}
        for m in metric_names:
            vals = raw_values[m]
            if not vals:
                computed_metrics[m] = {"mean": 0.0, "std": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}
                continue
            mean_val = statistics.mean(vals)
            std_val = statistics.stdev(vals) if len(vals) > 1 else 0.0
            ci_lower, ci_upper = _compute_ci(vals)
            computed_metrics[m] = {
                "mean": round(mean_val, 6),
                "std": round(std_val, 6),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }

        return ConditionSummary(
            condition_id=condition_id,
            n_trials=len(results),
            metrics=computed_metrics,
            raw_values=raw_values,
        )

    def compute_deltas(
        self,
        summaries: dict[str, ConditionSummary],
    ) -> dict:
        """Compute between-condition effect sizes and significance.

        Produces:
        1. provenance_aware_delta: survival(provenance_aware) - survival(default)
           at each threshold level.
        2. threshold_effect: trend of survival across threshold levels.
        3. instruction_effect: pairwise comparisons with Bonferroni correction.

        Args:
            summaries: Condition ID -> ConditionSummary mapping.

        Returns:
            Dict of delta computations with p-values.
        """
        deltas: dict[str, Any] = {}

        # --- Instruction Effect ---
        # For each threshold level, compare instruction variants
        instruction_effect: dict[str, Any] = {}

        for threshold in THRESHOLD_LEVELS:
            threshold_short = f"{threshold // 1000}K"
            model_short = self.base_model.split("-")[1] if "-" in self.base_model else self.base_model

            # Find condition IDs for each instruction variant at this threshold
            default_id = f"C-default-{threshold_short}-{model_short}"
            prov_aware_id = f"C-provenance_aware-{threshold_short}-{model_short}"
            minimal_id = f"C-minimal-{threshold_short}-{model_short}"

            default_summary = summaries.get(default_id)
            prov_summary = summaries.get(prov_aware_id)
            minimal_summary = summaries.get(minimal_id)

            # Compute provenance_aware_delta = provenance_aware - default
            if default_summary and prov_summary:
                for metric_name in ["structural_reachability", "artifact_id_survival"]:
                    default_vals = default_summary.raw_values.get(metric_name, [])
                    prov_vals = prov_summary.raw_values.get(metric_name, [])

                    if default_vals and prov_vals:
                        delta_val = statistics.mean(prov_vals) - statistics.mean(default_vals)
                        p_val = _bootstrap_permutation_test(default_vals, prov_vals)

                        instruction_effect.setdefault("provenance_aware_delta", {})[threshold_short] = {
                            "metric": metric_name,
                            "delta": round(delta_val, 6),
                            "p_value_uncorrected": round(p_val, 6),
                        }

            # Pairwise comparisons with Bonferroni
            pairs = [
                ("default_vs_provenance", default_summary, prov_summary),
                ("default_vs_minimal", default_summary, minimal_summary),
                ("provenance_vs_minimal", prov_summary, minimal_summary),
            ]

            raw_p_values = []
            pairwise_results = []

            for pair_name, summary_a, summary_b in pairs:
                if summary_a and summary_b:
                    vals_a = summary_a.raw_values.get("artifact_id_survival", [])
                    vals_b = summary_b.raw_values.get("artifact_id_survival", [])
                    if vals_a and vals_b:
                        p_val = _bootstrap_permutation_test(vals_a, vals_b)
                        raw_p_values.append(p_val)
                        pairwise_results.append({
                            "comparison": pair_name,
                            "threshold": threshold_short,
                            "delta": round(statistics.mean(vals_b) - statistics.mean(vals_a), 6),
                            "p_value_uncorrected": round(p_val, 6),
                        })

            # Apply Bonferroni correction
            corrected = _bonferroni_correct(raw_p_values, n_comparisons=3)
            for i, result in enumerate(pairwise_results):
                if i < len(corrected):
                    result["p_value_corrected"] = round(corrected[i], 6)
                    result["significant_at_0_05"] = corrected[i] < 0.05
                    # Corrected alpha = 0.05/3 = 0.0167
                    result["bonferroni_alpha"] = round(0.05 / 3, 4)

            instruction_effect.setdefault("pairwise", {})[threshold_short] = pairwise_results

        deltas["instruction_effect"] = instruction_effect

        # --- Threshold Effect ---
        # For each instruction variant, trend across thresholds
        threshold_effect: dict[str, Any] = {}
        model_short = self.base_model.split("-")[1] if "-" in self.base_model else self.base_model

        for instr_name in INSTRUCTION_VARIANTS:
            trend = []
            for threshold in THRESHOLD_LEVELS:
                threshold_short = f"{threshold // 1000}K"
                cid = f"C-{instr_name}-{threshold_short}-{model_short}"
                summary = summaries.get(cid)
                if summary:
                    mean_survival = summary.metrics.get("artifact_id_survival", {}).get("mean", 0.0)
                    trend.append({
                        "threshold": threshold_short,
                        "mean_survival": mean_survival,
                    })

            # Determine overall trend direction
            if len(trend) >= 2:
                first_survival = trend[0]["mean_survival"]
                last_survival = trend[-1]["mean_survival"]
                if last_survival > first_survival + 0.01:
                    direction = "increasing"
                elif last_survival < first_survival - 0.01:
                    direction = "decreasing"
                else:
                    direction = "flat"
            else:
                direction = "insufficient_data"

            threshold_effect[instr_name] = {
                "trend": trend,
                "overall_trend": direction,
            }

        deltas["threshold_effect"] = threshold_effect

        return deltas

    def export_results(self, results: AblationResults, path: str | None = None):
        """Write ablation results to JSON and JSONL files.

        Produces:
        1. {output_dir}/ablation-{id}-summary.json — aggregated summary
        2. {output_dir}/ablation-{id}-conditions.jsonl — per-condition detail

        Args:
            results: AblationResults to export.
            path: Override output directory.
        """
        project_root = Path(__file__).parent.parent
        output_dir = project_root / (path or self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Summary JSON
        summary_path = output_dir / f"{results.ablation_id}-summary.json"
        with open(summary_path, "w") as f:
            json.dump(results.to_dict(), f, indent=2, default=str)

        # Per-condition JSONL
        conditions_path = output_dir / f"{results.ablation_id}-conditions.jsonl"
        with open(conditions_path, "w") as f:
            for cid, summary in results.conditions.items():
                line = {
                    "condition_id": cid,
                    "ablation_id": results.ablation_id,
                    **summary.to_dict(),
                }
                f.write(json.dumps(line, default=str) + "\n")


# --- CLI entry point ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Track C Ablation Framework")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Run in dry-run mode (default)")
    parser.add_argument("--live", action="store_true",
                        help="Run with live API calls")
    parser.add_argument("-n", "--trials", type=int, default=1,
                        help="Trials per condition (default: 1)")
    parser.add_argument("--include-opus", action="store_true",
                        help="Include Opus model conditions")
    args = parser.parse_args()

    dry_run = not args.live
    runner = AblationRunner(dry_run=dry_run, include_opus=args.include_opus)

    print(f"Track C Ablation — {'dry-run' if dry_run else 'live'} mode")
    print(f"Conditions: {len(runner.generate_conditions())} base conditions")
    print(f"Trials per condition: {args.trials}")
    print()

    results = runner.run_full_ablation(n_per_condition=args.trials)

    print(f"\nAblation complete: {results.ablation_id}")
    print(f"Conditions run: {len(results.conditions)}")
    for cid, summary in results.conditions.items():
        survival = summary.metrics.get("artifact_id_survival", {})
        print(f"  {cid}: survival mean={survival.get('mean', 'N/A')}, "
              f"std={survival.get('std', 'N/A')}")

    print(f"\nDeltas:")
    prov_deltas = results.deltas.get("instruction_effect", {}).get("provenance_aware_delta", {})
    for threshold, delta_info in prov_deltas.items():
        print(f"  provenance_aware_delta at {threshold}: "
              f"{delta_info['delta']:.4f} (p={delta_info['p_value_uncorrected']:.4f})")
