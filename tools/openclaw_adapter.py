"""
openclaw_adapter.py -- Forge integration adapter for OpenClaw queue worker runtime.

Intercepts OpenClaw lifecycle events (task start/done, patch proposed/applied/failed/rejected,
cursor advancement) and registers each as a forge chamber artifact with typed absence states
and provenance refs.

Approach: Post-hoc JSONL ledger analysis (Approach 2 from compaction characterization,
docs/compaction-characterization.md). Parses queue_ledger.jsonl events after execution
and builds forge chambers from the event stream. Non-invasive: requires zero modifications
to the runtime.

Enhancement path: Real-time wrapping of append_ledger()/next_task() for live instrumentation
(Approach 1), deployable alongside queue_worker.py on the VM.

Convention compliance:
- All uses of "compaction" are qualified (LLM compaction vs forge trace compression).
- Absence states from forge_nulls.py V1_ABSENCE_STATES.
- Artifact IDs follow convention #5 (colon-separated hierarchical).
- Chamber IDs follow convention #5 (chamber:<seg1>:<seg2>[:<segN>]).
- Protocol version: forge.internal.v1.

Does NOT modify any existing forge tool code.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

# Ensure forge tools are importable from same directory
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from forge_chamber import (
    ForgeChamberError,
    create_chamber,
    register_stage,
    seal_chamber,
    validate_chamber,
)
from forge_nulls import AbsenceState, ForgeNullError
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import decode_trace, encode_trace, trace_stats, verify_trace


# --- Ledger event parsing ---


def parse_ledger_events(ledger_path: str) -> list[dict]:
    """Parse a queue_ledger.jsonl file into a list of event dicts.

    Each line must be valid JSON with required fields: ts, kind, task_id.
    Empty lines are skipped. Malformed lines raise ValueError.

    Args:
        ledger_path: Path to queue_ledger.jsonl file.

    Returns:
        List of event dicts in chronological order.

    Raises:
        FileNotFoundError: If ledger file does not exist.
        ValueError: If any line has invalid JSON or missing required fields.
    """
    required_fields = {"ts", "kind", "task_id"}
    events: list[dict] = []

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Ledger line {line_num}: invalid JSON: {e}"
                ) from e

            if not isinstance(event, dict):
                raise ValueError(
                    f"Ledger line {line_num}: expected JSON object, got {type(event).__name__}"
                )

            missing = required_fields - set(event.keys())
            if missing:
                raise ValueError(
                    f"Ledger line {line_num}: missing required fields: {sorted(missing)}"
                )

            events.append(event)

    return events


# --- Task lifecycle grouping ---


def group_events_by_task(events: list[dict]) -> list[dict]:
    """Group ledger events into task lifecycle sequences.

    A task lifecycle starts with a task.start event and ends with task.done.
    Patch events between task.start and task.done belong to that task.
    Patch events outside a task bracket are grouped as orphans.

    Returns:
        List of task group dicts:
        {
            "task_id": str,
            "events": [event_dicts],
            "started": bool,
            "completed": bool,
            "ok": bool | None,
        }
    """
    groups: list[dict] = []
    current_task: dict | None = None

    for event in events:
        kind = event["kind"]

        if kind == "task.start":
            # Close any open task without a task.done (abnormal termination)
            if current_task is not None:
                current_task["completed"] = False
                groups.append(current_task)

            current_task = {
                "task_id": event["task_id"],
                "events": [event],
                "started": True,
                "completed": False,
                "ok": None,
            }

        elif kind == "task.done":
            if current_task is not None and current_task["task_id"] == event["task_id"]:
                current_task["events"].append(event)
                current_task["completed"] = True
                current_task["ok"] = event.get("ok")
                groups.append(current_task)
                current_task = None
            else:
                # task.done without matching task.start -- record as standalone
                groups.append({
                    "task_id": event["task_id"],
                    "events": [event],
                    "started": False,
                    "completed": True,
                    "ok": event.get("ok"),
                })

        elif kind.startswith("patch."):
            if current_task is not None:
                current_task["events"].append(event)
            else:
                # Orphan patch event outside task bracket
                groups.append({
                    "task_id": event.get("task_id", "orphan"),
                    "events": [event],
                    "started": False,
                    "completed": False,
                    "ok": None,
                })

        else:
            # Unknown event kind -- attach to current task or record standalone
            if current_task is not None:
                current_task["events"].append(event)
            else:
                groups.append({
                    "task_id": event.get("task_id", "unknown"),
                    "events": [event],
                    "started": False,
                    "completed": False,
                    "ok": None,
                })

    # Close any trailing open task
    if current_task is not None:
        current_task["completed"] = False
        groups.append(current_task)

    return groups


# --- Adapter core ---


class OpenClawAdapter:
    """Forge integration adapter for the OpenClaw queue worker runtime.

    Intercepts lifecycle events from the OpenClaw queue worker's JSONL ledger
    and registers each as a forge chamber artifact. Implements all four
    interception points required by Plan 02-02:

    1. PER-TURN REGISTRATION: Each task lifecycle (task.start -> task.done) becomes
       a forge stage artifact with source_refs chain to the previous task.

    2. PER-TOOL-CALL REGISTRATION: Each patch event (proposed/applied/failed/rejected)
       becomes a child artifact with source_ref to parent task.

    3. LLM COMPACTION EVENT DETECTION: Cursor advancement (the queue worker's
       "forgetting" mechanism) is detected and registered as a forge compaction
       artifact with source_refs to all tasks behind the cursor.
       NOTE: This is cursor-based state loss, NOT LLM context-window compaction.
       The term "compact" in artifact IDs refers to the cursor advancement event
       that makes prior tasks invisible to the worker.

    4. CHAMBER LIFECYCLE: Chamber created at adapter instantiation, sealed on
       finalize(). Exception-safe: seal on error preserves partial data.
    """

    def __init__(self, session_id: str):
        """Initialize adapter with a unique session identifier.

        Args:
            session_id: Unique session identifier for this adapter run.
                        Used in chamber and artifact IDs.
        """
        self._session_id = session_id
        self._chamber = create_chamber(f"chamber:openclaw:{session_id}:v1")
        self._task_artifacts: list[str] = []
        self._subcall_counter: int = 0
        self._compaction_count: int = 0
        self._sealed: bool = False

    @property
    def chamber(self) -> dict:
        """The forge chamber being built by this adapter."""
        return self._chamber

    @property
    def session_id(self) -> str:
        """The session identifier for this adapter run."""
        return self._session_id

    # --- Per-turn registration (interception point 1) ---

    def register_task(
        self,
        task_id: str,
        *,
        output: str | None = None,
        ok: bool | None = None,
        detail: str = "",
        meta: dict | None = None,
    ) -> str:
        """Register a task lifecycle as a forge stage artifact.

        Maps one OpenClaw task (from task.start to task.done) to a forge
        stage artifact with provenance chain to the previous task.

        Args:
            task_id: The OpenClaw task identifier.
            output: Task output text, or None if task produced no output.
            ok: Whether the task completed successfully (from task.done event).
            detail: Additional detail string from the ledger event.
            meta: Metadata dict from the ledger event.

        Returns:
            The artifact ID of the registered task artifact.
        """
        if self._sealed:
            raise ForgeChamberError("Cannot register task in sealed adapter")

        iter_idx = len(self._task_artifacts)
        stage_id = f"artifact:openclaw:{self._session_id}:iter:{iter_idx}:r1"

        # Build source_refs chain: each task refs the previous one
        source_refs: list[str] = []
        if self._task_artifacts:
            source_refs.append(self._task_artifacts[-1])

        # Determine output and typed absence state
        if output is None:
            if ok is False:
                # Task failed -- output is absent due to failure
                output_state = AbsenceState.NOT_GENERATED
                effective_output = None
            else:
                # Task produced no output but may have succeeded
                output_state = AbsenceState.NOT_GENERATED
                effective_output = None
        else:
            output_state = None
            effective_output = output

        artifact = create_v1_stage_artifact(
            stage_id=stage_id,
            seat="openclaw-task",
            producer_name="openclaw-queue-worker",
            producer_role="task-executor",
            output=effective_output,
            output_state=output_state,
            source_refs=source_refs if source_refs else None,
        )

        # Build summary text with task lifecycle details
        summary_parts = [f"Task '{task_id}'"]
        if detail:
            summary_parts.append(f"detail='{detail}'")
        if ok is True:
            summary_parts.append("completed successfully")
        elif ok is False:
            summary_parts.append("failed")
        else:
            summary_parts.append("status unknown")

        summary = create_v1_stage_summary(
            artifact,
            ". ".join(summary_parts) + ".",
            extra_source_refs=source_refs if source_refs else None,
        )

        register_stage(self._chamber, artifact, summary)
        self._task_artifacts.append(stage_id)

        return stage_id

    # --- Per-tool-call registration (interception point 2) ---

    def register_patch(
        self,
        patch_id: str,
        kind: str,
        *,
        parent_task_artifact: str | None = None,
        detail: str = "",
        meta: dict | None = None,
    ) -> str:
        """Register a patch lifecycle event as a child artifact.

        Maps one OpenClaw patch event (proposed/applied/failed/rejected) to
        a forge stage artifact with source_ref to the parent task.

        Args:
            patch_id: The patch identifier (e.g., diff filename).
            kind: The patch event kind (patch.proposed, patch.applied, etc.).
            parent_task_artifact: Artifact ID of the parent task. If None,
                                  uses the most recent task artifact.
            detail: Additional detail string from the ledger event.
            meta: Metadata dict from the ledger event.

        Returns:
            The artifact ID of the registered patch artifact.
        """
        if self._sealed:
            raise ForgeChamberError("Cannot register patch in sealed adapter")

        subcall_idx = self._subcall_counter
        self._subcall_counter += 1

        stage_id = f"artifact:openclaw:{self._session_id}:subcall:{subcall_idx}:r1"

        # Build source_ref to parent task
        if parent_task_artifact is None:
            parent_task_artifact = (
                self._task_artifacts[-1] if self._task_artifacts else None
            )

        source_refs = [parent_task_artifact] if parent_task_artifact else None

        # Build output from patch event details
        output_parts = [f"Patch '{patch_id}': {kind}"]
        if detail:
            output_parts.append(f"detail='{detail}'")
        if meta:
            touched = meta.get("touched_files")
            if touched:
                output_parts.append(f"files={touched}")
            pre_val = meta.get("pre_validate")
            post_val = meta.get("post_validate")
            if pre_val or post_val:
                output_parts.append(f"pre={pre_val}, post={post_val}")

        output_text = ". ".join(output_parts)

        artifact = create_v1_stage_artifact(
            stage_id=stage_id,
            seat="openclaw-patch",
            producer_name="openclaw-queue-worker",
            producer_role="patch-processor",
            output=output_text,
            source_refs=source_refs,
        )

        summary = create_v1_stage_summary(
            artifact,
            f"Patch event: {kind} for '{patch_id}'.",
            extra_source_refs=source_refs,
        )

        register_stage(self._chamber, artifact, summary)

        return stage_id

    # --- Cursor advancement / LLM compaction detection (interception point 3) ---

    def register_cursor_advancement(
        self,
        *,
        old_cursor: int = 0,
        new_cursor: int = 0,
        task_ids_behind_cursor: list[str] | None = None,
    ) -> str:
        """Register a cursor advancement event as a forge compaction artifact.

        Cursor advancement is the OpenClaw queue worker's "forgetting" mechanism:
        once the cursor moves past a task, that task is invisible to the worker.
        This is analogous to LLM context-window compaction in that state becomes
        inaccessible, but differs in that the underlying data persists in the
        queue and ledger files. The forge adapter marks these tasks as
        pruned_recoverable (recoverable from the persistent files).

        NOTE: This is NOT LLM context-window compaction (lossy semantic
        summarization). This is cursor-based state loss at the queue worker layer.

        Args:
            old_cursor: Byte position before cursor advancement.
            new_cursor: Byte position after cursor advancement.
            task_ids_behind_cursor: Artifact IDs of tasks now behind the cursor.
                                    If None, uses all registered task artifacts.

        Returns:
            The artifact ID of the cursor advancement artifact.
        """
        if self._sealed:
            raise ForgeChamberError(
                "Cannot register cursor advancement in sealed adapter"
            )

        self._compaction_count += 1
        compact_id = (
            f"artifact:openclaw:{self._session_id}:compact:{self._compaction_count}:r1"
        )

        # Source refs point to all tasks that are now behind the cursor
        compacted_refs = (
            list(task_ids_behind_cursor)
            if task_ids_behind_cursor is not None
            else list(self._task_artifacts)
        )

        output_text = (
            f"Cursor advanced from byte {old_cursor} to {new_cursor}. "
            f"{len(compacted_refs)} task artifact(s) now behind cursor "
            f"(pruned_recoverable: data persists in queue and ledger files)."
        )

        artifact = create_v1_stage_artifact(
            stage_id=compact_id,
            seat="openclaw-cursor",
            producer_name="openclaw-queue-worker",
            producer_role="cursor-manager",
            output=output_text,
            source_refs=compacted_refs if compacted_refs else None,
        )

        summary = create_v1_stage_summary(
            artifact,
            f"Cursor advancement #{self._compaction_count}: "
            f"{len(compacted_refs)} task(s) now behind cursor.",
            extra_source_refs=compacted_refs if compacted_refs else None,
        )

        register_stage(self._chamber, artifact, summary)

        return compact_id

    # --- Chamber lifecycle (interception point 4) ---

    def finalize(self) -> dict:
        """Seal the chamber and return it.

        Idempotent: calling finalize() on an already-sealed adapter returns
        the existing chamber without error.

        Returns:
            The sealed forge chamber dict.
        """
        if not self._sealed and self._chamber["status"] == "open":
            seal_chamber(self._chamber)
            self._sealed = True
        return self._chamber

    def finalize_on_error(self, error: Exception) -> dict:
        """Seal the chamber on error to preserve partial data.

        Records the error as a final artifact before sealing.

        Args:
            error: The exception that caused the error.

        Returns:
            The sealed forge chamber dict.
        """
        if not self._sealed and self._chamber["status"] == "open":
            # Register error as final artifact
            error_idx = len(self._task_artifacts) + self._subcall_counter
            error_id = f"artifact:openclaw:{self._session_id}:error:{error_idx}:r1"

            source_refs = (
                [self._task_artifacts[-1]] if self._task_artifacts else None
            )

            try:
                artifact = create_v1_stage_artifact(
                    stage_id=error_id,
                    seat="openclaw-error",
                    producer_name="openclaw-adapter",
                    producer_role="error-handler",
                    output=f"Adapter error: {type(error).__name__}: {error}",
                    source_refs=source_refs,
                )
                summary = create_v1_stage_summary(
                    artifact,
                    f"Adapter terminated with error: {type(error).__name__}.",
                    extra_source_refs=source_refs,
                )
                register_stage(self._chamber, artifact, summary)
            except Exception:
                # Cannot register error artifact -- seal anyway
                pass

            seal_chamber(self._chamber)
            self._sealed = True

        return self._chamber


# --- Post-hoc ledger analysis (Approach 2 primary strategy) ---


def process_ledger(
    ledger_path: str,
    session_id: str,
    *,
    detect_cursor_advancement: bool = True,
) -> dict:
    """Process a queue_ledger.jsonl file and produce a forge chamber.

    This is the primary integration entry point (Approach 2: post-hoc JSONL
    analysis). Reads the ledger, groups events by task, and registers each
    task and its patch events as forge chamber artifacts.

    Cursor advancement detection: If enabled, detects sequences where a
    task.done is followed by a task.start with a different task_id. The
    completed task is considered "behind the cursor" (pruned_recoverable).
    Resume events (task_id containing "resume") with queue_byte_start=0
    indicate cursor resets, which are noted but do not affect the
    provenance chain.

    Args:
        ledger_path: Path to the queue_ledger.jsonl file.
        session_id: Unique session identifier for artifact/chamber IDs.
        detect_cursor_advancement: If True, register cursor advancement
                                    events when tasks complete.

    Returns:
        A sealed forge chamber dict containing all registered artifacts.

    Raises:
        FileNotFoundError: If ledger file does not exist.
        ValueError: If ledger contains malformed data.
    """
    events = parse_ledger_events(ledger_path)
    task_groups = group_events_by_task(events)

    adapter = OpenClawAdapter(session_id)

    completed_task_artifacts: list[str] = []

    try:
        for group in task_groups:
            task_id = group["task_id"]
            task_events = group["events"]

            # Find task.start and task.done events for output synthesis
            start_event = None
            done_event = None
            patch_events: list[dict] = []

            for event in task_events:
                if event["kind"] == "task.start":
                    start_event = event
                elif event["kind"] == "task.done":
                    done_event = event
                elif event["kind"].startswith("patch."):
                    patch_events.append(event)

            # Build output from task events
            detail = ""
            meta = None
            ok = group.get("ok")

            if start_event:
                detail = start_event.get("detail", "")
                meta = start_event.get("meta")

            # Synthesize output text from the task lifecycle
            output_parts = []
            if start_event:
                output_parts.append(f"task.start: {start_event.get('detail', '')}")
            for pe in patch_events:
                output_parts.append(f"{pe['kind']}: {pe.get('detail', '')}")
            if done_event:
                ok_str = "ok" if done_event.get("ok") else "failed"
                output_parts.append(f"task.done: {ok_str}")
                if done_event.get("detail"):
                    output_parts.append(f"detail: {done_event['detail']}")

            output = " | ".join(output_parts) if output_parts else None

            # Register the task
            task_art_id = adapter.register_task(
                task_id,
                output=output,
                ok=ok,
                detail=detail,
                meta=meta,
            )

            # Register patch events as child artifacts
            for pe in patch_events:
                adapter.register_patch(
                    pe.get("task_id", task_id),
                    pe["kind"],
                    parent_task_artifact=task_art_id,
                    detail=pe.get("detail", ""),
                    meta=pe.get("meta"),
                )

            # Track completed tasks for cursor advancement detection
            if group.get("completed") and group.get("ok"):
                completed_task_artifacts.append(task_art_id)

        # Register cursor advancement if tasks completed
        if detect_cursor_advancement and completed_task_artifacts:
            adapter.register_cursor_advancement(
                task_ids_behind_cursor=completed_task_artifacts,
            )

    except Exception as e:
        adapter.finalize_on_error(e)
        raise

    return adapter.finalize()


# --- Metric computation (reused from primordial_rlm_bridge.py) ---
#
# The metric functions (compute_reversibility_score, compute_overhead,
# compute_provenance_depth) in primordial_rlm_bridge.py are RLM-agnostic.
# However, importing that module at the top level triggers
# `from rlm.core.rlm import RLM` which fails when the rlm package is not
# installed. We use importlib.util to load only the module spec and source,
# then selectively import the metric functions into a clean namespace that
# has forge tool imports but not the RLM import.


def _load_bridge_metrics() -> dict:
    """Load metric functions from primordial_rlm_bridge.py without RLM.

    Reads the bridge module source, strips the RLM import lines and the
    PrimordialRLM class definition, then compiles and runs only the
    standalone metric function definitions in a namespace with forge imports.
    """
    import ast
    import types
    from pathlib import Path

    bridge_path = Path(__file__).parent / "primordial_rlm_bridge.py"
    source = bridge_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Identify which top-level nodes are safe to execute (not RLM imports,
    # not the PrimordialRLM class)
    metric_fn_names = {
        "compute_reversibility_score",
        "compute_overhead",
        "compute_provenance_depth",
        "compute_vanilla_reversibility",
        "run_primordial_analysis",
    }
    safe_nodes = []
    for node in tree.body:
        # Keep: from __future__ import annotations
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            safe_nodes.append(node)
        # Keep: import json, import sys, import time, etc.
        elif isinstance(node, ast.Import):
            safe_nodes.append(node)
        # Keep: forge tool imports (from forge_*)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("forge_"):
            safe_nodes.append(node)
        # Keep: metric function defs
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in metric_fn_names:
                safe_nodes.append(node)

    # Build a new module with only the safe nodes
    new_tree = ast.Module(body=safe_nodes, type_ignores=[])
    ast.fix_missing_locations(new_tree)

    code = compile(new_tree, str(bridge_path), "exec")
    ns: dict = {"__builtins__": __builtins__, "__name__": "primordial_rlm_bridge_metrics"}

    # Python needs __future__ annotations active for the compiled code.
    # The compiled module already has `from __future__ import annotations` as its
    # first statement, so this is handled.
    _run_code_obj(code, ns)

    return ns


def _run_code_obj(code, ns):
    """Run a compiled code object in a namespace. Separated for clarity."""
    # This is safe: we compiled the code ourselves from a known source file
    # (primordial_rlm_bridge.py) after stripping all non-metric code.
    # No user input is involved.
    function_runner = type(lambda: None)  # noqa: E731
    fn = function_runner(code, ns)
    fn()


# Module-level cache
_bridge_ns: dict | None = None


def _get_bridge_ns() -> dict:
    """Get (cached) namespace with bridge metric functions."""
    global _bridge_ns
    if _bridge_ns is None:
        _bridge_ns = _load_bridge_metrics()
    return _bridge_ns


def compute_reversibility_score(chamber: dict) -> float:
    """Fraction of artifacts with valid provenance chain to root.

    Delegates to compute_reversibility_score() from primordial_rlm_bridge.py.
    """
    return _get_bridge_ns()["compute_reversibility_score"](chamber)


def compute_overhead(trace: dict, vanilla_payload_size: int = 0) -> dict:
    """Overhead analysis comparing Primordial trace to vanilla logger.

    Delegates to compute_overhead() from primordial_rlm_bridge.py.
    """
    return _get_bridge_ns()["compute_overhead"](trace, vanilla_payload_size)


def compute_provenance_depth(chamber: dict) -> dict:
    """Compute max provenance chain depth and verify all chains reach root.

    Delegates to compute_provenance_depth() from primordial_rlm_bridge.py.
    """
    return _get_bridge_ns()["compute_provenance_depth"](chamber)


def run_openclaw_analysis(
    chamber: dict,
    vanilla_payload_size: int = 0,
) -> dict:
    """Run full forge analysis on a chamber produced by the OpenClaw adapter.

    Analogous to run_primordial_analysis() in primordial_rlm_bridge.py but
    for OpenClaw-produced chambers.

    Args:
        chamber: A sealed forge chamber from the OpenClaw adapter.
        vanilla_payload_size: Size in bytes of vanilla (uninstrumented) output
                               for overhead comparison.

    Returns:
        Analysis dict with validation errors, trace verification, and metrics.
    """
    validation_errors = validate_chamber(chamber)

    trace = encode_trace(chamber)
    verification = verify_trace(trace, chamber)

    reversibility = compute_reversibility_score(chamber)
    provenance = compute_provenance_depth(chamber)
    overhead = compute_overhead(trace, vanilla_payload_size)

    return {
        "validation_errors": len(validation_errors),
        "validation_details": validation_errors,
        "trace_verified": verification["valid"],
        "hash_match": verification["hash_match"],
        "content_match": verification["content_match"],
        "reversibility_score": reversibility,
        "provenance": provenance,
        "overhead": overhead,
        "stage_count": len(chamber.get("stages", [])),
    }
