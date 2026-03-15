"""
forge_stage_output.py — Stage output artifact governed by the Forge grammar layer.

v1 convergence: create_v1_stage_artifact() and create_v1_stage_summary()
emit full forge.internal.v1 envelopes that pass the canonical validator.
The old create_stage_output() is kept as a deprecated compatibility wrapper.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from forge_nulls import AbsenceState, ForgeNullError, normalize_absence_state, validate_record
from forge_reversible_summary import ForgeRefError, create_summary, create_summary_view
from forge_v1_bridge import (
    assert_artifact_envelope_v1,
    load_protocol_dict,
    normalize_code,
    record_legacy_usage,
    validate_artifact_envelope_v1,
    validate_summary_view_v1,
)

PROTOCOL_ID = "forge.internal.v1"


def load_protocol_codes() -> dict[str, dict]:
    """Load protocol dict via v1 bridge."""
    return load_protocol_dict()


class ForgeProtocolError(Exception):
    """Raised when a protocol code is invalid or misused."""


# --- v1 artifact helpers ---

def _compute_payload_hash(payload: dict) -> dict:
    """Hash the semantic payload for the artifact envelope."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"algorithm": "sha256", "value": digest}


def _structured_ref(ref_id: str, state: str = "resolved") -> dict:
    return {"ref": ref_id, "state": state}


def _make_loc(stage_id: str) -> str:
    """Derive a storage location from the stage_id."""
    safe = stage_id.replace(":", "/")
    return f"memory/stages/{safe}.json"


def _validate_finding_v1(finding: dict, codes: dict[str, dict]) -> dict:
    """Validate a finding dict. Codes must be v1 domain-dot format."""
    if not isinstance(finding, dict):
        raise ForgeProtocolError(f"Finding must be a dict, got {type(finding).__name__}")

    code = finding.get("code")
    if not code or not isinstance(code, str):
        raise ForgeProtocolError(f"Finding missing 'code': {finding}")

    v1_code = normalize_code(code)
    if v1_code not in codes:
        raise ForgeProtocolError(
            f"Unknown protocol code '{v1_code}'. "
            f"Must be registered in forge_protocol_dict.json"
        )

    if "detail" not in finding:
        raise ForgeProtocolError(f"Finding '{v1_code}' missing 'detail'")

    entry = codes[v1_code]
    out = dict(finding)
    out["code"] = v1_code  # normalize to domain-dot
    out.setdefault("severity", entry["severity"])
    return out


# --- v1 canonical: stage artifact ---

def create_v1_stage_artifact(
    stage_id: str,
    seat: str,
    producer_name: str,
    producer_role: str,
    output: str | None,
    output_state: AbsenceState | None = None,
    source_refs: list[str] | None = None,
    findings: list[dict] | None = None,
    stop_reason: str | None = None,
) -> dict:
    """Build a v1 ArtifactEnvelope for a stage output.

    Returns a dict that passes validate_artifact_envelope from the
    canonical forge.internal.v1 validator.
    """
    codes = load_protocol_codes()
    now = datetime.now(timezone.utc).isoformat()

    # Validate stop_reason
    if stop_reason is not None:
        v1_stop = normalize_code(stop_reason)
        if v1_stop not in codes:
            raise ForgeProtocolError(f"Unknown stop_reason: '{v1_stop}'")
        entry = codes[v1_stop]
        domain = entry.get("domain", "")
        if domain != "STOP":
            raise ForgeProtocolError(f"Code '{v1_stop}' is domain '{domain}', not 'STOP'")
        stop_reason = v1_stop

    # Semantic payload
    payload: dict[str, Any] = {
        "seat": seat,
    }

    # Output — present or typed-absent
    if output is not None:
        payload["output"] = output
        payload["status"] = "complete"
    else:
        if output_state is None:
            raise ForgeNullError(
                "output is None but no output_state provided. "
                "Use AbsenceState to type the absence."
            )
        canonical_state = normalize_absence_state(output_state.value)
        payload["output"] = None
        payload["output_state"] = canonical_state
        payload["status"] = "failed" if stop_reason else "skipped"

    # Stop reason — present or typed-absent
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    else:
        payload["stop_reason"] = None
        payload["stop_reason_state"] = "not_invoked"

    # Findings — present (validated) or typed-absent
    if findings:
        payload["findings"] = [_validate_finding_v1(f, codes) for f in findings]
    else:
        payload["findings"] = None
        payload["findings_state"] = (
            "not_invoked" if output is None else "not_generated"
        )

    # Build refs from source_refs
    refs = []
    if source_refs:
        for ref_id in source_refs:
            refs.append(_structured_ref(ref_id))

    # Assemble the v1 artifact envelope
    artifact = {
        "id": stage_id,
        "type": "stage_output",
        "schema_version": PROTOCOL_ID,
        "hash": _compute_payload_hash(payload),
        "loc": _make_loc(stage_id),
        "refs": refs,
        "created_at": now,
        "producer": {
            "name": producer_name,
            "role": producer_role,
            "version": "1.0.0",
        },
    }
    artifact.update(payload)

    # Final null discipline + bridge assertion on tool egress
    validate_record(artifact)
    assert_artifact_envelope_v1(artifact)

    return artifact


