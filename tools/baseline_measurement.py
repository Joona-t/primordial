"""
baseline_measurement.py -- Measurement framework for three-tier baseline comparison.

Orchestrates running tasks across all three baseline tiers (uninstrumented,
structured logging, forge-instrumented) and collecting comparable metrics.

Computes all 5 canonical metrics from CONVENTIONS.md #7:
- reachability_fraction: (reachable via BFS) / total [0, 1]
- compression_ratio: original_size / encoded_size (1, inf)
- vs_vanilla_pct: (forge_size - vanilla_size) / vanilla_size * 100
- detection_rate: violations_detected / total_violations [0, 1]
- false_positive_rate: false_alarms / clean_runs [0, 1]

Convention compliance:
- All uses of "compaction" are qualified per Convention #6
- Metrics formulas match CONVENTIONS.md #7 exactly
- Statistical reporting uses bootstrap 95% CIs for N < 30

ORDER-OF-MAGNITUDE ESTIMATES (for verification):
- Uninstrumented: detection_rate ~ 0, reachability = 0 (no provenance)
- Structured logging: detection_rate > 0 but < forge (schema catches some)
- Forge: detection_rate approaching 6/6 MockLM ceiling (ref-mock-experiment)
- Forge: reachability approaching 1.0 for non-compacted tasks
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))


# --- Task specification ---


class TaskSpec:
    """Specification for a single benchmark task.

    Attributes:
        task_id: Unique task identifier (e.g., "TASK-S1").
        tier: Complexity tier ("short" or "long").
        prompt: Fixed prompt text for the task.
        workspace_setup: Callable that prepares the workspace directory.
        success_check: Callable that verifies task success.
        expected_tokens: Estimated token count range (low, high).
        max_iterations: Maximum LLM iterations before timeout.
    """

    def __init__(
        self,
        task_id: str,
        tier: str,
        prompt: str,
        *,
        workspace_setup: Any = None,
        success_check: Any = None,
        expected_tokens: tuple[int, int] = (0, 0),
        max_iterations: int = 20,
    ):
        self.task_id = task_id
        self.tier = tier
        self.prompt = prompt
        self.workspace_setup = workspace_setup
        self.success_check = success_check
        self.expected_tokens = expected_tokens
        self.max_iterations = max_iterations

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "tier": self.tier,
            "prompt": self.prompt,
            "expected_tokens": list(self.expected_tokens),
            "max_iterations": self.max_iterations,
        }


# --- Tier 1: Uninstrumented (vanilla) baseline ---


def run_task_uninstrumented(task_spec: TaskSpec) -> dict[str, Any]:
    """Run a task with no instrumentation (vanilla baseline).

    Produces BASE-01 measurement: raw execution with no logging,
    no validation, no provenance tracking.

    The uninstrumented baseline represents what the vanilla runtime captures.
    Expected: no structural violations detected, no provenance, no hashing.

    Args:
        task_spec: Task specification with prompt and workspace setup.

    Returns:
        Result dict with:
        - task_id, tier, raw_output, token_count, duration_ms, errors
        - No provenance (reachability = 0)
        - No violations detected (detection_rate = 0)
    """
    start_time = time.monotonic()
    start_ts = _utc_iso_z()
    errors: list[dict[str, Any]] = []

    # Prepare workspace
    workspace_dir = None
    if task_spec.workspace_setup:
        try:
            workspace_dir = task_spec.workspace_setup()
        except Exception as e:
            errors.append(_error_record(e, "workspace_setup"))

    # Execute task (placeholder: real execution happens in Plan 02-04)
    raw_output: str | None = None
    token_count = 0
    ledger_events: list[dict[str, Any]] = []

    # In Plan 02-04, this will execute the task via the queue worker runtime.
    # For now, the framework accepts pre-recorded results.

    duration_ms = (time.monotonic() - start_time) * 1000

    return {
        "task_id": task_spec.task_id,
        "tier": task_spec.tier,
        "baseline_tier": "uninstrumented",
        "raw_output": raw_output,
        "token_count": token_count,
        "duration_ms": round(duration_ms, 3),
        "start_timestamp": start_ts,
        "end_timestamp": _utc_iso_z(),
        "errors": errors,
        "ledger_events": ledger_events,
        "workspace_dir": str(workspace_dir) if workspace_dir else None,
    }


# --- Tier 2: Structured logging baseline ---


def run_task_structured_logging(task_spec: TaskSpec) -> dict[str, Any]:
    """Run a task with the structured logging baseline (no forge features).

    Produces BASE-02 measurement: execution with span-based event recording,
    schema validation, timing, and token counting. No typed absence,
    no provenance DAG, no hash-verified compression.

    This baseline uses structured_logging_baseline.py.

    Args:
        task_spec: Task specification with prompt and workspace setup.

    Returns:
        Result dict with:
        - task_id, tier, raw_output, token_count, duration_ms, errors
        - spans: list of span dicts from structured logging
        - schema_violations: list of schema validation violations
        - No provenance (reachability = 0)
    """
    from structured_logging_baseline import StructuredLoggingSession, SchemaValidator

    start_time = time.monotonic()
    start_ts = _utc_iso_z()
    errors: list[dict[str, Any]] = []

    # Create structured logging session
    session = StructuredLoggingSession(
        f"{task_spec.task_id}-structlog",
        schema=SchemaValidator(
            required_fields=["ts", "kind", "task_id"],
            field_types={"ts": str, "kind": str, "task_id": str},
        ),
    )

    # Prepare workspace
    workspace_dir = None
    if task_spec.workspace_setup:
        try:
            workspace_dir = task_spec.workspace_setup()
        except Exception as e:
            errors.append(_error_record(e, "workspace_setup"))
            session.record_error(e, context="workspace_setup")

    # Execute task with structured logging (placeholder for Plan 02-04)
    raw_output: str | None = None
    token_count = 0

    # In Plan 02-04, this will execute the task via the queue worker runtime
    # with structured logging session wrapping each turn and tool call.

    duration_ms = (time.monotonic() - start_time) * 1000
    report = session.get_report()

    return {
        "task_id": task_spec.task_id,
        "tier": task_spec.tier,
        "baseline_tier": "structured_logging",
        "raw_output": raw_output,
        "token_count": token_count,
        "duration_ms": round(duration_ms, 3),
        "start_timestamp": start_ts,
        "end_timestamp": _utc_iso_z(),
        "errors": errors,
        "spans": report.get("spans", []),
        "schema_violations": report.get("schema_violations", []),
        "turn_count": report.get("turn_count", 0),
        "tool_call_count": report.get("tool_call_count", 0),
        "workspace_dir": str(workspace_dir) if workspace_dir else None,
    }


# --- Tier 3: Forge-instrumented baseline ---


def run_task_forge_instrumented(
    task_spec: TaskSpec,
    adapter: Any = None,
) -> dict[str, Any]:
    """Run a task with the forge adapter (from Plan 02-02).

    Produces the forge measurement: execution with typed absence states,
    provenance DAG, hash-verified trace compression, and structural
    violation detection.

    Uses openclaw_adapter.OpenClawAdapter for lifecycle instrumentation.

    Args:
        task_spec: Task specification with prompt and workspace setup.
        adapter: Pre-configured OpenClawAdapter instance, or None to create one.

    Returns:
        Result dict with:
        - task_id, tier, raw_output, token_count, duration_ms, errors
        - chamber: sealed forge chamber dict
        - Provenance (reachability = computed from chamber)
        - Violations detected (detection_rate = computed)
    """
    from openclaw_adapter import OpenClawAdapter

    start_time = time.monotonic()
    start_ts = _utc_iso_z()
    errors: list[dict[str, Any]] = []

    # Create adapter if not provided
    if adapter is None:
        session_id = f"{task_spec.task_id}-forge-{int(time.time())}"
        adapter = OpenClawAdapter(session_id)

    # Prepare workspace
    workspace_dir = None
    if task_spec.workspace_setup:
        try:
            workspace_dir = task_spec.workspace_setup()
        except Exception as e:
            errors.append(_error_record(e, "workspace_setup"))

    # Execute task with forge instrumentation (placeholder for Plan 02-04)
    raw_output: str | None = None
    token_count = 0

    # In Plan 02-04, this will execute the task via the queue worker runtime
    # with the forge adapter wrapping append_ledger(), next_task(), and
    # advance_cursor_after_ledger().

    # Finalize the adapter
    try:
        chamber = adapter.finalize()
    except Exception as e:
        errors.append(_error_record(e, "adapter_finalize"))
        chamber = adapter.finalize_on_error(e)

    duration_ms = (time.monotonic() - start_time) * 1000

    return {
        "task_id": task_spec.task_id,
        "tier": task_spec.tier,
        "baseline_tier": "forge_instrumented",
        "raw_output": raw_output,
        "token_count": token_count,
        "duration_ms": round(duration_ms, 3),
        "start_timestamp": start_ts,
        "end_timestamp": _utc_iso_z(),
        "errors": errors,
        "chamber": chamber,
        "workspace_dir": str(workspace_dir) if workspace_dir else None,
    }


# --- Metric computation ---
#
# All formulas match CONVENTIONS.md #7 exactly.


def collect_metrics(
    uninstrumented_result: dict[str, Any],
    structured_result: dict[str, Any],
    forge_result: dict[str, Any],
) -> dict[str, Any]:
    """Compute all 5 canonical metrics from CONVENTIONS.md #7.

    Computes the differential between the three baseline tiers.

    Args:
        uninstrumented_result: Result from run_task_uninstrumented().
        structured_result: Result from run_task_structured_logging().
        forge_result: Result from run_task_forge_instrumented().

    Returns:
        Dict with metrics per tier and differential comparisons:
        - reachability_fraction: per tier
        - compression_ratio: forge only
        - vs_vanilla_pct: forge vs uninstrumented
        - detection_rate: per tier
        - false_positive_rate: per tier
    """
    # --- reachability_fraction ---
    # (reachable artifacts via BFS on provenance DAG) / (total artifacts)
    # Uninstrumented and structured logging: 0.0 (no provenance DAG)
    # Forge: computed from chamber

    forge_reachability = 0.0
    chamber = forge_result.get("chamber")
    if chamber and chamber.get("stages"):
        try:
            from openclaw_adapter import compute_reversibility_score
            forge_reachability = compute_reversibility_score(chamber)
        except Exception:
            forge_reachability = 0.0

    # --- compression_ratio ---
    # original_size / encoded_size (forge trace compression only)
    # N/A for uninstrumented and structured logging

    forge_compression_ratio: float | None = None
    forge_encoded_size: int = 0
    forge_original_size: int = 0

    if chamber and chamber.get("stages"):
        try:
            from forge_trace_codec import encode_trace, trace_stats
            trace = encode_trace(chamber)
            stats = trace_stats(trace)
            forge_original_size = stats.get("original_bytes", 0)
            forge_encoded_size = stats.get("encoded_bytes", 0)
            if forge_encoded_size > 0:
                forge_compression_ratio = forge_original_size / forge_encoded_size
        except Exception:
            forge_compression_ratio = None

    # --- vs_vanilla_pct ---
    # (forge_size - vanilla_size) / vanilla_size * 100
    # Negative = forge is smaller; positive = forge is larger

    vanilla_size = uninstrumented_result.get("token_count", 0)
    forge_size = forge_result.get("token_count", 0)

    # Use payload size if token counts are not available
    if vanilla_size == 0 and forge_size == 0:
        vanilla_payload = json.dumps(uninstrumented_result, default=str)
        forge_payload = json.dumps(forge_result, default=str)
        vanilla_size = len(vanilla_payload.encode("utf-8"))
        forge_size = len(forge_payload.encode("utf-8"))

    vs_vanilla_pct: float | None = None
    if vanilla_size > 0:
        vs_vanilla_pct = ((forge_size - vanilla_size) / vanilla_size) * 100

    # --- detection_rate ---
    # violations_detected / total_violations
    # Uninstrumented: 0 (no violation detection)
    # Structured logging: schema violations / total (schema catches some)
    # Forge: structural violations / total (forge catches structural)

    uninstrumented_detection = 0.0
    structured_detection = 0.0
    forge_detection = 0.0

    # Structured logging detection: count schema violations found
    structured_violations = structured_result.get("schema_violations", [])
    # Note: structured logging detects malformed responses (schema violations)
    # but NOT structural violations (illegal state transitions, missing absence labels)

    # Forge detection: count structural violations found via chamber validation
    forge_violations_detected = 0
    if chamber:
        try:
            from forge_chamber import validate_chamber
            validation_errors = validate_chamber(chamber)
            forge_violations_detected = len(validation_errors)
        except Exception:
            pass

    # Total violations: determined during execution (injected or naturally occurring)
    # For clean runs, total_violations = 0 and detection_rate is N/A
    # For violation-injected runs, total_violations is known a priori
    # Store raw counts; let the caller compute rates when total is known

    # --- false_positive_rate ---
    # false_alarms / clean_runs
    # Measured on uninstrumented clean runs: any violations reported = false positive

    # false_positive tracking stored as raw counts for bootstrap CI computation

    return {
        "task_id": uninstrumented_result.get("task_id", ""),
        "tier": uninstrumented_result.get("tier", ""),

        # Per-tier reachability
        "reachability_fraction": {
            "uninstrumented": 0.0,
            "structured_logging": 0.0,
            "forge": forge_reachability,
        },

        # Forge trace compression (Convention #7: forge compaction only)
        "compression_ratio": forge_compression_ratio,
        "forge_original_bytes": forge_original_size,
        "forge_encoded_bytes": forge_encoded_size,

        # Overhead vs vanilla (Convention #7)
        "vs_vanilla_pct": vs_vanilla_pct,
        "vanilla_payload_bytes": vanilla_size,
        "forge_payload_bytes": forge_size,

        # Detection (raw counts -- rates computed when total_violations known)
        "detection": {
            "uninstrumented": {
                "violations_detected": 0,
                "false_alarms": 0,
            },
            "structured_logging": {
                "violations_detected": len(structured_violations),
                "schema_violations": structured_violations,
                "false_alarms": 0,
            },
            "forge": {
                "violations_detected": forge_violations_detected,
                "false_alarms": 0,
            },
        },

        # Timing
        "duration_ms": {
            "uninstrumented": uninstrumented_result.get("duration_ms", 0),
            "structured_logging": structured_result.get("duration_ms", 0),
            "forge": forge_result.get("duration_ms", 0),
        },

        # Token counts
        "token_count": {
            "uninstrumented": uninstrumented_result.get("token_count", 0),
            "structured_logging": structured_result.get("token_count", 0),
            "forge": forge_result.get("token_count", 0),
        },
    }


def compute_detection_rate(
    violations_detected: int,
    total_violations: int,
) -> float | None:
    """Compute detection rate: violations_detected / total_violations.

    Returns None if total_violations is 0 (rate undefined on clean runs).

    Convention #7: detection_rate in [0, 1].
    """
    if total_violations == 0:
        return None
    return violations_detected / total_violations


def compute_false_positive_rate(
    false_alarms: int,
    clean_runs: int,
) -> float | None:
    """Compute false positive rate: false_alarms / clean_runs.

    Returns None if clean_runs is 0.

    Convention #7: false_positive_rate in [0, 1].
    """
    if clean_runs == 0:
        return None
    return false_alarms / clean_runs


# --- Bootstrap confidence intervals ---


def bootstrap_ci(
    values: list[float],
    confidence: float = 0.95,
    n_resamples: int = 10_000,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for small samples.

    Uses the percentile method with numpy for resampling.

    Args:
        values: Sample values.
        confidence: Confidence level (default 0.95 for 95% CI).
        n_resamples: Number of bootstrap resamples.

    Returns:
        (lower, upper) bounds of the confidence interval.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute bootstrap CI on empty values")

    if len(values) == 1:
        # Single value: CI is the value itself (no uncertainty estimate possible)
        return (values[0], values[0])

    try:
        import numpy as np
    except ImportError:
        # Fallback: use stdlib random for resampling (less efficient)
        return _bootstrap_ci_stdlib(values, confidence, n_resamples)

    arr = np.array(values, dtype=np.float64)
    rng = np.random.default_rng(seed=42)  # Fixed seed for reproducibility

    # Resample and compute statistic (mean)
    boot_means = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means[i] = np.mean(sample)

    alpha = 1 - confidence
    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    return (lower, upper)


def _bootstrap_ci_stdlib(
    values: list[float],
    confidence: float,
    n_resamples: int,
) -> tuple[float, float]:
    """Stdlib fallback for bootstrap CI (no numpy required)."""
    import random

    random.seed(42)  # Fixed seed for reproducibility
    n = len(values)

    boot_means: list[float] = []
    for _ in range(n_resamples):
        sample = [random.choice(values) for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = 1 - confidence
    lower_idx = int(n_resamples * alpha / 2)
    upper_idx = int(n_resamples * (1 - alpha / 2)) - 1

    return (boot_means[lower_idx], boot_means[upper_idx])


# --- Result persistence ---


def persist_results(
    results: list[dict[str, Any]],
    output_dir: str | Path,
) -> None:
    """Save all raw data and computed metrics to JSON files.

    Creates output_dir if it does not exist. Writes:
    - raw_results.json: all per-run results
    - metrics.json: per-task computed metrics
    - aggregate_metrics.json: aggregate metrics with bootstrap CIs

    Args:
        results: List of result dicts (one per run per tier).
        output_dir: Directory to write output files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save raw results
    raw_path = output_dir / "raw_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": _utc_iso_z(),
                "run_count": len(results),
                "results": results,
            },
            f,
            indent=2,
            default=str,
        )

    # Group results by task_id and baseline_tier
    grouped: dict[str, dict[str, list[dict]]] = {}
    for r in results:
        task_id = r.get("task_id", "unknown")
        tier = r.get("baseline_tier", "unknown")
        if task_id not in grouped:
            grouped[task_id] = {}
        if tier not in grouped[task_id]:
            grouped[task_id][tier] = []
        grouped[task_id][tier].append(r)

    # Compute per-task metrics
    task_metrics: dict[str, Any] = {}
    for task_id, tier_runs in grouped.items():
        task_metrics[task_id] = {
            "tiers": {},
            "run_counts": {tier: len(runs) for tier, runs in tier_runs.items()},
        }
        for tier, runs in tier_runs.items():
            durations = [r.get("duration_ms", 0) for r in runs]
            tokens = [r.get("token_count", 0) for r in runs]

            tier_metric: dict[str, Any] = {
                "run_count": len(runs),
                "duration_ms": {
                    "mean": sum(durations) / len(durations) if durations else 0,
                },
                "token_count": {
                    "mean": sum(tokens) / len(tokens) if tokens else 0,
                },
            }

            # Bootstrap CIs for samples with N >= 2
            if len(durations) >= 2:
                ci = bootstrap_ci(durations)
                tier_metric["duration_ms"]["ci_95"] = list(ci)
            if len(tokens) >= 2:
                ci = bootstrap_ci(tokens)
                tier_metric["token_count"]["ci_95"] = list(ci)

            task_metrics[task_id]["tiers"][tier] = tier_metric

    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": _utc_iso_z(),
                "task_metrics": task_metrics,
            },
            f,
            indent=2,
            default=str,
        )

    # Compute aggregate metrics across all tasks
    all_durations = {
        "uninstrumented": [],
        "structured_logging": [],
        "forge_instrumented": [],
    }
    for r in results:
        tier = r.get("baseline_tier", "")
        if tier in all_durations:
            all_durations[tier].append(r.get("duration_ms", 0))

    aggregate: dict[str, Any] = {
        "total_runs": len(results),
        "tasks": list(grouped.keys()),
    }

    for tier, durations in all_durations.items():
        if durations:
            agg: dict[str, Any] = {
                "run_count": len(durations),
                "duration_ms_mean": sum(durations) / len(durations),
            }
            if len(durations) >= 2:
                ci = bootstrap_ci(durations)
                agg["duration_ms_ci_95"] = list(ci)
            aggregate[tier] = agg

    agg_path = output_dir / "aggregate_metrics.json"
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": _utc_iso_z(),
                "aggregate": aggregate,
            },
            f,
            indent=2,
            default=str,
        )


