#!/usr/bin/env python3
"""Execute the full 201-run adversarial campaign (Plan 07-03, Task 1).

Execution order per plan spec:
1. Backend prerequisite check (MockLM fallback)
2. Pilot batch (10 runs) -- verify pipeline end-to-end
3. Tier A battery (120 runs) -- highest violation likelihood
4. Tier B battery (68 runs) -- lower probability, needed for coverage
5. Control battery (21 runs) -- expected 0 violations

Convention assertions:
  violation_classification = "structural only (CONVENTIONS.md #8)"
  compaction_disambiguation = "forge compaction = lossless; LLM compaction = lossy"
  all_metrics_dimensionless = True
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

_project_root = _tools_dir.parent
os.chdir(_project_root)

from adversarial_corpus import AdversarialCorpus, STRESS_LEVELS
from campaign_runner import CampaignRunner, MockLMBackend, validate_run_result

# ---------------------------------------------------------------------------
# Campaign configuration (from 07-03-PLAN.md)
# ---------------------------------------------------------------------------

STRESS_LEVEL_LIST = ["control", "mild", "moderate", "heavy"]

# Pilot batch: 1 representative task per category/stress combo
PILOT_TASKS = [
    ("TASK-C9a", "control"),
    ("TASK-A1a", "moderate"),
    ("TASK-A2a", "heavy"),
    ("TASK-B5a", "mild"),
    ("TASK-C9b", "control"),
    ("TASK-A3a", "moderate"),
    ("TASK-A4a", "heavy"),
    ("TASK-B6a", "moderate"),
    ("TASK-B7a", "heavy"),
    ("TASK-B8a", "moderate"),
]

# Tier A tasks and their planned runs (total 112 from manifest)
TIER_A_TASKS = {
    "TASK-A1a": 12, "TASK-A1b": 12, "TASK-A1c": 12,
    "TASK-A2a": 12, "TASK-A2b": 12, "TASK-A2c": 12,
    "TASK-A3a": 10, "TASK-A3b": 10,
    "TASK-A4a": 10, "TASK-A4b": 10,
}

# Tier B tasks (total 68)
TIER_B_TASKS = {
    "TASK-B5a": 10, "TASK-B5b": 10,
    "TASK-B6a": 10, "TASK-B6b": 10,
    "TASK-B7a": 10, "TASK-B7b": 10,
    "TASK-B8a": 8,
}

# Control tasks (total 21)
CONTROL_TASKS = {
    "TASK-C9a": 7, "TASK-C9b": 7, "TASK-C9c": 7,
}

OUTPUT_DIR = "data/campaign/runs"
STATUS_FILE = "data/campaign/campaign_status.json"


def distribute_runs(total_runs: int) -> list[str]:
    """Distribute total_runs across 4 stress levels.

    Returns list of stress_level strings, one per run.
    """
    levels = []
    per_level = total_runs // 4
    remainder = total_runs % 4
    for i, level in enumerate(STRESS_LEVEL_LIST):
        count = per_level + (1 if i < remainder else 0)
        levels.extend([level] * count)
    return levels


def check_backend() -> str:
    """Backend prerequisite check. Returns backend name."""
    # Check OpenClaw/Zarathustra availability
    openclaw_available = False
    # In production, we would probe the API here.
    # For now, OpenClaw is not configured.

    if openclaw_available:
        return "openclaw"

    # MockLM is always available
    print("=" * 72)
    print("WARNING: BACKEND=mock")
    print("Campaign will exercise the full pipeline but violations can only")
    print("arise from forge instrumentation bugs, not real LLM behavior.")
    print("The RQ2b verdict MUST carry a 'pending live validation' qualifier.")
    print("=" * 72)
    return "mock"


def run_campaign():
    """Execute the full 201-run campaign."""
    start_time = datetime.now(timezone.utc)
    start_epoch = time.monotonic()

    # Step 1: Backend check
    backend = check_backend()

    # Initialize
    corpus = AdversarialCorpus()
    runner = CampaignRunner(
        corpus=corpus,
        output_dir=OUTPUT_DIR,
        backend=backend,
        seed=42,
    )

    # Track results
    total_planned = 201
    run_counter = 0
    failures = 0
    category_completed: dict[str, dict] = {}

    # Track which (task_id, stress_level) combos are used for pilots
    # so the main battery skips them
    pilot_run_ids: set[str] = set()

    def get_category(task_id: str) -> str:
        task = corpus.get_task(task_id)
        return task.category.split("-")[0]

    def execute_run(task_id: str, stress_level: str, run_index: int) -> dict:
        """Execute a single run and track results."""
        nonlocal run_counter, failures

        result = runner.run_single(task_id, stress_level, run_index)
        run_counter += 1

        cat = get_category(task_id)
        if cat not in category_completed:
            category_completed[cat] = {"completed": 0, "failed": 0}

        if result.get("task_completed"):
            category_completed[cat]["completed"] += 1
        else:
            failures += 1
            category_completed[cat]["failed"] += 1

        # Validate run result schema
        schema_errors = validate_run_result(result)
        if schema_errors:
            print(f"  SCHEMA ERROR in {result['run_id']}: {schema_errors}")

        return result

    def progress_checkpoint(phase_name: str):
        """Print progress checkpoint."""
        elapsed = time.monotonic() - start_epoch
        print(f"\n--- Progress Checkpoint ({phase_name}) ---")
        print(f"  Runs completed: {run_counter}/{total_planned}")
        print(f"  Failures: {failures}")
        print(f"  Elapsed: {elapsed:.1f}s")
        for cat in sorted(category_completed.keys()):
            s = category_completed[cat]
            print(f"    {cat}: completed={s['completed']}, failed={s['failed']}")
        print("---\n")

    # -----------------------------------------------------------------------
    # Phase 1: Pilot batch (10 runs)
    # -----------------------------------------------------------------------
    print("\n=== PHASE 1: PILOT BATCH (10 runs) ===\n")
    pilot_results = []
    for task_id, stress_level in PILOT_TASKS:
        # Use run_index 900+ for pilot runs to avoid collision with main battery
        pilot_idx = 900 + len(pilot_results)
        result = execute_run(task_id, stress_level, pilot_idx)
        pilot_results.append(result)
        pilot_run_ids.add(result["run_id"])

        # Verify all 7 channels present
        channels_ok = all([
            isinstance(result.get("chamber"), dict) and bool(result["chamber"]),
            isinstance(result.get("transcript"), list),
            isinstance(result.get("tool_call_log"), list),
            isinstance(result.get("compaction_events"), list),
            isinstance(result.get("token_count"), dict),
            isinstance(result.get("wall_clock_seconds"), (int, float)),
            isinstance(result.get("framework_version"), str),
        ])
        status = "OK" if channels_ok else "MISSING_CHANNELS"
        print(f"  Pilot: {task_id:12s} @ {stress_level:10s} -> {status}")

    progress_checkpoint("After Pilot")

    pilot_failures = sum(1 for r in pilot_results if not r.get("task_completed"))
    if pilot_failures > 3:
        print(f"WARNING: {pilot_failures}/10 pilot runs failed.")

    # -----------------------------------------------------------------------
    # Phase 2: Tier A battery
    # -----------------------------------------------------------------------
    print("\n=== PHASE 2: TIER A BATTERY ===\n")
    for task_id, total_runs in TIER_A_TASKS.items():
        stress_schedule = distribute_runs(total_runs)
        for run_index, stress_level in enumerate(stress_schedule):
            execute_run(task_id, stress_level, run_index)
        cat = get_category(task_id)
        print(f"  {task_id}: {total_runs} runs complete (category {cat})")

    progress_checkpoint("After Tier A")

    # -----------------------------------------------------------------------
    # Phase 3: Tier B battery
    # -----------------------------------------------------------------------
    print("\n=== PHASE 3: TIER B BATTERY ===\n")
    for task_id, total_runs in TIER_B_TASKS.items():
        stress_schedule = distribute_runs(total_runs)
        for run_index, stress_level in enumerate(stress_schedule):
            execute_run(task_id, stress_level, run_index)
        cat = get_category(task_id)
        print(f"  {task_id}: {total_runs} runs complete (category {cat})")

    progress_checkpoint("After Tier B")

    # -----------------------------------------------------------------------
    # Phase 4: Control battery
    # -----------------------------------------------------------------------
    print("\n=== PHASE 4: CONTROL BATTERY ===\n")
    for task_id, total_runs in CONTROL_TASKS.items():
        stress_schedule = distribute_runs(total_runs)
        for run_index, stress_level in enumerate(stress_schedule):
            execute_run(task_id, stress_level, run_index)
        print(f"  {task_id}: {total_runs} runs complete (control)")

    progress_checkpoint("After Controls")

    # -----------------------------------------------------------------------
    # Write campaign_status.json
    # -----------------------------------------------------------------------
    end_time = datetime.now(timezone.utc)
    elapsed_total = time.monotonic() - start_epoch

    all_tasks = {**TIER_A_TASKS, **TIER_B_TASKS, **CONTROL_TASKS}
    per_category_status: dict[str, dict] = {}
    for task_id, planned in all_tasks.items():
        cat = get_category(task_id)
        if cat not in per_category_status:
            per_category_status[cat] = {"planned": 0, "completed": 0, "failed": 0, "violations": 0}
        per_category_status[cat]["planned"] += planned

    for cat, stats in category_completed.items():
        if cat in per_category_status:
            per_category_status[cat]["completed"] = stats["completed"]
            per_category_status[cat]["failed"] = stats["failed"]

    campaign_status = {
        "campaign_id": "v2.0-viol04",
        "backend": backend,
        "backend_caveat": (
            "BACKEND=mock: violations are forge-layer only, not LLM-behavioral. "
            "RQ2b verdict must carry 'pending live validation' qualifier."
            if backend == "mock"
            else "Live backend: violations may arise from real LLM behavior."
        ),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "elapsed_seconds": round(elapsed_total, 2),
        "total_runs": run_counter,
        "completed": run_counter - failures,
        "failed": failures,
        "timed_out": 0,
        "per_category": per_category_status,
        "pilot_runs": len(pilot_results),
        "pilot_failures": pilot_failures,
        "framework_version": "primordial-v2.0-phase7",
        "seed": 42,
    }

    status_path = Path(STATUS_FILE)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, "w") as f:
        json.dump(campaign_status, f, indent=2)

    print(f"\n{'=' * 72}")
    print(f"CAMPAIGN COMPLETE")
    print(f"  Total runs: {run_counter}")
    print(f"  Completed: {run_counter - failures}")
    print(f"  Failed: {failures}")
    print(f"  Elapsed: {elapsed_total:.1f}s")
    print(f"  Backend: {backend}")
    print(f"  Status: {STATUS_FILE}")
    print(f"{'=' * 72}")

    return campaign_status


if __name__ == "__main__":
    run_campaign()