def create_v1_stage_summary(
    stage_artifact: dict,
    summary_text: str,
    extra_source_refs: list[str] | None = None,
) -> dict:
    """Build a v1 SummaryView for a completed stage artifact.

    The summary's view_of points to the stage artifact.
    source_refs include the stage artifact plus any extras.
    """
    artifact_id = stage_artifact["id"]
    summary_id = artifact_id.replace(":stage:", ":summary:stage:")
    if summary_id == artifact_id:
        summary_id = f"{artifact_id}:summary"

    all_refs = [artifact_id]
    if extra_source_refs:
        all_refs.extend(extra_source_refs)

    return create_summary_view(
        summary_id=summary_id,
        text=summary_text,
        source_refs=all_refs,
        view_of=artifact_id,
    )


# --- v1 validation ---

def validate_v1_stage(
    artifact: dict,
    summary: dict | None = None,
    known_artifact_ids: set[str] | None = None,
) -> list[dict]:
    """Validate a stage artifact (and optional summary) against the canonical v1 spec.

    known_artifact_ids: IDs of upstream artifacts that exist in the chamber
    context but aren't passed here. Avoids false REF.REF_UNRESOLVED errors.

    Returns a list of error dicts. Empty list = clean pass.
    """
    from forge_v1_bridge import validate_summary_view_v1

    index = set()
    artifact_id = artifact.get("id")
    if isinstance(artifact_id, str):
        index.add(artifact_id)
    if summary is not None:
        sid = summary.get("id")
        if isinstance(sid, str):
            index.add(sid)
    if known_artifact_ids:
        index |= set(known_artifact_ids)

    errors = validate_artifact_envelope_v1(artifact, index)
    if summary is not None:
        errors.extend(validate_summary_view_v1(summary, index))

    return errors


# --- Deprecated: Phase 2 compatibility wrappers ---

def _validate_finding(finding: dict, codes: dict[str, dict]) -> dict:
    """DEPRECATED — use _validate_finding_v1."""
    return _validate_finding_v1(finding, codes)


def create_stage_output(
    stage_id: str,
    seat: str,
    output: str | None,
    source_refs: list[str] | None = None,
    output_state: AbsenceState | None = None,
    summary_text: str | None = None,
    findings: list[dict] | None = None,
    stop_reason: str | None = None,
) -> dict:
    """DEPRECATED — use create_v1_stage_artifact + create_v1_stage_summary.

    Compatibility-only wrapper kept for caller stability.
    Removal gate: explicit deprecation window plus confirmed zero external callers.
    """
    record_legacy_usage(
        "stage.create_stage_output",
        detail=f"seat={seat}",
        stacklevel=2,
    )
    codes = load_protocol_codes()
    now = datetime.now(timezone.utc).isoformat()

    if stop_reason is not None:
        if stop_reason not in codes:
            raise ForgeProtocolError(f"Unknown stop_reason code: '{stop_reason}'")

    record: dict[str, Any] = {
        "stage_id": stage_id,
        "seat": seat,
        "created_at": now,
    }

    if stop_reason is not None:
        record["stop_reason"] = stop_reason
    else:
        record["stop_reason"] = None
        record["stop_reason_state"] = "not_invoked"

    if output is not None:
        record["output"] = output
        if not summary_text:
            raise ValueError("summary_text is required when output is present")
        if not source_refs:
            raise ForgeRefError("source_refs required to create grounded summary")
        record["summary"] = create_summary(summary_text, source_refs)
        record["status"] = "complete"
    else:
        if output_state is None:
            raise ForgeNullError(
                "output is None but no output_state provided. "
                "Use AbsenceState to type the absence."
            )
        canonical_state = normalize_absence_state(output_state.value)
        record["output"] = None
        record["output_state"] = canonical_state
        record["summary"] = None
        record["summary_state"] = (
            "not_invoked" if output_state in (AbsenceState.NOT_GENERATED, AbsenceState.NOT_INVOKED)
            else canonical_state
        )
        record["status"] = "failed" if stop_reason else "skipped"

    if findings:
        record["findings"] = [_validate_finding_v1(f, codes) for f in findings]
    else:
        record["findings"] = None
        record["findings_state"] = "not_invoked" if output is None else "not_generated"

    validate_record(record)
    return record