# --- Utilities ---


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _error_record(error: Exception, context: str) -> dict[str, Any]:
    return {
        "timestamp": _utc_iso_z(),
        "error_type": type(error).__name__,
        "message": str(error),
        "context": context,
    }


# --- CLI entry point ---


def main() -> None:
    """Run a demo measurement to verify the framework works."""
    print("Baseline Measurement Framework")
    print("=" * 50)
    print()

    # Create a test task spec
    spec = TaskSpec(
        task_id="TASK-DEMO",
        tier="short",
        prompt="Demo task for framework verification.",
        expected_tokens=(1000, 5000),
    )

    print(f"Task: {spec.task_id} ({spec.tier})")
    print(f"Expected tokens: {spec.expected_tokens}")
    print()

    # Run all three tiers
    print("Tier 1: Uninstrumented...")
    r1 = run_task_uninstrumented(spec)
    print(f"  Duration: {r1['duration_ms']:.1f} ms")

    print("Tier 2: Structured logging...")
    r2 = run_task_structured_logging(spec)
    print(f"  Duration: {r2['duration_ms']:.1f} ms")
    print(f"  Schema violations: {len(r2.get('schema_violations', []))}")

    print("Tier 3: Forge instrumented...")
    r3 = run_task_forge_instrumented(spec)
    print(f"  Duration: {r3['duration_ms']:.1f} ms")
    print(f"  Chamber stages: {len(r3.get('chamber', {}).get('stages', []))}")

    print()

    # Compute metrics
    print("Computing metrics...")
    metrics = collect_metrics(r1, r2, r3)
    print(f"  Reachability (forge): {metrics['reachability_fraction']['forge']}")
    print(f"  Compression ratio: {metrics['compression_ratio']}")
    print(f"  vs_vanilla_pct: {metrics['vs_vanilla_pct']}")

    print()

    # Test bootstrap CI
    print("Bootstrap CI test...")
    test_values = [1.0, 2.0, 3.0, 4.0, 5.0]
    ci = bootstrap_ci(test_values)
    print(f"  Values: {test_values}")
    print(f"  95% CI: ({ci[0]:.3f}, {ci[1]:.3f})")

    # Test edge cases
    print("  Single value CI:", bootstrap_ci([42.0]))

    print()

    # Persist results
    output_dir = Path(__file__).parent / "baseline_demo_output"
    print(f"Persisting to {output_dir}...")
    persist_results([r1, r2, r3], output_dir)
    print("  raw_results.json written")
    print("  metrics.json written")
    print("  aggregate_metrics.json written")

    print()
    print("Framework verification complete.")
    print()

    # Canonical metrics from CONVENTIONS.md #7:
    print("Canonical Metrics (CONVENTIONS.md #7):")
    print(f"  1. reachability_fraction: {metrics['reachability_fraction']}")
    print(f"  2. compression_ratio: {metrics['compression_ratio']}")
    print(f"  3. vs_vanilla_pct: {metrics['vs_vanilla_pct']}")
    print(f"  4. detection_rate: raw counts = {metrics['detection']}")
    print(f"  5. false_positive_rate: per-tier in detection dict")


if __name__ == "__main__":
    main()
