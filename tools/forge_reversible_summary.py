"""
forge_reversible_summary.py — Summaries that always retain recovery paths.

Key invariant: no summary can exist without source_refs pointing back
to the artifacts it was derived from. Ungrounded summaries are a
protocol violation.

v1 convergence: create_summary_view() emits full forge.internal.v1
SummaryView envelopes. The old create_summary() is kept as a
deprecated lightweight helper.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

PROTOCOL_ID = "forge.internal.v1"

# Pattern: "artifact:<seg1>:<seg2>[:<segN>]" per RFC-0001 section 3.1
_REF_PATTERN = re.compile(r"^artifact:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$")


class ForgeRefError(Exception):
    """Raised when a summary lacks valid source references."""


def _validate_ref(ref: str) -> str:
    """Validate a single source reference looks like an artifact ID."""
    if not isinstance(ref, str) or not ref.strip():
        raise ForgeRefError(f"Source ref must be a non-empty string, got: {ref!r}")
    if not _REF_PATTERN.match(ref):
        raise ForgeRefError(
            f"Source ref does not match artifact ID pattern "
            f"'artifact:<seg1>:<seg2>[:<segN>]': {ref!r}"
        )
    return ref


def _structured_ref(ref_id: str, state: str = "resolved") -> dict:
    """Build a v1 structured ref entry."""
    return {"ref": ref_id, "state": state}


def _compute_hash(text: str) -> dict:
    """Compute v1-compliant hash object for summary text."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"algorithm": "sha256", "value": digest}


# --- v1 canonical: SummaryView ---

def create_summary_view(
    summary_id: str,
    text: str,
    source_refs: list[str],
    view_of: str,
    *,
    assert_v1: bool = True,
) -> dict:
    """Create a full v1 SummaryView artifact envelope.

    Args:
        summary_id: Artifact ID for this summary.
        text: The summary text. Must be non-empty.
        source_refs: List of artifact IDs this summary is derived from. Must be non-empty.
        view_of: The primary artifact this summary is a view over.
        assert_v1: If True, run the bridge assertion against canonical validator.

    Returns:
        v1-compliant SummaryView dict.

    Raises:
        ForgeRefError: If source_refs is missing/empty or refs are invalid.
        ValueError: If text or summary_id is empty.
    """
    if not isinstance(summary_id, str) or not summary_id.strip():
        raise ValueError("summary_id must be a non-empty string")
    _validate_ref(summary_id)

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Summary text must be a non-empty string")

    if not isinstance(source_refs, list) or len(source_refs) == 0:
        raise ForgeRefError(
            "source_refs must be a non-empty list of artifact references"
        )

    _validate_ref(view_of)
    validated_refs = [_validate_ref(ref) for ref in source_refs]

    sv = {
        "id": summary_id,
        "type": "summary_view",
        "schema_version": PROTOCOL_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": text.strip(),
        "source_refs": [_structured_ref(ref) for ref in validated_refs],
        "view_of": view_of,
        "summary_hash": _compute_hash(text.strip()),
        "refs": [_structured_ref(view_of)],
    }

    if assert_v1:
        # Boundary assertion: tool egress must be v1 valid.
        from forge_v1_bridge import assert_summary_view_v1

        local_index = {summary_id, view_of, *validated_refs}
        try:
            assert_summary_view_v1(sv, artifact_index=local_index)
        except Exception as e:  # pragma: no cover - defensive bridge guard
            raise ForgeRefError(f"Generated summary view failed v1 validation: {e}") from e

    return sv


def validate_summary_view(obj: dict) -> dict:
    """Validate an existing v1 SummaryView object.

    Checks required fields, source_refs structure, and ref format.
    Returns the object unchanged if valid.
    """
    if not isinstance(obj, dict):
        raise ForgeRefError(f"Expected dict, got {type(obj).__name__}")

    required = ["id", "type", "schema_version", "summary", "source_refs", "view_of", "summary_hash"]
    for key in required:
        if key not in obj:
            raise ForgeRefError(f"SummaryView missing required field: '{key}'")

    if obj.get("type") != "summary_view":
        raise ForgeRefError(f"type must be 'summary_view', got {obj.get('type')!r}")

    if not isinstance(obj.get("summary"), str) or not obj["summary"].strip():
        raise ForgeRefError("summary must be a non-empty string")

    refs = obj.get("source_refs")
    if not isinstance(refs, list) or len(refs) == 0:
        raise ForgeRefError("source_refs must be a non-empty list")

    for ref_entry in refs:
        if isinstance(ref_entry, dict):
            _validate_ref(ref_entry.get("ref", ""))
        elif isinstance(ref_entry, str):
            # Ingress compatibility
            _validate_ref(ref_entry)
        else:
            raise ForgeRefError(f"Invalid source_ref entry: {ref_entry!r}")

    _validate_ref(obj["view_of"])

    return obj


