"""
primordial_rlm_bridge.py — Bridge between Primordial Computing and RLM.

Subclasses RLM to wrap each iteration, subcall, and compaction event
as Primordial chamber artifacts with typed absence, provenance refs,
and hash-verified trace compression. Does NOT modify RLM or forge source.
"""

from __future__ import annotations

import sys
import time
from typing import Any

# Ensure forge tools are importable
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from forge_chamber import (
    ForgeChamberError,
    create_chamber,
    register_stage,
    seal_chamber,
    validate_chamber,
)
from forge_nulls import AbsenceState, ForgeNullError
from forge_reversible_summary import ForgeRefError, create_summary_view
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import decode_trace, encode_trace, trace_stats, verify_trace

# RLM imports
from rlm.core.rlm import RLM
from rlm.core.types import RLMChatCompletion, RLMIteration
from rlm.logger import RLMLogger


class PrimordialRLM(RLM):
    """RLM subclass that wraps execution with Primordial chamber instrumentation.

    Each completion() creates a chamber. Each _completion_turn() registers
    an artifact. Subcalls register child artifacts with parent refs.
    Compactions create SummaryViews with source_refs to compacted iterations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chamber: dict | None = None
        self._iteration_artifacts: list[str] = []
        self._current_iteration_subcalls: list[str] = []
        self._subcall_counter: int = 0
        self._compaction_count: int = 0
        self._run_id: str = ""

    def completion(
        self, prompt: str | dict[str, Any], root_prompt: str | None = None
    ) -> RLMChatCompletion:
        self._run_id = f"run{int(time.time() * 1000) % 100000}"
        self._chamber = create_chamber(f"chamber:rlm:{self._run_id}:v1")
        self._iteration_artifacts = []
        self._subcall_counter = 0
        self._compaction_count = 0

        try:
            result = super().completion(prompt, root_prompt)
        except Exception:
            if self._chamber and self._chamber["status"] == "open":
                seal_chamber(self._chamber)
            raise

        if self._chamber["status"] == "open":
            seal_chamber(self._chamber)
        return result

    def _completion_turn(
        self,
        prompt: str | dict[str, Any],
        lm_handler: Any,
        environment: Any,
    ) -> RLMIteration:
        self._current_iteration_subcalls = []

        iteration = super()._completion_turn(prompt, lm_handler, environment)

        iter_idx = len(self._iteration_artifacts)
        stage_id = f"artifact:rlm:{self._run_id}:iter:{iter_idx}:r1"

        # Build source refs: previous iteration + any subcalls during this iteration
        source_refs: list[str] = []
        if self._iteration_artifacts:
            source_refs.append(self._iteration_artifacts[-1])
        source_refs.extend(self._current_iteration_subcalls)

        output = iteration.response if iteration.response else None
        output_state = AbsenceState.NOT_GENERATED if output is None else None

        artifact = create_v1_stage_artifact(
            stage_id=stage_id,
            seat="rlm-engine",
            producer_name="rlm-completion-turn",
            producer_role="engine",
            output=output,
            output_state=output_state,
            source_refs=source_refs if source_refs else None,
        )

        summary_text = f"Iteration {iter_idx}: "
        if iteration.code_blocks:
            summary_text += f"{len(iteration.code_blocks)} code block(s). "
        if self._current_iteration_subcalls:
            summary_text += f"{len(self._current_iteration_subcalls)} subcall(s). "
        if iteration.final_answer:
            summary_text += "Final answer produced."
        else:
            summary_text += "No final answer."

        summary = create_v1_stage_summary(
            artifact, summary_text,
            extra_source_refs=source_refs if source_refs else None,
        )

        register_stage(self._chamber, artifact, summary)
        self._iteration_artifacts.append(stage_id)

        return iteration

    def _subcall(self, prompt: str, model: str | None = None) -> RLMChatCompletion:
        parent_ref = self._iteration_artifacts[-1] if self._iteration_artifacts else None
        subcall_idx = self._subcall_counter
        self._subcall_counter += 1

        result = super()._subcall(prompt, model)

        subcall_id = f"artifact:rlm:{self._run_id}:subcall:{subcall_idx}:r1"
        source_refs = [parent_ref] if parent_ref else None

        output = result.response if result.response else None
        output_state = AbsenceState.NOT_GENERATED if output is None else None

        artifact = create_v1_stage_artifact(
            stage_id=subcall_id,
            seat="rlm-subcall",
            producer_name="rlm-subcall",
            producer_role="subcall",
            output=output,
            output_state=output_state,
            source_refs=source_refs,
        )
        summary = create_v1_stage_summary(
            artifact,
            f"Subcall {subcall_idx}: model={model or 'default'}, "
            f"response_len={len(output) if output else 0}",
            extra_source_refs=source_refs,
        )
        register_stage(self._chamber, artifact, summary)
        self._current_iteration_subcalls.append(subcall_id)

        return result

    def _compact_history(
        self,
        lm_handler: Any,
        environment: Any,
        message_history: list[dict[str, Any]],
        compaction_count: int = 1,
    ) -> list[dict[str, Any]]:
        compacted_refs = list(self._iteration_artifacts)

        new_history = super()._compact_history(
            lm_handler, environment, message_history, compaction_count
        )

        self._compaction_count += 1
        compact_art_id = (
            f"artifact:rlm:{self._run_id}:compact:{self._compaction_count}:r1"
        )

        # Extract summary text from the LM's compaction summary
        summary_text = "Compaction summary"
        if len(new_history) > 2 and isinstance(new_history[2], dict):
            summary_text = new_history[2].get("content", summary_text)

        # Register compaction as an artifact
        artifact = create_v1_stage_artifact(
            stage_id=compact_art_id,
            seat="rlm-compactor",
            producer_name="rlm-compact-history",
            producer_role="compactor",
            output=summary_text,
            source_refs=compacted_refs if compacted_refs else None,
        )
        summary = create_v1_stage_summary(
            artifact,
            f"Compaction #{self._compaction_count}: "
            f"summarized {len(compacted_refs)} iteration(s)",
            extra_source_refs=compacted_refs if compacted_refs else None,
        )
        register_stage(self._chamber, artifact, summary)

        return new_history

    @property
    def chamber(self) -> dict | None:
        return self._chamber


# --- Metric Computation ---


def compute_reversibility_score(chamber: dict) -> float:
    """H1: Fraction of artifacts with valid provenance chain to root.

    An artifact has valid provenance if it either:
    - Has no refs (root artifact, iteration 0)
    - All its resolved refs point to artifacts in the chamber
    """
    stages = chamber.get("stages", [])
    if not stages:
        return 1.0

    index = chamber.get("artifact_index", set())
    if isinstance(index, list):
        index = set(index)

    valid = 0
    total = len(stages)

    for stage in stages:
        artifact = stage.get("artifact", {})
        refs = artifact.get("refs", [])
        all_resolved = True
        for ref_entry in refs:
            if isinstance(ref_entry, dict) and ref_entry.get("state") == "resolved":
                if ref_entry.get("ref") not in index:
                    all_resolved = False
                    break
        if all_resolved:
            valid += 1

    return valid / total if total > 0 else 1.0


def compute_provenance_depth(chamber: dict) -> dict:
    """Compute max provenance chain depth and verify all chains reach root."""
    stages = chamber.get("stages", [])
    if not stages:
        return {"max_depth": 0, "all_reach_root": True}

    # Build ref graph: artifact_id -> set of referenced artifact_ids
    ref_graph: dict[str, set[str]] = {}
    stage_ids = set()
    for stage in stages:
        art = stage.get("artifact", {})
        art_id = art.get("id", "")
        stage_ids.add(art_id)
        refs = set()
        for ref_entry in art.get("refs", []):
            if isinstance(ref_entry, dict) and ref_entry.get("state") == "resolved":
                refs.add(ref_entry["ref"])
        ref_graph[art_id] = refs

    # Find roots (artifacts with no refs to other stage artifacts)
    roots = set()
    for art_id, refs in ref_graph.items():
        if not refs.intersection(stage_ids):
            roots.add(art_id)

    # BFS depth from each artifact
    max_depth = 0

    def chain_depth(art_id: str, visited: set) -> int:
        if art_id in visited:
            return 0
        visited.add(art_id)
        refs = ref_graph.get(art_id, set()).intersection(stage_ids)
        if not refs:
            return 0
        return 1 + max(chain_depth(r, visited) for r in refs)

    for art_id in stage_ids:
        d = chain_depth(art_id, set())
        max_depth = max(max_depth, d)

    # Check all reach root
    def reaches_root(art_id: str, visited: set) -> bool:
        if art_id in roots:
            return True
        if art_id in visited:
            return False
        visited.add(art_id)
        refs = ref_graph.get(art_id, set()).intersection(stage_ids)
        return any(reaches_root(r, set(visited)) for r in refs)

    all_reach = all(reaches_root(sid, set()) for sid in stage_ids)

    return {"max_depth": max_depth, "all_reach_root": all_reach}


def compute_overhead(trace: dict, vanilla_payload_size: int = 0) -> dict:
    """H3: Overhead analysis comparing Primordial trace to vanilla logger.

    Two overhead metrics:
    1. absolute_overhead_pct: Primordial metadata vs raw content (output text)
    2. vs_vanilla_pct: How much larger Primordial trace is compared to vanilla
       logger payload for the same data. This is the meaningful comparison.
    """
    import json as _json

    stats = trace_stats(trace)
    encoded_json = _json.dumps(
        {"shared": trace.get("shared", {}), "stages": trace.get("stages", [])},
        sort_keys=True,
    )
    primordial_bytes = len(encoded_json.encode("utf-8"))

    # Content bytes: sum of output text in decoded stages
    decoded = decode_trace(trace)
    content_bytes = 0
    for stage in decoded:
        art = stage.get("artifact", {})
        output = art.get("output")
        if isinstance(output, str):
            content_bytes += len(output.encode("utf-8"))

    # Absolute overhead (Primordial metadata vs raw content)
    abs_metadata = primordial_bytes - content_bytes
    abs_overhead_pct = (abs_metadata / content_bytes * 100) if content_bytes > 0 else 0

    # Vs-vanilla overhead (the meaningful metric)
    vs_vanilla_pct = 0.0
    if vanilla_payload_size > 0:
        extra = primordial_bytes - vanilla_payload_size
        vs_vanilla_pct = (extra / vanilla_payload_size * 100)

    return {
        "compression_ratio": stats["compression_ratio"],
        "original_size": stats["original_size"],
        "encoded_size": stats["encoded_size"],
        "primordial_bytes": primordial_bytes,
        "vanilla_bytes": vanilla_payload_size,
        "content_bytes": content_bytes,
        "absolute_overhead_pct": round(abs_overhead_pct, 2),
        "vs_vanilla_pct": round(vs_vanilla_pct, 2),
        "shared_structures": stats["shared_structures"],
        "ref_replacements": stats["ref_replacements"],
    }


def compute_vanilla_reversibility(trajectory: dict | None) -> float:
    """Compute reversibility for vanilla RLM logger output.

    The logger stores a flat list of iterations. There are no refs,
    no DAG structure, no provenance chains. We check if any iteration
    has structural links to others (expected: none).
    """
    if trajectory is None:
        return 0.0

    iterations = trajectory.get("iterations", [])
    if not iterations:
        return 0.0

    # Check for any provenance information
    has_provenance = 0
    for it in iterations:
        # Check if iteration has any reference to other iterations
        # (RLM logger doesn't store refs, so this should always be 0)
        if "source_refs" in it or "refs" in it or "parent_id" in it:
            has_provenance += 1

    # Score: fraction with provenance. Expected: 0.0
    return has_provenance / len(iterations) if iterations else 0.0


def run_primordial_analysis(
    chamber: dict, vanilla_payload_size: int = 0
) -> dict:
    """Run full Primordial analysis on a completed chamber."""
    # Validate chamber
    validation_errors = validate_chamber(chamber)

    # Encode trace
    trace = encode_trace(chamber)

    # Verify round-trip
    verification = verify_trace(trace, chamber)

    # Metrics
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
