"""Campaign execution runner for Phase 7 adversarial violation campaign.

Dispatches adversarial tasks with full forge instrumentation, records all 7
required instrumentation channels per run, manages stress level progression,
handles timeouts and partial runs, and produces per-run JSONL output.

7 Instrumentation Channels (per RESEARCH Section 5.4):
  1. Forge chamber     -- complete provenance DAG, artifact states, refs, seals
  2. Raw LLM transcript -- input/output for every LLM call
  3. Tool call log      -- every tool invocation with I/O, timing, errors
  4. Compaction events  -- when/how context was compacted (if observable)
  5. Token counts       -- per-call and cumulative
  6. Wall clock time    -- start, end, per-step timing
  7. Framework version  -- exact version of runtime under test

Backends:
  mock       -- uses MockLM to generate synthetic but structurally valid data
  openclaw   -- real OpenClaw/Zarathustra sessions (requires API)
  claude-code -- real Claude Code sessions (requires API)

Convention assertions (project-specific -- physics conventions N/A):
  violation_classification = "structural only (CONVENTIONS.md #8)"
  compaction_disambiguation = "forge compaction = lossless; LLM compaction = lossy"
  all_metrics_dimensionless = True

References:
  - 07-RESEARCH.md Section 5.4 (instrumentation requirements)
  - ReliabilityBench (arxiv:2601.06112) stress calibration
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from adversarial_corpus import (
    AdversarialCorpus,
    AdversarialTask,
    STRESS_LEVELS,
    VALID_STRESS_LEVELS,
    TIER_DEFAULTS,
)
from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_nulls import AbsenceState


# ---------------------------------------------------------------------------
# Framework version
# ---------------------------------------------------------------------------

FRAMEWORK_VERSION = "primordial-v2.0-phase7"


# ---------------------------------------------------------------------------
# Run result schema
# ---------------------------------------------------------------------------

def _empty_run_result(
    task_id: str,
    stress_level: str,
    run_index: int,
) -> dict:
    """Create an empty run result with all 7 channels initialized."""
    run_id = f"{task_id}_{stress_level}_{run_index:03d}"
    return {
        "run_id": run_id,
        "task_id": task_id,
        "stress_level": stress_level,
        "run_index": run_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # Channel 1: Forge chamber
        "chamber": {},

        # Channel 2: Raw LLM transcript
        "transcript": [],

        # Channel 3: Tool call log
        "tool_call_log": [],

        # Channel 4: Compaction events
        "compaction_events": [],

        # Channel 5: Token counts
        "token_count": {"per_call": [], "cumulative": 0},

        # Channel 6: Wall clock
        "wall_clock_seconds": 0.0,

        # Channel 7: Framework version
        "framework_version": FRAMEWORK_VERSION,

        # Meta
        "task_completed": False,
        "task_success": False,
        "timed_out": False,
        "errors": [],
    }


def validate_run_result(result: dict) -> list[str]:
    """Validate a run result has all 7 channels with correct types.

    Returns list of validation errors (empty = valid).
    """
    errors = []
    required_fields = {
        "run_id": str,
        "task_id": str,
        "stress_level": str,
        "run_index": int,
        "timestamp": str,
        "chamber": dict,
        "transcript": list,
        "tool_call_log": list,
        "compaction_events": list,
        "token_count": dict,
        "wall_clock_seconds": (int, float),
        "framework_version": str,
        "task_completed": bool,
        "task_success": bool,
        "errors": list,
    }
    for field_name, expected_type in required_fields.items():
        if field_name not in result:
            errors.append(f"Missing field: {field_name}")
        elif not isinstance(result[field_name], expected_type):
            errors.append(
                f"Field {field_name}: expected {expected_type}, "
                f"got {type(result[field_name])}"
            )

    # Token count substructure
    if "token_count" in result and isinstance(result["token_count"], dict):
        tc = result["token_count"]
        if "per_call" not in tc:
            errors.append("token_count missing 'per_call'")
        if "cumulative" not in tc:
            errors.append("token_count missing 'cumulative'")
        elif not isinstance(tc["cumulative"], (int, float)):
            errors.append(f"token_count.cumulative: expected number, got {type(tc['cumulative'])}")

    return errors


# ---------------------------------------------------------------------------
# Mock LLM Backend
# ---------------------------------------------------------------------------

class MockLMBackend:
    """Synthetic backend for dry-run testing.

    Generates structurally valid forge chambers, transcripts, and tool call
    logs without real API calls. Output schema is identical to real runs.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._call_count = 0

    def run_task(
        self,
        task: AdversarialTask,
        stress_config: dict,
    ) -> dict:
        """Execute a task with MockLM, producing all 7 channels."""
        import random
        rng = random.Random(self._seed + hash(task.task_id))

        workspace = task.generate_workspace()
        prompt = task.generate_prompt(stress_config["stress_level"])
        start_time = time.monotonic()

        # --- Channel 1: Build forge chamber ---
        chamber_id = f"chamber:campaign:{task.task_id}:{stress_config['stress_level']}:v1"
        chamber = create_chamber(chamber_id)

        # Simulate N steps based on tier
        n_steps = {"SHORT": 2, "MEDIUM": 5, "LONG": 8, "EXTREME": 12}.get(task.tier, 3)
        artifact_ids = []

        for step in range(n_steps):
            seat = f"agent-step-{step}"
            stage_id = f"artifact:campaign:{task.task_id}:stage:{seat}:r1"

            # Build source_refs chain
            source_refs = []
            if artifact_ids:
                source_refs.append(artifact_ids[-1])
            if len(artifact_ids) >= 3 and step % 3 == 0:
                source_refs.append(artifact_ids[-3])

            output_text = f"Step {step} output for {task.task_id} ({len(prompt)} chars prompt)"

            artifact = create_v1_stage_artifact(
                stage_id=stage_id,
                seat=seat,
                producer_name="mock-lm",
                producer_role="agent",
                output=output_text,
                source_refs=source_refs,
            )
            summary = create_v1_stage_summary(
                artifact,
                f"Summary of step {step}",
                extra_source_refs=source_refs,
            )
            register_stage(chamber, artifact, summary)
            artifact_ids.append(stage_id)

        seal_chamber(chamber)

        # Serialize chamber (sets must become lists for JSON)
        chamber_serializable = _serialize_chamber(chamber)

        # --- Channel 2: Transcript ---
        transcript = []
        for step in range(n_steps):
            tokens_in = rng.randint(100, 500)
            tokens_out = rng.randint(200, 800)
            transcript.append({
                "role": "user",
                "content": f"Step {step} instruction ({len(prompt)} chars)",
                "tokens": tokens_in,
            })
            transcript.append({
                "role": "assistant",
                "content": f"Step {step} response for {task.task_id}",
                "tokens": tokens_out,
            })

        # --- Channel 3: Tool call log ---
        tool_call_log = []
        tools = workspace.get("tools", [])
        for step in range(n_steps):
            tool_name = tools[step % len(tools)] if tools else "generic_tool"
            duration = rng.randint(50, 2000)
            error = None
            # Inject tool failures based on lambda
            if rng.random() < stress_config.get("tool_failure_rate", 0.0):
                error = "Simulated tool failure (stress injection)"

            tool_call_log.append({
                "tool": tool_name,
                "call_id": f"call_{step:03d}",
                "input": {"step": step, "args": f"args_for_{tool_name}"},
                "output": {"result": f"output_step_{step}"} if error is None else None,
                "duration_ms": duration,
                "error": error,
            })

        # --- Channel 4: Compaction events ---
        compaction_events = []
        # Simulate LLM compaction for LONG/EXTREME tiers
        if task.tier in ("LONG", "EXTREME") and n_steps > 5:
            compaction_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "llm_context_compaction",
                "tokens_before": sum(
                    t["tokens"] for t in transcript
                ),
                "tokens_after": int(sum(
                    t["tokens"] for t in transcript
                ) * 0.6),
            })

        # --- Channel 5: Token counts ---
        per_call_tokens = [t["tokens"] for t in transcript]
        cumulative = sum(per_call_tokens)

        # --- Channel 6: Wall clock ---
        wall_clock = time.monotonic() - start_time

        return {
            "chamber": chamber_serializable,
            "transcript": transcript,
            "tool_call_log": tool_call_log,
            "compaction_events": compaction_events,
            "token_count": {"per_call": per_call_tokens, "cumulative": cumulative},
            "wall_clock_seconds": wall_clock,
            "task_completed": True,
            "task_success": True,
            "errors": [],
        }


