#!/usr/bin/env python3
"""Pilot Track A Runner — Phase 6, Plan 03 of Primordial v2.0.

Executes 6 pilot Track A trials (2 per category) with genuine LLM compaction
via Anthropic's compact_20260112 API:

  | Trial     | Category      | Provenance-aware | Threshold |
  |-----------|---------------|-----------------|-----------|
  | pilot-001 | coding        | No              | 80K       |
  | pilot-002 | coding        | Yes             | 80K       |
  | pilot-003 | debugging     | No              | 80K       |
  | pilot-004 | debugging     | Yes             | 80K       |
  | pilot-005 | specification | No              | 80K       |
  | pilot-006 | specification | Yes             | 80K       |

Outputs:
  data/compaction/genuine/pilot-results.jsonl  (one JSON line per trial)
  stdout: per-trial summaries + overall pilot summary

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from genuine_compaction_runner import (
    GenuineCompactionRunner,
    RunnerConfig,
    DEFAULT_PROVENANCE_INSTRUCTIONS,
)
from task_templates import (
    CodingTaskTemplate,
    DebuggingTaskTemplate,
    SpecificationTaskTemplate,
)
from findings_ledger import FindingsLedger


# --- Cost Estimation ---

# Sonnet pricing (as of March 2026): $3/M input, $15/M output
SONNET_INPUT_PRICE_PER_TOKEN = 3.0 / 1_000_000
SONNET_OUTPUT_PRICE_PER_TOKEN = 15.0 / 1_000_000

def estimate_trial_cost(threshold: int, num_iterations: int, tokens_per_response: int = 700) -> float:
    """Estimate API cost for a single trial.

    Conservative estimate: assumes reaching threshold once, then all output tokens.
    Actual cost may be lower (compaction reduces input tokens on subsequent calls).
    """
    # Input tokens accumulate per iteration (conversation grows)
    # Average input per call ≈ threshold / 2 (midpoint of growth)
    avg_input_per_call = threshold / 2
    total_input = avg_input_per_call * num_iterations
    total_output = tokens_per_response * num_iterations

    input_cost = total_input * SONNET_INPUT_PRICE_PER_TOKEN
    output_cost = total_output * SONNET_OUTPUT_PRICE_PER_TOKEN

    return input_cost + output_cost


# --- Trial Matrix ---

TRIAL_MATRIX = [
    {
        "trial_id": "pilot-001",
        "category": "coding",
        "template_class": CodingTaskTemplate,
        "provenance_aware": False,
        "threshold": 80_000,
    },
    {
        "trial_id": "pilot-002",
        "category": "coding",
        "template_class": CodingTaskTemplate,
        "provenance_aware": True,
        "threshold": 80_000,
    },
    {
        "trial_id": "pilot-003",
        "category": "debugging",
        "template_class": DebuggingTaskTemplate,
        "provenance_aware": False,
        "threshold": 80_000,
    },
    {
        "trial_id": "pilot-004",
        "category": "debugging",
        "template_class": DebuggingTaskTemplate,
        "provenance_aware": True,
        "threshold": 80_000,
    },
    {
        "trial_id": "pilot-005",
        "category": "specification",
        "template_class": SpecificationTaskTemplate,
        "provenance_aware": False,
        "threshold": 80_000,
    },
    {
        "trial_id": "pilot-006",
        "category": "specification",
        "template_class": SpecificationTaskTemplate,
        "provenance_aware": True,
        "threshold": 80_000,
    },
]


def run_pilot(dry_run: bool = False, cost_limit: float = 50.0) -> dict:
    """Execute 6 pilot Track A trials.

    Args:
        dry_run: If True, use synthetic data (no API calls).
                 If False, use live API (requires ANTHROPIC_API_KEY).
        cost_limit: Maximum total cost before pausing ($).

    Returns:
        Dict with pilot summary: completed, failed, results, mode.
    """
    # Check for API key
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    mode = "dry-run" if (dry_run or not has_api_key) else "live"

    if not has_api_key and not dry_run:
        print("WARNING: ANTHROPIC_API_KEY not set. Running in dry-run mode.")
        print("Set ANTHROPIC_API_KEY to run live pilot trials.\n")

    print(f"=" * 70)
    print(f"PILOT TRACK A — {len(TRIAL_MATRIX)} trials")
    print(f"Mode: {mode}")
    print(f"Model: claude-sonnet-4-20250514")
    print(f"Threshold: 80,000 tokens")
    print(f"Max iterations: 20")
    print(f"Cost limit: ${cost_limit:.2f}")
    print(f"=" * 70)
    print()

    # Estimate total cost
    if mode == "live":
        estimated_per_trial = estimate_trial_cost(80_000, 20)
        estimated_total = estimated_per_trial * len(TRIAL_MATRIX)
        print(f"Estimated cost per trial: ${estimated_per_trial:.2f}")
        print(f"Estimated total cost: ${estimated_total:.2f}")
        print()

    # Setup output
    output_dir = PROJECT_ROOT / "data" / "compaction" / "genuine"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "pilot-results.jsonl"

    # Ledger for findings
    ledger = FindingsLedger()

    # Run trials
    completed = []
    failed = []
    running_cost = 0.0
    all_results = []

    for i, trial_spec in enumerate(TRIAL_MATRIX):
        trial_id = trial_spec["trial_id"]
        category = trial_spec["category"]
        provenance_aware = trial_spec["provenance_aware"]
        threshold = trial_spec["threshold"]

        print(f"Trial {i + 1}/{len(TRIAL_MATRIX)}: {trial_id} — "
              f"{category} (provenance_aware={provenance_aware})...")

        # Cost guard
        if mode == "live":
            est = estimate_trial_cost(threshold, 20)
            print(f"  Estimated cost: ${est:.2f} (running total: ${running_cost:.2f})")
            if running_cost + est > cost_limit:
                print(f"  WARNING: Exceeding cost limit (${cost_limit:.2f}). Stopping.")
                break

        # Configure runner
        config = RunnerConfig(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            threshold=threshold,
            pause_after_compaction=True,
            provenance_aware_instructions=(
                DEFAULT_PROVENANCE_INSTRUCTIONS if provenance_aware else None
            ),
            max_retries=3,
            retry_base_delay=2.0,
            output_dir=str(output_dir),
            dry_run=(mode == "dry-run"),
            num_iterations=20,
        )

        # Create template
        template = trial_spec["template_class"](run_id=trial_id)

        # Run trial
        trial_start = time.time()
        try:
            runner = GenuineCompactionRunner(config, ledger)
            result = runner.run_trial(template)

            # Override trial_id with our pilot naming
            result.trial_id = trial_id
            result.provenance_aware = provenance_aware
            result.mode = mode

            trial_duration = time.time() - trial_start

            # Print per-trial summary
            metrics = result.aggregate_metrics
            n_events = len(result.compaction_events)
            print(f"  Duration: {trial_duration:.1f}s")
            print(f"  LLM compaction events: {n_events}")
            print(f"  artifact_id_survival: {metrics.get('artifact_id_survival', 'N/A')}")
            print(f"  structural_reachability: {metrics.get('structural_reachability', 'N/A')}")
            print(f"  degraded_fraction: {metrics.get('degraded_fraction', 'N/A')}")
            print(f"  compression_ratio: {metrics.get('compression_ratio', 'N/A')}")
            print()

            # Write to JSONL
            with open(results_path, "a") as f:
                f.write(json.dumps(result.to_dict(), default=str) + "\n")

            completed.append(trial_id)
            all_results.append(result.to_dict())

        except Exception as e:
            trial_duration = time.time() - trial_start
            print(f"  FAILED after {trial_duration:.1f}s: {type(e).__name__}: {e}")
            print()
            failed.append({"trial_id": trial_id, "error": str(e)})

    # Overall summary
    print(f"=" * 70)
    print(f"PILOT SUMMARY")
    print(f"=" * 70)
    print(f"Completed: {len(completed)}/{len(TRIAL_MATRIX)}")
    print(f"Failed: {len(failed)}/{len(TRIAL_MATRIX)}")
    print(f"Mode: {mode}")
    print(f"Results: {results_path}")
    print()

    if completed:
        # Compute aggregate statistics
        all_survival = []
        all_reachability = []
        all_degraded = []
        all_compression = []

        for r in all_results:
            m = r.get("aggregate_metrics", {})
            if "artifact_id_survival" in m:
                all_survival.append(m["artifact_id_survival"])
            if "structural_reachability" in m:
                all_reachability.append(m["structural_reachability"])
            if "degraded_fraction" in m:
                all_degraded.append(m["degraded_fraction"])
            if "compression_ratio" in m:
                all_compression.append(m["compression_ratio"])

        if all_survival:
            mean_survival = sum(all_survival) / len(all_survival)
            print(f"Mean artifact_id_survival: {mean_survival:.4f}")
        if all_reachability:
            mean_reach = sum(all_reachability) / len(all_reachability)
            print(f"Mean structural_reachability: {mean_reach:.4f}")
        if all_degraded:
            mean_deg = sum(all_degraded) / len(all_degraded)
            print(f"Mean degraded_fraction: {mean_deg:.4f}")
        if all_compression:
            mean_comp = sum(all_compression) / len(all_compression)
            print(f"Mean compression_ratio: {mean_comp:.2f}")

        # Per-category breakdown
        print()
        print("Per-category breakdown:")
        for cat in ["coding", "debugging", "specification"]:
            cat_results = [r for r in all_results if r.get("task_category") == cat]
            if cat_results:
                cat_survival = [r["aggregate_metrics"]["artifact_id_survival"]
                              for r in cat_results if "aggregate_metrics" in r]
                cat_reach = [r["aggregate_metrics"]["structural_reachability"]
                           for r in cat_results if "aggregate_metrics" in r]
                if cat_survival:
                    print(f"  {cat}: survival={sum(cat_survival)/len(cat_survival):.4f}, "
                          f"reachability={sum(cat_reach)/len(cat_reach):.4f}")

        # Provenance-aware delta
        print()
        print("Provenance-aware delta:")
        for cat in ["coding", "debugging", "specification"]:
            aware = [r for r in all_results
                    if r.get("task_category") == cat and r.get("provenance_aware")]
            unaware = [r for r in all_results
                      if r.get("task_category") == cat and not r.get("provenance_aware")]
            if aware and unaware:
                aware_surv = aware[0]["aggregate_metrics"]["artifact_id_survival"]
                unaware_surv = unaware[0]["aggregate_metrics"]["artifact_id_survival"]
                delta = aware_surv - unaware_surv
                print(f"  {cat}: delta={delta:+.4f} "
                      f"(aware={aware_surv:.4f}, unaware={unaware_surv:.4f})")

    # Compaction event count
    trials_with_compaction = sum(
        1 for r in all_results if len(r.get("compaction_events", [])) > 0
    )
    print()
    print(f"Trials with LLM compaction events: {trials_with_compaction}/{len(all_results)}")

    # Validation checks
    valid_pipeline = len(completed) >= 4
    valid_compaction = trials_with_compaction >= 4
    print()
    print(f"Pipeline valid (>= 4 completed): {'PASS' if valid_pipeline else 'FAIL'}")
    print(f"LLM compaction fires (>= 4 trials): {'PASS' if valid_compaction else 'FAIL'}")

    summary = {
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "completed": completed,
        "failed": failed,
        "total_trials": len(TRIAL_MATRIX),
        "trials_with_compaction": trials_with_compaction,
        "pipeline_valid": valid_pipeline,
        "compaction_fires": valid_compaction,
        "results": all_results,
        "results_path": str(results_path),
    }

    return summary


def analyze_pilot(results_path: str | Path) -> dict:
    """Analyze pilot results and produce aggregated statistics.

    Args:
        results_path: Path to pilot-results.jsonl.

    Returns:
        Dict with aggregated analysis suitable for pilot-analysis.json.
    """
    results_path = Path(results_path)
    if not results_path.exists():
        return {"error": f"Results file not found: {results_path}"}

    # Parse JSONL
    results = []
    with open(results_path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))

    if not results:
        return {"error": "No results in file"}

    # Mode (should be uniform across all trials)
    mode = results[0].get("mode", "unknown")

    # Global aggregates
    all_metrics = {
        "artifact_id_survival": [],
        "structural_reachability": [],
        "degraded_fraction": [],
        "compression_ratio": [],
        "semantic_fidelity": [],
    }

    for r in results:
        m = r.get("aggregate_metrics", {})
        for key in all_metrics:
            if key in m:
                all_metrics[key].append(m[key])

    def stats(values: list[float]) -> dict:
        if not values:
            return {"mean": None, "min": None, "max": None, "range": None, "n": 0}
        n = len(values)
        mean = sum(values) / n
        mn = min(values)
        mx = max(values)
        return {
            "mean": round(mean, 4),
            "min": round(mn, 4),
            "max": round(mx, 4),
            "range": round(mx - mn, 4),
            "n": n,
        }

    global_stats = {key: stats(vals) for key, vals in all_metrics.items()}

    # Per-category breakdown
    categories = ["coding", "debugging", "specification"]
    per_category = {}
    for cat in categories:
        cat_results = [r for r in results if r.get("task_category") == cat]
        cat_metrics = {key: [] for key in all_metrics}
        for r in cat_results:
            m = r.get("aggregate_metrics", {})
            for key in cat_metrics:
                if key in m:
                    cat_metrics[key].append(m[key])
        per_category[cat] = {key: stats(vals) for key, vals in cat_metrics.items()}

    # Provenance-aware delta
    provenance_delta = {}
    for cat in categories:
        aware = [r for r in results
                if r.get("task_category") == cat and r.get("provenance_aware")]
        unaware = [r for r in results
                  if r.get("task_category") == cat and not r.get("provenance_aware")]
        if aware and unaware:
            aware_surv = aware[0]["aggregate_metrics"]["artifact_id_survival"]
            unaware_surv = unaware[0]["aggregate_metrics"]["artifact_id_survival"]
            aware_reach = aware[0]["aggregate_metrics"]["structural_reachability"]
            unaware_reach = unaware[0]["aggregate_metrics"]["structural_reachability"]
            provenance_delta[cat] = {
                "survival_delta": round(aware_surv - unaware_surv, 4),
                "reachability_delta": round(aware_reach - unaware_reach, 4),
                "aware_survival": round(aware_surv, 4),
                "unaware_survival": round(unaware_surv, 4),
                "aware_reachability": round(aware_reach, 4),
                "unaware_reachability": round(unaware_reach, 4),
            }

    # Anchor comparisons
    anchor_comparisons = {
        "mockml_ceiling": {
            "description": "MockLM experiment: 100% reachability, 100% survival (controlled ceiling)",
            "pilot_mean_survival": global_stats["artifact_id_survival"]["mean"],
            "pilot_mean_reachability": global_stats["structural_reachability"]["mean"],
            "delta_from_ceiling_survival": (
                round(global_stats["artifact_id_survival"]["mean"] - 1.0, 4)
                if global_stats["artifact_id_survival"]["mean"] is not None else None
            ),
            "delta_from_ceiling_reachability": (
                round(global_stats["structural_reachability"]["mean"] - 1.0, 4)
                if global_stats["structural_reachability"]["mean"] is not None else None
            ),
        },
        "knowledge_objects": {
            "description": "Zahn & Chana March 2026: 60% fact loss per LLM compression pass",
            "expected_survival_if_unstructured": 0.4,
            "pilot_mean_survival": global_stats["artifact_id_survival"]["mean"],
            "survival_vs_unstructured": (
                "better" if global_stats["artifact_id_survival"]["mean"] is not None
                    and global_stats["artifact_id_survival"]["mean"] > 0.4
                else "worse_or_equal" if global_stats["artifact_id_survival"]["mean"] is not None
                else "unknown"
            ),
        },
        "v1_simulated": {
            "description": "v1.0 simulated compaction: reachability 0.93 (10% del) to 0.25 (90% del)",
            "v1_at_50pct_deletion": 0.82,
            "pilot_mean_reachability": global_stats["structural_reachability"]["mean"],
            "note": "Comparison requires matching compression ratio from pilot to simulated deletion percentage",
        },
    }

    # Tier distribution
    tier_counts = {"resolved": 0, "degraded": 0, "broken": 0}
    for r in results:
        for boundary in r.get("boundaries", r.get("compaction_events", [])):
            tiers = boundary.get("tier_classification", {})
            for tier in tiers.values():
                if tier in tier_counts:
                    tier_counts[tier] += 1

    total_classified = sum(tier_counts.values())
    tier_distribution = {
        tier: {
            "count": count,
            "fraction": round(count / max(total_classified, 1), 4)
        }
        for tier, count in tier_counts.items()
    }

    # LLM compaction event statistics
    compaction_event_counts = [
        len(r.get("compaction_events", []))
        for r in results
    ]
    trials_with_compaction = sum(1 for c in compaction_event_counts if c > 0)

    # Go/no-go assessment
    def compute_go_nogo(n_completed, n_total, n_compaction, mean_survival, mean_reach):
        if n_completed < 4:
            return "STOP", "Fewer than 4/6 trials completed — pipeline unreliable"
        if mode == "dry-run":
            return "BLOCKED", "Dry-run only — live API required for go/no-go decision"
        if n_compaction < 4:
            return "REVISE", "LLM compaction did not fire reliably — adjust threshold or task length"
        if mean_survival is None or mean_reach is None:
            return "STOP", "Metrics could not be computed"
        if mean_survival == 0.0 and mean_reach == 0.0:
            return "STOP", "All metrics at zero — provenance completely destroyed"
        if mean_survival >= 0.99 and mean_reach >= 0.99:
            return "REVISE", "All metrics near ceiling — LLM compaction may not be impactful enough"
        return "GO", "Compaction fires, metrics in measurable range"

    n_completed = len(results)
    mean_surv = global_stats["artifact_id_survival"]["mean"]
    mean_reach = global_stats["structural_reachability"]["mean"]

    go_decision, go_reason = compute_go_nogo(
        n_completed, 6, trials_with_compaction, mean_surv, mean_reach
    )

    analysis = {
        "pilot_summary": {
            "mode": mode,
            "total_trials": len(results),
            "trials_with_compaction": trials_with_compaction,
            "compaction_event_counts": compaction_event_counts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "global_statistics": global_stats,
        "per_category": per_category,
        "provenance_aware_delta": provenance_delta,
        "anchor_comparisons": anchor_comparisons,
        "tier_distribution": tier_distribution,
        "go_nogo": {
            "decision": go_decision,
            "reason": go_reason,
            "criteria": {
                "pipeline_valid": n_completed >= 4,
                "compaction_fires": trials_with_compaction >= 4,
                "metrics_measurable": (
                    mean_surv is not None
                    and mean_reach is not None
                    and not (mean_surv == 0.0 and mean_reach == 0.0)
                    and not (mean_surv >= 0.99 and mean_reach >= 0.99)
                ),
                "live_mode": mode == "live",
            },
        },
    }

    return analysis


def write_pilot_report(analysis: dict, output_path: str | Path) -> Path:
    """Write the pilot report markdown file.

    Args:
        analysis: Output from analyze_pilot().
        output_path: Path for the report file.

    Returns:
        Path to the written report.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mode = analysis.get("pilot_summary", {}).get("mode", "unknown")
    go = analysis.get("go_nogo", {})
    gs = analysis.get("global_statistics", {})
    pc = analysis.get("per_category", {})
    pd = analysis.get("provenance_aware_delta", {})
    ac = analysis.get("anchor_comparisons", {})
    td = analysis.get("tier_distribution", {})
    ps = analysis.get("pilot_summary", {})

    lines = []
    lines.append("# Pilot Track A Report")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append(f"**Mode:** {mode}")
    lines.append(f"**Trials:** {ps.get('total_trials', 0)}/6")
    lines.append(f"**Trials with LLM compaction events:** {ps.get('trials_with_compaction', 0)}")
    lines.append("")

    if mode == "dry-run":
        lines.append("> **NOTE:** This report is based on dry-run data (synthetic LLM compaction).")
        lines.append("> Dry-run validates pipeline logic but NOT genuine LLM behavior.")
        lines.append("> Live API trials required before making go/no-go decision.")
        lines.append("> See forbidden proxy fp-dry-run-only in Plan 03 contract.")
        lines.append("")

    # Go/No-Go
    lines.append(f"## Go/No-Go Recommendation: **{go.get('decision', 'UNKNOWN')}**")
    lines.append("")
    lines.append(f"**Reason:** {go.get('reason', 'N/A')}")
    lines.append("")
    criteria = go.get("criteria", {})
    lines.append("| Criterion | Status |")
    lines.append("|-----------|--------|")
    for k, v in criteria.items():
        status = "PASS" if v else "FAIL"
        lines.append(f"| {k} | {status} |")
    lines.append("")

    # Global Statistics
    lines.append("## Global Statistics (pilot N=6)")
    lines.append("")
    lines.append("| Metric | Mean | Min | Max | Range | N |")
    lines.append("|--------|------|-----|-----|-------|---|")
    for metric, s in gs.items():
        if isinstance(s, dict):
            lines.append(
                f"| {metric} | {s.get('mean', 'N/A')} | {s.get('min', 'N/A')} | "
                f"{s.get('max', 'N/A')} | {s.get('range', 'N/A')} | {s.get('n', 0)} |"
            )
    lines.append("")

    # Per-Category
    lines.append("## Per-Category Breakdown")
    lines.append("")
    for cat in ["coding", "debugging", "specification"]:
        if cat in pc:
            lines.append(f"### {cat.capitalize()}")
            lines.append("")
            lines.append("| Metric | Mean | Min | Max |")
            lines.append("|--------|------|-----|-----|")
            for metric, s in pc[cat].items():
                if isinstance(s, dict) and s.get("n", 0) > 0:
                    lines.append(
                        f"| {metric} | {s.get('mean', 'N/A')} | "
                        f"{s.get('min', 'N/A')} | {s.get('max', 'N/A')} |"
                    )
            lines.append("")

    # Provenance-Aware Delta
    lines.append("## Provenance-Aware Delta")
    lines.append("")
    if pd:
        lines.append("| Category | Survival Delta | Aware | Unaware | Reachability Delta |")
        lines.append("|----------|---------------|-------|---------|-------------------|")
        for cat, d in pd.items():
            lines.append(
                f"| {cat} | {d.get('survival_delta', 'N/A'):+.4f} | "
                f"{d.get('aware_survival', 'N/A')} | {d.get('unaware_survival', 'N/A')} | "
                f"{d.get('reachability_delta', 'N/A'):+.4f} |"
            )
        lines.append("")
        lines.append("**Interpretation:** Positive delta means provenance-aware instructions help.")
        lines.append("Note: N=1 per cell — no statistical significance on pilot data.")
    else:
        lines.append("No provenance-aware delta computed (insufficient data).")
    lines.append("")

    # Anchor Comparisons
    lines.append("## Anchor Comparisons")
    lines.append("")

    # MockLM
    ml = ac.get("mockml_ceiling", {})
    lines.append("### 1. MockLM Ceiling (controlled condition)")
    lines.append("")
    lines.append(f"- MockLM ceiling: survival=1.0, reachability=1.0")
    lines.append(f"- Pilot mean survival: {ml.get('pilot_mean_survival', 'N/A')}")
    lines.append(f"- Pilot mean reachability: {ml.get('pilot_mean_reachability', 'N/A')}")
    lines.append(f"- Delta from ceiling (survival): {ml.get('delta_from_ceiling_survival', 'N/A')}")
    lines.append(f"- Delta from ceiling (reachability): {ml.get('delta_from_ceiling_reachability', 'N/A')}")
    lines.append(f"- **Expected:** Genuine < MockLM (real LLM compaction is lossy)")
    lines.append("")

    # Knowledge Objects
    ko = ac.get("knowledge_objects", {})
    lines.append("### 2. Knowledge Objects (Zahn & Chana, March 2026)")
    lines.append("")
    lines.append(f"- Knowledge Objects: 60% fact loss per LLM compression pass")
    lines.append(f"- Expected unstructured survival: 0.4 (40%)")
    lines.append(f"- Pilot mean artifact_id_survival: {ko.get('pilot_mean_survival', 'N/A')}")
    lines.append(f"- Comparison: {ko.get('survival_vs_unstructured', 'N/A')}")
    lines.append(f"- **If survival > 0.4:** Structured provenance survives better than unstructured facts")
    lines.append("")

    # v1.0 Simulated
    v1 = ac.get("v1_simulated", {})
    lines.append("### 3. v1.0 Simulated Compaction")
    lines.append("")
    lines.append(f"- v1.0 at 50% random deletion: reachability = 0.82")
    lines.append(f"- Pilot mean reachability: {v1.get('pilot_mean_reachability', 'N/A')}")
    lines.append(f"- Note: {v1.get('note', 'N/A')}")
    lines.append("")

    # Tier Distribution
    lines.append("## Tier Distribution")
    lines.append("")
    lines.append("| Tier | Count | Fraction |")
    lines.append("|------|-------|----------|")
    for tier in ["resolved", "degraded", "broken"]:
        if tier in td:
            t = td[tier]
            lines.append(f"| {tier} | {t.get('count', 0)} | {t.get('fraction', 0):.4f} |")
    lines.append("")
    lines.append("**Note:** First-ever population of degraded tier under LLM compaction.")
    lines.append("v1.0 simulated compaction produced zero degraded refs (all resolved or broken).")
    lines.append("")

    # Variance Estimate
    lines.append("## Variance Estimate (pilot N=6)")
    lines.append("")
    surv_range = gs.get("artifact_id_survival", {}).get("range", "N/A")
    reach_range = gs.get("structural_reachability", {}).get("range", "N/A")
    lines.append(f"- artifact_id_survival range: {surv_range}")
    lines.append(f"- structural_reachability range: {reach_range}")
    lines.append(f"- **Note:** N=6 is insufficient for variance estimation.")
    lines.append(f"  Pilot serves to detect gross failures, not estimate population parameters.")
    lines.append("")

    # Limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append("1. **N=6 is not statistical:** No p-values, no confidence intervals, no hypothesis tests.")
    lines.append("2. **Pilot validates pipeline, not hypothesis:** Full Track A (N=60) needed for statistical claims.")
    if mode == "dry-run":
        lines.append("3. **DRY-RUN ONLY:** All data is synthetic. Live API calls required for genuine measurements.")
        lines.append("   Forbidden proxy fp-dry-run-only is TRIGGERED. claim-pipeline-valid is BLOCKED.")
    lines.append("")

    report_text = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(report_text)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Pilot Track A trials")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Force dry-run mode (no API calls)"
    )
    parser.add_argument(
        "--cost-limit", type=float, default=50.0,
        help="Maximum total cost before pausing ($)"
    )
    parser.add_argument(
        "--analyze-only", type=str, default=None,
        help="Skip running, just analyze an existing JSONL file"
    )
    args = parser.parse_args()

    if args.analyze_only:
        # Analysis-only mode
        analysis = analyze_pilot(args.analyze_only)
        analysis_path = PROJECT_ROOT / "data" / "compaction" / "genuine" / "pilot-analysis.json"
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"Analysis written to: {analysis_path}")

        report_path = PROJECT_ROOT / "docs" / "pilot-report.md"
        write_pilot_report(analysis, report_path)
        print(f"Report written to: {report_path}")
    else:
        # Run pilot
        summary = run_pilot(dry_run=args.dry_run, cost_limit=args.cost_limit)

        # Analyze results
        results_path = summary["results_path"]
        analysis = analyze_pilot(results_path)

        # Write analysis JSON
        analysis_path = PROJECT_ROOT / "data" / "compaction" / "genuine" / "pilot-analysis.json"
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\nAnalysis written to: {analysis_path}")

        # Write pilot report
        report_path = PROJECT_ROOT / "docs" / "pilot-report.md"
        write_pilot_report(analysis, report_path)
        print(f"Report written to: {report_path}")

        print(f"\nGo/No-Go: {analysis['go_nogo']['decision']}")
        print(f"Reason: {analysis['go_nogo']['reason']}")
