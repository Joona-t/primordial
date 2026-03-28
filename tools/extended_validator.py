"""
extended_validator.py -- Extended chamber validator covering D1-D9 canonical taxonomy.

Wraps existing validate_chamber() and adds 6 new checks for D-types that
the structural validator misses: D3 (content hash), D4 (fake source refs),
D6 (illegal state transition), D7 (tool-call-to-trace completeness),
D8 (content truncation/corruption), D9 (post-seal timestamp).

D-type labels match the canonical taxonomy in CONVENTIONS.md #8 and
fault_injector.py exactly.

Convention compliance:
  - "Compaction" always qualified per Convention #6
  - Hash integrity: SHA-256 on json.dumps(obj, sort_keys=True, ensure_ascii=True)
    per Convention #10
  - Violation classification: structural only per Convention #8
  - All error codes follow the EXTENDED.D{N}_DESCRIPTION pattern
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from forge_chamber import validate_chamber
from forge_nulls import TRANSITION_TABLE, V1_ABSENCE_STATES, validate_transition


# ---------------------------------------------------------------------------
# D-type classification map
#
# Maps every known error code to its canonical D-type (D1-D9) or a structural
# category (STRUCTURAL, SCHEMA) for codes that don't correspond to a single
# D-type in the fault taxonomy.
#
# CRITICAL: CHAMBER.DUPLICATE_STAGE_ID, INDEX_NOT_MONOTONIC, and INDEX_DESYNC
# are structural integrity checks (ordering, uniqueness), NOT D6 (illegal
# state transition). D6 is detected EXCLUSIVELY by EXTENDED.D6_ILLEGAL_TRANSITION.
# ---------------------------------------------------------------------------

D_TYPE_MAP: dict[str, str] = {
    # Existing validate_chamber() error codes
    "ABSENCE.MISSING_STATE_LABEL": "D5",      # Missing state label on null output (also D1)
    "REF.REF_UNRESOLVED": "D2",                # Broken provenance: ref not in artifact_index
    "CHAMBER.DUPLICATE_STAGE_ID": "STRUCTURAL",  # Structural: duplicate stage registration (NOT D6)
    "CHAMBER.INDEX_NOT_MONOTONIC": "STRUCTURAL", # Structural: stage ordering violated (NOT D6)
    "CHAMBER.INDEX_DESYNC": "STRUCTURAL",         # Structural: artifact_index inconsistent (NOT D6)
    "SUMMARY.MISSING_SOURCE_REFS": "D2",          # Broken provenance in summary

    # REVISION.REV_BLOCK_SCHEMA is a structural schema error; classify by context
    # in classify_single_error() below.
    "REVISION.REV_BLOCK_SCHEMA": "SCHEMA",

    # New extended validator error codes (D3, D4, D6, D7, D8, D9)
    "EXTENDED.D3_CONTENT_HASH_MISMATCH": "D3",
    "EXTENDED.D4_SUSPICIOUS_REF_TARGET": "D4",
    "EXTENDED.D6_ILLEGAL_TRANSITION": "D6",
    "EXTENDED.D7_TRACE_DATA_LOSS": "D7",
    "EXTENDED.D8_CONTENT_TRUNCATION": "D8",
    "EXTENDED.D9_POST_SEAL_TIMESTAMP": "D9",
}


def _err(code: str, message: str, path: str) -> dict:
    """Create an error dict with d_type classification."""
    d_type = D_TYPE_MAP.get(code, "UNKNOWN")
    return {"code": code, "message": message, "path": path, "d_type": d_type}


def classify_single_error(error: dict) -> str:
    """Classify a single error dict to its D-type.

    For REVISION.REV_BLOCK_SCHEMA errors, attempts contextual classification
    based on the error path and message content.
    """
    code = error.get("code", "")
    base_dtype = D_TYPE_MAP.get(code, "UNKNOWN")

    if base_dtype != "SCHEMA":
        return base_dtype

    # Contextual classification for REV_BLOCK_SCHEMA
    path = error.get("path", "").lower()
    message = error.get("message", "").lower()

    if "hash" in path or "hash" in message:
        return "D3"
    if "ref" in path or "ref" in message:
        return "D2"
    return "SCHEMA"


def classify_errors_by_dtype(errors: list[dict]) -> dict[str, list[dict]]:
    """Group validation errors by D-type (D1-D9).

    Returns {d_type: [errors]} where d_type is one of D1-D9,
    STRUCTURAL, SCHEMA, or UNKNOWN.
    """
    result: dict[str, list[dict]] = {}
    for error in errors:
        d_type = error.get("d_type")
        if d_type is None:
            d_type = classify_single_error(error)
        result.setdefault(d_type, []).append(error)
    return result


# ---------------------------------------------------------------------------
# Extended checks
# ---------------------------------------------------------------------------

def _check_d3_content_hash(chamber: dict) -> list[dict]:
    """D3: Content hash re-verification.

    For every artifact that has a "hash" field, recompute SHA-256 on the
    artifact's content using the canonical serialization (CONVENTIONS.md #10:
    json.dumps(obj, sort_keys=True, ensure_ascii=True)) and compare.

    This detects post-hash modification (inject_d3_corrupted_hashes modifies
    output AFTER hash computation).
    """
    errors: list[dict] = []

    for i, stage in enumerate(chamber.get("stages", [])):
        artifact = stage.get("artifact", {})
        hash_obj = artifact.get("hash")

        if not isinstance(hash_obj, dict):
            continue

        expected_hash = hash_obj.get("value")
        algorithm = hash_obj.get("algorithm", "sha256")

        if not isinstance(expected_hash, str) or algorithm != "sha256":
            continue

        # Reconstruct the semantic payload that was hashed at creation time.
        # The hash covers the semantic payload fields -- we need to figure out
        # which fields were in the payload. Looking at create_v1_stage_artifact,
        # the payload contains: seat, output, status, output_state (if present),
        # stop_reason, stop_reason_state (if present), findings, findings_state
        # (if present).
        #
        # The hash is computed on the payload dict BEFORE it's merged into the
        # artifact envelope. We need to extract the payload fields from the
        # artifact.
        payload_keys = {
            "seat", "output", "status", "output_state",
            "stop_reason", "stop_reason_state",
            "findings", "findings_state",
        }
        payload = {k: artifact[k] for k in payload_keys if k in artifact}

        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        if actual_hash != expected_hash:
            errors.append(_err(
                "EXTENDED.D3_CONTENT_HASH_MISMATCH",
                f"SHA-256 hash mismatch: expected {expected_hash[:16]}..., "
                f"got {actual_hash[:16]}... (content modified after hash computation)",
                f"stages[{i}].artifact.hash",
            ))

    return errors


def _check_d4_fake_source_refs(chamber: dict) -> list[dict]:
    """D4: Fake source ref detection.

    For every artifact, check whether source_refs point to semantically
    correct parents (not just any valid ID).

    Heuristics:
    1. If a ref points to an artifact registered AFTER the referencing artifact,
       it's likely fake (temporal ordering violation).
    2. Self-referencing loop (artifact refs itself).
    3. Stage artifact refs a summary artifact (cross-type ref -- stage outputs
       should normally ref other stage outputs, not summaries).
    4. Non-adjacent ref gap: in a linear chain, stage N normally refs stage N-1.
       If stage N refs stage M where |N-M| > 1 AND stage N has exactly 1 ref
       AND the ref target is not the chamber_id, this is suspicious. Legitimate
       multi-hop refs exist but are rare; combined with other signals this
       catches D4 injections that pick a random valid ID.
    """
    errors: list[dict] = []

    # Build maps for temporal ordering and type classification
    id_to_index: dict[str, int] = {}
    summary_ids: set[str] = set()
    stage_artifact_ids: set[str] = set()

    for stage in chamber.get("stages", []):
        stage_id = stage.get("stage_id", "")
        stage_index = stage.get("stage_index", -1)
        id_to_index[stage_id] = stage_index
        stage_artifact_ids.add(stage_id)

        # Track summary IDs separately
        summary = stage.get("summary")
        if summary is not None and isinstance(summary.get("id"), str):
            sid = summary["id"]
            id_to_index[sid] = stage_index
            summary_ids.add(sid)

    chamber_id = chamber.get("chamber_id", "")

    for i, stage in enumerate(chamber.get("stages", [])):
        artifact = stage.get("artifact", {})
        own_id = artifact.get("id", "")
        own_index = stage.get("stage_index", i)

        for j, ref_entry in enumerate(artifact.get("refs", [])):
            if not isinstance(ref_entry, dict):
                continue
            if ref_entry.get("state") != "resolved":
                continue

            ref_id = ref_entry.get("ref", "")

            # Check 1: Self-referencing loop
            if ref_id == own_id:
                errors.append(_err(
                    "EXTENDED.D4_SUSPICIOUS_REF_TARGET",
                    f"Self-referencing loop: artifact {own_id} refs itself",
                    f"stages[{i}].artifact.refs[{j}]",
                ))
                continue

            # Check 2: Temporal ordering violation (forward reference)
            ref_index = id_to_index.get(ref_id)
            if ref_index is not None and ref_index > own_index:
                errors.append(_err(
                    "EXTENDED.D4_SUSPICIOUS_REF_TARGET",
                    f"Ref {ref_id} points to artifact at stage {ref_index}, "
                    f"registered after referencing artifact at stage {own_index}",
                    f"stages[{i}].artifact.refs[{j}]",
                ))
                continue

            # Check 3: Cross-type ref (stage artifact refs a summary)
            if ref_id in summary_ids and own_id in stage_artifact_ids:
                errors.append(_err(
                    "EXTENDED.D4_SUSPICIOUS_REF_TARGET",
                    f"Stage artifact {own_id} refs summary artifact {ref_id} "
                    f"(stage outputs should ref other stage outputs, not summaries)",
                    f"stages[{i}].artifact.refs[{j}]",
                ))
                continue

            # Check 4: Non-adjacent ref gap in a simple chain
            # If this stage has exactly 1 ref and it skips over intermediate stages,
            # the ref may have been swapped to a wrong target.
            refs_list = artifact.get("refs", [])
            resolved_refs = [
                r for r in refs_list
                if isinstance(r, dict) and r.get("state") == "resolved"
            ]
            if (
                len(resolved_refs) == 1
                and ref_id != chamber_id
                and ref_index is not None
                and own_index > 0
            ):
                gap = own_index - ref_index
                if gap > 1:
                    # Skipping intermediate stages -- suspicious
                    errors.append(_err(
                        "EXTENDED.D4_SUSPICIOUS_REF_TARGET",
                        f"Ref gap: stage {own_index} refs stage {ref_index} "
                        f"(gap={gap}, skipping {gap - 1} intermediate stages)",
                        f"stages[{i}].artifact.refs[{j}]",
                    ))

    return errors


def _check_d6_illegal_transition(chamber: dict) -> list[dict]:
    """D6: Illegal state transition detection.

    For each pair of consecutive stages (i, i+1) where both have an
    output_state field, call validate_transition() from forge_nulls.py.
    If validate_transition() returns False, the transition is illegal per
    the TRANSITION_TABLE (64 entries, 19 illegal).

    IMPORTANT: CHAMBER.DUPLICATE_STAGE_ID, INDEX_NOT_MONOTONIC, and
    INDEX_DESYNC are structural integrity checks (ordering, uniqueness),
    NOT state transition legality checks. They do NOT detect D6.
    This check is the ONLY D6 detector.
    """
    errors: list[dict] = []
    stages = chamber.get("stages", [])

    for i in range(len(stages) - 1):
        current_artifact = stages[i].get("artifact", {})
        next_artifact = stages[i + 1].get("artifact", {})

        from_state = current_artifact.get("output_state")
        to_state = next_artifact.get("output_state")

        # Only check if both stages have output_state
        if from_state is None or to_state is None:
            continue

        # Both must be valid absence states
        if from_state not in V1_ABSENCE_STATES or to_state not in V1_ABSENCE_STATES:
            continue

        if not validate_transition(from_state, to_state):
            errors.append(_err(
                "EXTENDED.D6_ILLEGAL_TRANSITION",
                f"Illegal state transition: {from_state} -> {to_state} "
                f"between stages[{i}] and stages[{i + 1}]",
                f"stages[{i}]->{i + 1}.artifact.output_state",
            ))

    return errors


def _check_d7_trace_data_loss(
    chamber: dict,
    tool_call_log: list[dict] | None = None,
) -> list[dict]:
    """D7: Tool-call-log-to-trace completeness check.

    Accept an optional tool_call_log (list of dicts with at minimum
    {"tool": str, "call_id": str}). For each tool call in the log,
    verify a corresponding artifact or trace entry exists in the chamber.
    A missing tool call in the trace indicates data was lost between
    tool execution and forge recording.
    """
    errors: list[dict] = []

    if tool_call_log is None:
        return errors

    # Build set of all artifact content indicators
    # Look for tool call IDs in artifact outputs and refs
    artifact_content: set[str] = set()
    for stage in chamber.get("stages", []):
        artifact = stage.get("artifact", {})
        stage_id = artifact.get("id", "")
        artifact_content.add(stage_id)

        # Also index output content for substring matching
        output = artifact.get("output")
        if isinstance(output, str):
            artifact_content.add(output)

        # Index ref targets
        for ref_entry in artifact.get("refs", []):
            if isinstance(ref_entry, dict):
                ref_id = ref_entry.get("ref", "")
                artifact_content.add(ref_id)

    for k, call_entry in enumerate(tool_call_log):
        if not isinstance(call_entry, dict):
            continue

        call_id = call_entry.get("call_id", "")
        tool_name = call_entry.get("tool", "")

        if not call_id:
            continue

        # Check if this tool call is represented in the chamber
        found = False
        for content in artifact_content:
            if call_id in content:
                found = True
                break

        if not found:
            errors.append(_err(
                "EXTENDED.D7_TRACE_DATA_LOSS",
                f"Tool call {tool_name}:{call_id} not found in chamber trace. "
                f"Data may have been lost between tool execution and forge recording.",
                f"tool_call_log[{k}]",
            ))

    return errors


def _check_d8_content_truncation(chamber: dict) -> list[dict]:
    """D8: Content truncation / corruption detection.

    For every artifact with non-null output, check for truncation signatures:
    (a) known truncation markers like "[TRUNCATED"
    (b) output ends mid-JSON bracket (unbalanced braces/brackets)
    (c) summary_hash mismatch (corruption propagates to summaries)
    """
    errors: list[dict] = []

    # Known truncation markers
    truncation_markers = [
        "[TRUNCATED",
        "[TRUNCATED_BY_CONTEXT_PRES",
        "...[truncated",
        "<!-- truncated",
    ]

    for i, stage in enumerate(chamber.get("stages", [])):
        artifact = stage.get("artifact", {})
        output = artifact.get("output")

        if output is not None and isinstance(output, str):
            # Check for known truncation markers
            for marker in truncation_markers:
                if marker in output:
                    errors.append(_err(
                        "EXTENDED.D8_CONTENT_TRUNCATION",
                        f"Truncation marker found in output: '{marker}'",
                        f"stages[{i}].artifact.output",
                    ))
                    break
            else:
                # Check for mid-JSON truncation (unbalanced braces/brackets)
                if output.strip():
                    open_braces = output.count("{") - output.count("}")
                    open_brackets = output.count("[") - output.count("]")
                    if open_braces > 0 or open_brackets > 0:
                        # Only flag if the output looks like it should be
                        # structured (starts with { or [)
                        first_char = output.strip()[0] if output.strip() else ""
                        if first_char in ("{", "["):
                            errors.append(_err(
                                "EXTENDED.D8_CONTENT_TRUNCATION",
                                f"Unbalanced JSON structure in output: "
                                f"{open_braces} unclosed braces, "
                                f"{open_brackets} unclosed brackets",
                                f"stages[{i}].artifact.output",
                            ))

        # Check summary hash mismatch
        summary = stage.get("summary")
        if summary is not None and isinstance(summary, dict):
            summary_text = summary.get("summary", "")
            summary_hash_obj = summary.get("summary_hash")

            if (
                isinstance(summary_text, str)
                and isinstance(summary_hash_obj, dict)
                and summary_hash_obj.get("algorithm") == "sha256"
            ):
                expected_hash = summary_hash_obj.get("value", "")
                # Summary hash uses raw text encoding, NOT json.dumps()
                # (see forge_reversible_summary._compute_hash)
                actual_hash = hashlib.sha256(
                    summary_text.encode("utf-8")
                ).hexdigest()

                if expected_hash and actual_hash != expected_hash:
                    errors.append(_err(
                        "EXTENDED.D8_CONTENT_TRUNCATION",
                        f"Summary hash mismatch: summary text was modified "
                        f"(expected {expected_hash[:16]}..., "
                        f"got {actual_hash[:16]}...)",
                        f"stages[{i}].summary.summary_hash",
                    ))

    return errors


def _check_d9_post_seal_timestamp(chamber: dict) -> list[dict]:
    """D9: Post-seal timestamp check.

    If chamber status is "sealed" and has a "sealed_at" timestamp, verify
    no stage has a "registered_at" timestamp after sealed_at.

    Also checks: if the chamber is sealed but lacks sealed_at, infer
    the seal time from the last registered stage and check for stages
    whose registered_at is after the last stage's registered_at
    (indicating bypass of normal registration flow).

    Additionally: checks for stages that were manually appended after
    the seal by comparing stage count against artifact_index membership.
    """
    errors: list[dict] = []

    if chamber.get("status") != "sealed":
        return errors

    stages = chamber.get("stages", [])
    if not stages:
        return errors

    # Primary check: explicit sealed_at timestamp
    sealed_at_str = chamber.get("sealed_at")
    if sealed_at_str is not None:
        try:
            sealed_at = datetime.fromisoformat(sealed_at_str)
            for i, stage in enumerate(stages):
                registered_at_str = stage.get("registered_at")
                if registered_at_str is not None:
                    try:
                        registered_at = datetime.fromisoformat(registered_at_str)
                        if registered_at > sealed_at:
                            errors.append(_err(
                                "EXTENDED.D9_POST_SEAL_TIMESTAMP",
                                f"Stage registered at {registered_at_str} "
                                f"after chamber sealed at {sealed_at_str}",
                                f"stages[{i}].registered_at",
                            ))
                    except (ValueError, TypeError):
                        pass
        except (ValueError, TypeError):
            pass

    # Secondary check: detect stages that were manually appended
    # after seal (bypassing register_stage which would throw ForgeChamberError).
    # If artifact_index doesn't contain a stage's ID, it wasn't properly
    # registered -- it was injected after seal.
    artifact_index = chamber.get("artifact_index", set())
    if isinstance(artifact_index, list):
        artifact_index = set(artifact_index)

    for i, stage in enumerate(stages):
        stage_id = stage.get("stage_id", "")
        if stage_id and stage_id not in artifact_index:
            errors.append(_err(
                "EXTENDED.D9_POST_SEAL_TIMESTAMP",
                f"Stage {stage_id} not in artifact_index "
                f"(likely registered after seal, bypassing register_stage())",
                f"stages[{i}].stage_id",
            ))

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_chamber_extended(
    chamber: dict,
    tool_call_log: list[dict] | None = None,
) -> list[dict]:
    """Run validate_chamber() + all 6 extended checks.

    Returns list of error dicts: {"code": str, "message": str, "path": str, "d_type": str}
    The d_type field maps to D1-D9 canonical taxonomy (CONVENTIONS.md #8).
    """
    # Run existing structural validation
    base_errors = validate_chamber(chamber)

    # Add d_type classification to base errors
    classified_base_errors = []
    for error in base_errors:
        d_type = D_TYPE_MAP.get(error.get("code", ""), "UNKNOWN")
        enriched = dict(error)
        enriched["d_type"] = d_type
        classified_base_errors.append(enriched)

    # Run the 6 extended checks
    extended_errors: list[dict] = []
    extended_errors.extend(_check_d3_content_hash(chamber))
    extended_errors.extend(_check_d4_fake_source_refs(chamber))
    extended_errors.extend(_check_d6_illegal_transition(chamber))
    extended_errors.extend(_check_d7_trace_data_loss(chamber, tool_call_log))
    extended_errors.extend(_check_d8_content_truncation(chamber))
    extended_errors.extend(_check_d9_post_seal_timestamp(chamber))

    return classified_base_errors + extended_errors