def _serialize_chamber(chamber: dict) -> dict:
    """Convert chamber to JSON-serializable form (sets -> sorted lists)."""
    result = dict(chamber)
    if "artifact_index" in result and isinstance(result["artifact_index"], set):
        result["artifact_index"] = sorted(result["artifact_index"])
    # Deep-copy stages to avoid mutation
    if "stages" in result:
        serialized_stages = []
        for stage in result["stages"]:
            s = dict(stage)
            serialized_stages.append(s)
        result["stages"] = serialized_stages
    return result


# ---------------------------------------------------------------------------
# Campaign Runner
# ---------------------------------------------------------------------------

class CampaignRunner:
    """Campaign execution engine for adversarial violation detection.

    Dispatches tasks at graduated stress levels, records all 7 instrumentation
    channels, supports resume, handles timeouts and partial runs.
    """

    def __init__(
        self,
        corpus: AdversarialCorpus | None = None,
        output_dir: str = "data/campaign/runs",
        dry_run: bool = False,
        backend: str = "mock",
        seed: int = 42,
    ):
        self.corpus = corpus or AdversarialCorpus()
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.backend_name = backend
        self.seed = seed

        # Initialize backend
        if backend == "mock" or dry_run:
            self._backend = MockLMBackend(seed=seed)
        else:
            # Real backends would be initialized here
            raise NotImplementedError(
                f"Backend '{backend}' not yet implemented. Use 'mock' for dry-run."
            )

        # Ensure output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Status tracking
        self._completed_runs: set[str] = set()
        self._failed_runs: set[str] = set()
        self._load_completed()

    def _load_completed(self):
        """Scan output_dir for completed runs (for resume support)."""
        if not self.output_dir.exists():
            return
        for f in self.output_dir.glob("*.json"):
            if f.name == "campaign_status.json":
                continue
            try:
                with open(f) as fh:
                    data = json.load(fh)
                run_id = data.get("run_id", f.stem)
                if data.get("errors") and not data.get("task_completed"):
                    self._failed_runs.add(run_id)
                else:
                    self._completed_runs.add(run_id)
            except (json.JSONDecodeError, IOError):
                pass

    def _make_run_id(self, task_id: str, stress_level: str, run_index: int) -> str:
        return f"{task_id}_{stress_level}_{run_index:03d}"

    def run_single(
        self,
        task_id: str,
        stress_level: str = "control",
        run_index: int = 0,
    ) -> dict:
        """Execute one run. Returns result dict with all 7 channels."""
        run_id = self._make_run_id(task_id, stress_level, run_index)

        # Skip if already completed (resume support)
        if run_id in self._completed_runs:
            return self._load_run(run_id)

        task = self.corpus.get_task(task_id)
        stress_config = task.get_stress_config(stress_level)

        result = _empty_run_result(task_id, stress_level, run_index)
        result["run_id"] = run_id

        # Timeout configuration
        tier_config = TIER_DEFAULTS.get(task.tier, {"timeout_minutes": 30})
        timeout_seconds = tier_config["timeout_minutes"] * 60

        start_time = time.monotonic()

        try:
            backend_result = self._backend.run_task(task, stress_config)

            # Merge backend results into our result structure
            result["chamber"] = backend_result.get("chamber", {})
            result["transcript"] = backend_result.get("transcript", [])
            result["tool_call_log"] = backend_result.get("tool_call_log", [])
            result["compaction_events"] = backend_result.get("compaction_events", [])
            result["token_count"] = backend_result.get("token_count", {"per_call": [], "cumulative": 0})
            result["task_completed"] = backend_result.get("task_completed", False)
            result["task_success"] = backend_result.get("task_success", False)
            result["errors"] = backend_result.get("errors", [])

        except TimeoutError:
            result["timed_out"] = True
            result["errors"].append(f"Timed out after {timeout_seconds}s")

        except Exception as e:
            result["errors"].append(f"Run failed: {type(e).__name__}: {str(e)}")

        # Channel 6: Wall clock (always measured, even on error)
        result["wall_clock_seconds"] = time.monotonic() - start_time

        # Channel 7: Framework version (always set)
        result["framework_version"] = FRAMEWORK_VERSION

        # Persist run result immediately
        self._save_run(result)
        self._completed_runs.add(run_id)

        return result

    def run_task_battery(
        self,
        task_id: str,
        runs_per_level: int = 3,
    ) -> list[dict]:
        """Run all stress levels for one task.

        Returns list of result dicts (one per stress level per repetition).
        """
        results = []
        run_index = 0
        for level in STRESS_LEVELS:
            for rep in range(runs_per_level):
                result = self.run_single(task_id, level, run_index)
                results.append(result)
                run_index += 1
        return results

    def run_full_campaign(
        self,
        resume_from: str | None = None,
    ) -> dict:
        """Run entire campaign. Supports resume.

        Args:
            resume_from: Optional task_id to resume from (skip earlier tasks).

        Returns:
            Campaign summary dict.
        """
        manifest = self.corpus.generate_manifest()
        all_results = []
        started = resume_from is None
        total_planned = manifest["total_planned_runs"]
        completed_count = 0
        failed_count = 0

        for task_meta in manifest["tasks"]:
            task_id = task_meta["task_id"]
            runs_planned = task_meta["runs_planned"]

            if not started:
                if task_id == resume_from:
                    started = True
                else:
                    continue

            # Distribute runs across stress levels
            # 4 levels, roughly equal distribution
            levels = list(STRESS_LEVELS.keys())
            runs_per_level = max(1, runs_planned // len(levels))
            remainder = runs_planned - (runs_per_level * len(levels))

            run_index = 0
            for i, level in enumerate(levels):
                count = runs_per_level + (1 if i < remainder else 0)
                for rep in range(count):
                    try:
                        result = self.run_single(task_id, level, run_index)
                        all_results.append(result)
                        if result.get("task_completed"):
                            completed_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                    run_index += 1

        # Update campaign status
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_planned": total_planned,
            "completed": completed_count,
            "failed": failed_count,
            "skipped": total_planned - completed_count - failed_count,
            "framework_version": FRAMEWORK_VERSION,
        }
        self._save_status(status)

        return status

    def get_campaign_status(self) -> dict:
        """Return progress: completed/total/failed/skipped per task."""
        manifest = self.corpus.generate_manifest()
        total_planned = manifest["total_planned_runs"]

        # Load status from disk if available
        status_path = self.output_dir / "campaign_status.json"
        if status_path.exists():
            with open(status_path) as f:
                stored = json.load(f)
        else:
            stored = {}

        # Count from completed runs
        completed = len(self._completed_runs)
        failed = len(self._failed_runs)

        per_task = {}
        for task_meta in manifest["tasks"]:
            task_id = task_meta["task_id"]
            task_completed = sum(
                1 for r in self._completed_runs if r.startswith(task_id)
            )
            task_failed = sum(
                1 for r in self._failed_runs if r.startswith(task_id)
            )
            per_task[task_id] = {
                "planned": task_meta["runs_planned"],
                "completed": task_completed,
                "failed": task_failed,
                "remaining": task_meta["runs_planned"] - task_completed - task_failed,
            }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_planned": total_planned,
            "completed": completed,
            "failed": failed,
            "skipped": max(0, total_planned - completed - failed),
            "per_task": per_task,
            "framework_version": FRAMEWORK_VERSION,
        }

    # --- Persistence ---

    def _save_run(self, result: dict):
        """Write a single run result to disk."""
        run_id = result["run_id"]
        path = self.output_dir / f"{run_id}.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=2, default=str)

    def _load_run(self, run_id: str) -> dict:
        """Load a run result from disk."""
        path = self.output_dir / f"{run_id}.json"
        with open(path) as f:
            return json.load(f)

    def _save_status(self, status: dict):
        """Write campaign status to disk."""
        path = self.output_dir / "campaign_status.json"
        with open(path, "w") as f:
            json.dump(status, f, indent=2)

    def clean_output(self):
        """Remove all run results and status (for testing)."""
        if self.output_dir.exists():
            for f in self.output_dir.glob("*.json"):
                f.unlink()
        self._completed_runs.clear()
        self._failed_runs.clear()