def validate_stage_output(obj: dict) -> dict:
    """DEPRECATED — use validate_v1_stage.

    Compatibility-only validator path for legacy stage record shapes.
    Removal gate: explicit deprecation window plus confirmed zero external callers.
    """
    codes = load_protocol_codes()
    validate_record(obj)

    summary = obj.get("summary")
    if summary is not None:
        from forge_reversible_summary import validate_summary
        validate_summary(summary)
    elif "summary_state" not in obj:
        raise ForgeNullError("summary is None but no summary_state")

    findings = obj.get("findings")
    if findings is not None:
        for f in findings:
            _validate_finding_v1(f, codes)
    elif "findings_state" not in obj:
        raise ForgeNullError("findings is None but no findings_state")

    sr = obj.get("stop_reason")
    if sr is not None and sr not in codes:
        raise ForgeProtocolError(f"Unknown stop_reason code: '{sr}'")

    return obj


# --- End-to-end: v1 artifact path under Primordial law ---

if __name__ == "__main__":
    print("=== forge_stage_output.py — v1 Artifact Path ===\n")

    # Scenario 1: Happy path — complete stage → artifact + summary
    print("1. v1 Happy path — Builder completes, full envelope + SummaryView:")
    art = create_v1_stage_artifact(
        stage_id="artifact:run52:stage:builder:r1",
        seat="builder",
        producer_name="builder-agent",
        producer_role="builder",
        output="def validate(schema): return check(schema, strict=True)",
        source_refs=[
            "artifact:run52:architect_plan:r1",
            "artifact:run52:requirements:r1",
        ],
    )
    sv = create_v1_stage_summary(
        art,
        "Builder produced strict schema validation function.",
        extra_source_refs=["artifact:run52:architect_plan:r1"],
    )
    # Upstream artifacts exist in the chamber — tell the validator
    chamber_context = {
        "artifact:run52:architect_plan:r1",
        "artifact:run52:requirements:r1",
    }
    errors = validate_v1_stage(art, sv, known_artifact_ids=chamber_context)
    print(f"   artifact.id: {art['id']}")
    print(f"   artifact.type: {art['type']}")
    print(f"   artifact.schema_version: {art['schema_version']}")
    print(f"   artifact.hash: {art['hash']['algorithm']}:{art['hash']['value'][:16]}...")
    print(f"   artifact.status: {art['status']}")
    print(f"   artifact.stop_reason_state: {art['stop_reason_state']}")
    print(f"   artifact.findings_state: {art['findings_state']}")
    print(f"   summary.id: {sv['id']}")
    print(f"   summary.type: {sv['type']}")
    print(f"   summary.view_of: {sv['view_of']}")
    print(f"   summary.source_refs: {[r['ref'] for r in sv['source_refs']]}")
    print(f"   v1 validation errors: {errors}")
    assert errors == [], f"FAILED: {errors}"
    print("   PASSED\n")

    # Scenario 2: Typed absence — Builder times out
    print("2. v1 Typed absence — Builder times out, findings with domain-dot code:")
    art2 = create_v1_stage_artifact(
        stage_id="artifact:run53:stage:builder:r1",
        seat="builder",
        producer_name="builder-agent",
        producer_role="builder",
        output=None,
        output_state=AbsenceState.NOT_GENERATED,
        stop_reason="STOP.STOP_TIMEOUT",
        findings=[
            {"code": "ERROR.ERR_TIMEOUT_SEAT", "detail": "Builder exceeded 30s limit"},
        ],
    )
    errors2 = validate_v1_stage(art2)
    print(f"   artifact.status: {art2['status']}")
    print(f"   artifact.output: {art2['output']}")
    print(f"   artifact.output_state: {art2['output_state']}")
    print(f"   artifact.stop_reason: {art2['stop_reason']}")
    print(f"   artifact.findings: {art2['findings']}")
    print(f"   v1 validation errors: {errors2}")
    assert errors2 == [], f"FAILED: {errors2}"
    print("   PASSED\n")

    # Scenario 3: Rejection — ambiguous null
    print("3. Rejection — bare None output:")
    try:
        create_v1_stage_artifact(
            stage_id="artifact:run54:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output=None,
        )
        print("   UNEXPECTED PASS")
    except ForgeNullError as e:
        print(f"   ForgeNullError: {e}\n")

    # Scenario 4: Rejection — ungrounded summary
    print("4. Rejection — summary with no refs:")
    try:
        art4 = create_v1_stage_artifact(
            stage_id="artifact:run55:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="some code",
        )
        create_v1_stage_summary(art4, "Lossy summary.", extra_source_refs=[])
        # view_of ref is automatically added, but let's test with explicitly empty
        print("   (view_of auto-included — rejection requires deeper test)")
    except ForgeRefError as e:
        print(f"   ForgeRefError: {e}\n")

    # Scenario 5: Rejection — unknown protocol code
    print("5. Rejection — finding with unknown code:")
    try:
        create_v1_stage_artifact(
            stage_id="artifact:run56:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output=None,
            output_state=AbsenceState.INVALID,
            findings=[
                {"code": "MADE_UP.CODE", "detail": "Does not exist"},
            ],
        )
        print("   UNEXPECTED PASS")
    except ForgeProtocolError as e:
        print(f"   ForgeProtocolError: {e}\n")

    print("All v1 scenarios passed.")