def is_grounded(obj: dict) -> bool:
    """Check if a summary has valid source references."""
    try:
        if "type" in obj and obj.get("type") == "summary_view":
            validate_summary_view(obj)
        else:
            _validate_legacy_summary(obj)
        return True
    except (ForgeRefError, Exception):
        return False


# --- Deprecated: lightweight summary helper ---

def create_summary(text: str, source_refs: list[str]) -> dict:
    """Create a lightweight summary dict. DEPRECATED — use create_summary_view().

    Compatibility-only ingress/output helper kept for caller stability.
    Removal gate: explicit deprecation window plus confirmed zero external callers.
    """
    from forge_v1_bridge import record_legacy_usage

    ref_count = len(source_refs) if isinstance(source_refs, list) else "invalid"
    record_legacy_usage(
        "summary.create_summary",
        detail=f"source_refs={ref_count}",
        stacklevel=2,
    )
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Summary text must be a non-empty string")

    if not isinstance(source_refs, list) or len(source_refs) == 0:
        raise ForgeRefError(
            "source_refs must be a non-empty list of artifact references"
        )

    validated_refs = [_validate_ref(ref) for ref in source_refs]

    return {
        "summary": text.strip(),
        "source_refs": validated_refs,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _validate_legacy_summary(obj: dict) -> dict:
    """Validate an old-style lightweight summary."""
    if "summary" not in obj:
        raise ForgeRefError("Summary object missing 'summary' field")
    if not isinstance(obj.get("summary"), str) or not obj["summary"].strip():
        raise ForgeRefError("Summary 'summary' field must be a non-empty string")
    refs = obj.get("source_refs")
    if not isinstance(refs, list) or len(refs) == 0:
        raise ForgeRefError("Summary missing or empty 'source_refs'")
    return obj


def validate_summary(obj: dict) -> dict:
    """Validate a summary — dispatches to v1 or legacy based on shape."""
    if not isinstance(obj, dict):
        raise ForgeRefError(f"Expected dict, got {type(obj).__name__}")

    if obj.get("type") == "summary_view":
        return validate_summary_view(obj)
    return _validate_legacy_summary(obj)


if __name__ == "__main__":
    print("=== forge_reversible_summary.py — v1-Aligned Reversible Summaries ===\n")

    # 1. Create a v1 SummaryView
    print("1. Creating a v1 SummaryView:")
    sv = create_summary_view(
        summary_id="artifact:run52:summary:builder:v1",
        text="Builder proposes strict fail-closed JSON boundaries.",
        source_refs=[
            "artifact:run52:builder_output:r1",
            "artifact:run52:architect_plan:r1",
        ],
        view_of="artifact:run52:builder_output:r1",
    )
    for k, v in sv.items():
        print(f"   {k}: {v}")
    print(f"   is_grounded: {is_grounded(sv)}\n")

    # 2. Validate v1 SummaryView
    print("2. Validating v1 SummaryView:")
    validate_summary_view(sv)
    print("   PASSED\n")

    # 3. Reject SummaryView with no refs
    print("3. Rejecting SummaryView with no source_refs:")
    try:
        create_summary_view(
            summary_id="artifact:run53:summary:v1",
            text="A lossy summary",
            source_refs=[],
            view_of="artifact:run53:output:r1",
        )
    except ForgeRefError as e:
        print(f"   ForgeRefError: {e}\n")

    # 4. Reject bad ref format
    print("4. Rejecting bad ref format:")
    try:
        create_summary_view(
            summary_id="artifact:run53:summary:v1",
            text="Summary",
            source_refs=["just-a-string"],
            view_of="artifact:run53:output:r1",
        )
    except ForgeRefError as e:
        print(f"   ForgeRefError: {e}\n")

    # 5. validate_summary dispatcher accepts v1 SummaryView
    print("5. validate_summary dispatcher accepts SummaryView:")
    dispatched = validate_summary(sv)
    print(f"   type: {dispatched['type']}\n")

    # 6. is_grounded on ungrounded object
    print("6. is_grounded on ungrounded object:")
    bad = {"summary": "No refs here"}
    print(f"   is_grounded: {is_grounded(bad)}")

    print("\nAll checks passed.")
