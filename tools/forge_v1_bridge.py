"""
forge_v1_bridge.py — Thin adapter between forge tools and the canonical
forge.internal.v1 validator from the Codex spec package.

Tries to import the canonical validator directly. If unavailable,
falls back to a narrow structural shim that enforces equivalent invariants.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Attempt to import the canonical v1 validator from the Codex package.
_CODEX_PACKAGE = os.path.expanduser("~/Codex x LoveSpark/lovespark-senate-codex")

_v1_validator = None

if os.path.isdir(_CODEX_PACKAGE):
    if _CODEX_PACKAGE not in sys.path:
        sys.path.insert(0, _CODEX_PACKAGE)
    try:
        from forge_protocol.validator import (
            ABSENCE_STATES as V1_ABSENCE_STATES,
            ARTIFACT_ID_RE,
            CODE_RE,
            validate_absence_tagged_field,
            validate_artifact_envelope as _v1_validate_artifact_envelope,
            validate_protocol_dictionary_entry,
            validate_summary_view as _v1_validate_summary_view,
        )
        _v1_validator = "codex"
    except ImportError:
        pass


class ForgeBridgeValidationError(ValueError):
    """Raised when bridge assertion detects v1 non-compliance."""


# --- Code mapping: legacy underscore codes -> v1 domain-dot codes ---
# Prefer active canonical v1 codes when possible.

_LEGACY_CODE_MAP = {
    "ABS_UNKNOWN": "ABSENCE.ABS_UNKNOWN",
    "ABS_NOT_GENERATED": "ABSENCE.ABS_NOT_GENERATED",
    "ABS_NOT_INVOKED": "ABSENCE.ABS_NOT_INVOKED",
    "ABS_INVALID": "ABSENCE.ABS_INVALID",
    "ABS_WITHHELD": "ABSENCE.ABS_WITHHELD",
    "ABS_PRUNED": "ABSENCE.ABS_PRUNED_RECOVERABLE",
    "ABS_DELETED": "ABSENCE.ABS_DELETED",
    "ABS_UNRESOLVED": "ABSENCE.ABS_UNRESOLVED",
    "STOP_CONSENSUS": "STOP.STOP_CONSENSUS",
    "STOP_FORCED": "STOP.STOP_FORCED",
    "STOP_USER": "STOP.STOP_USER",
    "STOP_TIMEOUT": "STOP.STOP_TIMEOUT",
    "STOP_BUDGET": "STOP.STOP_BUDGET",
    "STOP_ERROR": "STOP.STOP_ERROR",
    "ERR_SCHEMA_FAIL": "ERROR.ERR_SCHEMA_FAIL",
    "ERR_TIMEOUT_SEAT": "ERROR.ERR_TIMEOUT_SEAT",
    "ERR_PARSE_FAIL": "ERROR.ERR_PARSE_FAIL",
    "ERR_API_FAIL": "ERROR.ERR_API_FAIL",
    "ERR_VALIDATION_FAIL": "ERROR.ERR_VALIDATION_FAIL",
    "CRIT_SCHEMA": "CRITIQUE.CRIT_SCHEMA",
    "CRIT_SECURITY": "CRITIQUE.CRIT_SECURITY",
    "CRIT_PERMISSIONS": "CRITIQUE.CRIT_PERMISSIONS",
    "CRIT_ARCHITECTURE": "CRITIQUE.CRIT_ARCHITECTURE",
    "CRIT_TESTING": "CRITIQUE.CRIT_TESTING",
    "CRIT_INVARIANT": "CRITIQUE.CRIT_INVARIANT",
    "REV_BLOCK_SCHEMA": "REVISION.REV_BLOCK_SCHEMA",
    "REV_BLOCK_INVARIANT": "REVISION.REV_BLOCK_INVARIANT",
    # Legacy protocol-violation names map to canonical active v1 codes.
    "PROTO_UNGROUNDED_SUMMARY": "SUMMARY.MISSING_SOURCE_REFS",
    "PROTO_AMBIGUOUS_NULL": "ABSENCE.MISSING_STATE_LABEL",
    "PROTO_MISSING_REF": "REF.REF_UNRESOLVED",
}

_REVERSE_CODE_MAP = {v: k for k, v in _LEGACY_CODE_MAP.items()}

_SEVERITY_MAP = {
    None: "low",
    "info": "low",
    "warn": "med",
    "warning": "med",
    "low": "low",
    "med": "med",
    "high": "high",
    "error": "high",
    "critical": "block",
    "fatal": "block",
    "block": "block",
}

_LEGACY_USAGE_COUNTS: dict[str, int] = {}
_LEGACY_USAGE_EVENTS: list[dict[str, Any]] = []


def _caller_location(stacklevel: int = 2) -> str:
    """Best-effort caller location in '<file>:<line>' format."""
    try:
        stack = inspect.stack()
        this_file = str(Path(__file__).resolve())

        # Prefer the first frame outside this module for easier auditability.
        for frame in stack[stacklevel:]:
            try:
                if str(Path(frame.filename).resolve()) != this_file:
                    return f"{Path(frame.filename).name}:{frame.lineno}"
            except Exception:
                continue

        # Fallback to requested stacklevel if all frames are in this module.
        frame = stack[stacklevel]
        return f"{Path(frame.filename).name}:{frame.lineno}"
    except Exception:
        return "unknown"


def record_legacy_usage(
    surface: str,
    *,
    detail: str | None = None,
    stacklevel: int = 2,
) -> dict[str, Any]:
    """Record standardized telemetry for a compatibility-only legacy surface.

    Emits:
    - in-process counter
    - DeprecationWarning with normalized message format
    - optional JSON event to stderr when FORGE_LEGACY_LOG_STDERR=1
    """
    count = _LEGACY_USAGE_COUNTS.get(surface, 0) + 1
    _LEGACY_USAGE_COUNTS[surface] = count
    location = _caller_location(stacklevel)

    event = {
        "event": "forge_legacy_usage",
        "surface": surface,
        "count": count,
        "location": location,
        "detail": detail,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    _LEGACY_USAGE_EVENTS.append(event)

    msg = f"[forge-legacy] surface={surface}; count={count}; location={location}"
    if detail:
        msg += f"; detail={detail}"
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)

    if os.getenv("FORGE_LEGACY_LOG_STDERR", "0").lower() in {"1", "true", "yes"}:
        print(json.dumps(event, sort_keys=True), file=sys.stderr)

    return event


def get_legacy_usage_counts() -> dict[str, int]:
    """Return a snapshot of legacy-surface usage counters."""
    return dict(_LEGACY_USAGE_COUNTS)


def get_legacy_usage_events() -> list[dict[str, Any]]:
    """Return a snapshot of recorded legacy-surface usage events."""
    return [dict(e) for e in _LEGACY_USAGE_EVENTS]


def reset_legacy_usage_counts() -> None:
    """Clear in-process legacy-surface telemetry (used by tests)."""
    _LEGACY_USAGE_COUNTS.clear()
    _LEGACY_USAGE_EVENTS.clear()


def normalize_code(code: str) -> str:
    """Convert a legacy underscore code to v1 domain-dot format.

    This compatibility path is ingress-only and slated for removal after an
    explicit deprecation window and confirmed zero external callers.
    Returns code unchanged if already domain-dot.
    """
    if not isinstance(code, str) or not code:
        return code
    if "." in code:
        return code
    mapped = _LEGACY_CODE_MAP.get(code, code)
    if mapped != code:
        record_legacy_usage(
            "code.underscore_ingress",
            detail=f"{code}->{mapped}",
            stacklevel=2,
        )
    return mapped


def _normalize_severity(severity: Any) -> str:
    if isinstance(severity, str):
        severity = severity.lower().strip()
    return _SEVERITY_MAP.get(severity, "low")


def _normalize_lifecycle(lifecycle: Any) -> str:
    if isinstance(lifecycle, str):
        lifecycle = lifecycle.lower().strip()
    return lifecycle if lifecycle in {"active", "deprecated"} else "active"


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize a protocol dictionary entry to canonical v1 shape."""
    if not isinstance(entry, dict):
        raise ValueError(f"Protocol dict entry must be object, got {type(entry).__name__}")

    original_code = entry.get("code", "")
    if not isinstance(original_code, str) or not original_code:
        raise ValueError(f"Protocol dict entry missing code: {entry}")

    code = normalize_code(original_code)
    domain = code.split(".", 1)[0] if "." in code else str(entry.get("domain", "PROTO"))

    normalized = dict(entry)
    normalized["proto"] = str(entry.get("proto", "forge.internal.v1"))
    normalized["version"] = str(entry.get("version", "1.0.0"))
    normalized["domain"] = domain
    normalized["code"] = code
    normalized["severity"] = _normalize_severity(entry.get("severity"))
    normalized["lifecycle"] = _normalize_lifecycle(entry.get("lifecycle"))

    if "meaning" not in normalized:
        normalized["meaning"] = "Legacy entry migrated to v1 shape."
    if "human_decode" not in normalized:
        normalized["human_decode"] = normalized["meaning"]

    if "replaced_by" in normalized and isinstance(normalized["replaced_by"], str):
        normalized["replaced_by"] = normalize_code(normalized["replaced_by"])

    return normalized


# --- Dictionary loader with backward compatibility ---

def load_protocol_dict(path: str | None = None) -> dict[str, dict]:
    """Load the protocol dictionary with ingress compatibility.

    Supports both:
    - legacy flat list format
    - v1 container format: {"proto": ..., "version": ..., "entries": [...]}.

    Legacy flat-list ingress is compatibility-only and slated for removal after
    an explicit deprecation window and confirmed zero external callers.
    All entries are normalized to canonical v1 shape internally.
    Returns a lookup keyed by both canonical and legacy code aliases.
    """
    if path is None:
        path = str(Path(__file__).parent / "forge_protocol_dict.json")

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        record_legacy_usage(
            "dict.flat_list_ingress",
            detail=f"path={path}",
            stacklevel=2,
        )
        entries = raw
    elif isinstance(raw, dict) and "entries" in raw and isinstance(raw["entries"], list):
        entries = raw["entries"]
    else:
        raise ValueError(f"Unrecognized protocol dict format in {path}")

    code_map: dict[str, dict] = {}

    for original in entries:
        normalized = _normalize_entry(original)
        canonical_code = normalized["code"]

        # Canonical key
        code_map[canonical_code] = normalized

        # Legacy key from raw entry (if different)
        raw_code = original.get("code") if isinstance(original, dict) else None
        if isinstance(raw_code, str) and raw_code and raw_code != canonical_code:
            code_map[raw_code] = normalized

        # Legacy underscore alias inferred from canonical code
        legacy_alias = _REVERSE_CODE_MAP.get(canonical_code)
        if legacy_alias:
            code_map[legacy_alias] = normalized

    return code_map


# --- v1 validation bridge ---

def validate_summary_view_v1(summary_view: dict, artifact_index: set[str] | None = None) -> list[dict]:
    """Validate a SummaryView against the v1 spec."""
    if _v1_validator == "codex":
        return _v1_validate_summary_view(summary_view, artifact_index)
    return _shim_validate_summary_view(summary_view, artifact_index)


def validate_artifact_envelope_v1(artifact: dict, artifact_index: set[str] | None = None) -> list[dict]:
    """Validate an ArtifactEnvelope against the v1 spec."""
    if _v1_validator == "codex":
        return _v1_validate_artifact_envelope(artifact, artifact_index)
    return _shim_validate_artifact_envelope(artifact, artifact_index)


def validate_absence_field_v1(field_obj: dict) -> list[dict]:
    """Validate a v1 absence-tagged field object."""
    if _v1_validator == "codex":
        return validate_absence_tagged_field(field_obj)
    return _shim_validate_absence_field(field_obj)


def validate_dict_entry_v1(entry: dict) -> list[dict]:
    """Validate a protocol dictionary entry against v1 spec."""
    if _v1_validator == "codex":
        return validate_protocol_dictionary_entry(entry)
    return _shim_validate_dict_entry(entry)


def _raise_if_errors(label: str, errors: list[dict]) -> None:
    if not errors:
        return
    formatted = "; ".join(f"{e.get('code')}:{e.get('path')}:{e.get('message')}" for e in errors)
    raise ForgeBridgeValidationError(f"{label} failed v1 validation: {formatted}")


def assert_summary_view_v1(summary_view: dict, artifact_index: set[str] | None = None) -> None:
    """Assert SummaryView is v1-compliant, raise on failure."""
    _raise_if_errors("SummaryView", validate_summary_view_v1(summary_view, artifact_index))


def assert_artifact_envelope_v1(artifact: dict, artifact_index: set[str] | None = None) -> None:
    """Assert ArtifactEnvelope is v1-compliant, raise on failure."""
    _raise_if_errors("ArtifactEnvelope", validate_artifact_envelope_v1(artifact, artifact_index))


def get_validator_source() -> str:
    """Return which validator backend is active."""
    return _v1_validator or "shim"


# --- Structural shim (local fallback) ---

_SHIM_ABSENCE_STATES = frozenset({
    "not_generated", "not_invoked", "unknown", "withheld",
    "invalid", "deleted", "pruned_recoverable", "unresolved",
})
_SHIM_SEVERITIES = frozenset({"low", "med", "high", "block"})
_SHIM_LIFECYCLES = frozenset({"active", "deprecated"})
_SHIM_ARTIFACT_ID_RE = re.compile(r"^artifact:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$")
_SHIM_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*$")


def _err(code: str, message: str, path: str) -> dict:
    return {"code": code, "message": message, "path": path}


def _shim_validate_ref_entries(refs: Any, path: str) -> list[dict]:
    errors: list[dict] = []
    if not isinstance(refs, list):
        return [_err("REVISION.REV_BLOCK_SCHEMA", "refs must be list", path)]

    for i, entry in enumerate(refs):
        item_path = f"{path}[{i}]"
        if not isinstance(entry, dict):
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "ref must be object", item_path))
            continue
        ref_id = entry.get("ref", "")
        if not isinstance(ref_id, str) or not _SHIM_ARTIFACT_ID_RE.fullmatch(ref_id):
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad ref id", f"{item_path}.ref"))
        state = entry.get("state")
        if state not in {"resolved", "unresolved"}:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad ref state", f"{item_path}.state"))
        if state == "unresolved" and not isinstance(entry.get("reason"), str):
            errors.append(_err("REF.REF_UNRESOLVED", "unresolved ref requires reason", f"{item_path}.reason"))
    return errors


def _shim_validate_summary_view(sv: dict, index: set[str] | None = None) -> list[dict]:
    errors = []
    for key in ["id", "type", "schema_version", "created_at", "summary", "source_refs", "view_of", "summary_hash"]:
        if key not in sv:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", f"missing: {key}", key))

    if sv.get("type") != "summary_view":
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "type must be summary_view", "type"))

    if not isinstance(sv.get("summary"), str) or not sv.get("summary", "").strip():
        errors.append(_err("SUMMARY.MISSING_SOURCE_REFS", "summary empty", "summary"))

    errors.extend(_shim_validate_ref_entries(sv.get("source_refs"), "source_refs"))

    view_of = sv.get("view_of")
    if not isinstance(view_of, str) or not _SHIM_ARTIFACT_ID_RE.fullmatch(view_of):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "view_of invalid", "view_of"))

    summary_hash = sv.get("summary_hash")
    if not isinstance(summary_hash, dict):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "summary_hash must be object", "summary_hash"))
    else:
        if summary_hash.get("algorithm") not in {"sha256", "sha512", "blake3"}:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad hash algorithm", "summary_hash.algorithm"))
        val = summary_hash.get("value", "")
        if not isinstance(val, str) or len(val) < 16 or not re.fullmatch(r"[A-Fa-f0-9]+", val):
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad hash value", "summary_hash.value"))

    if sv.get("schema_version") != "forge.internal.v1":
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "schema_version wrong", "schema_version"))

    if index is not None:
        for i, entry in enumerate(sv.get("source_refs", [])):
            if isinstance(entry, dict) and entry.get("state") == "resolved" and entry.get("ref") not in index:
                errors.append(_err("REF.REF_UNRESOLVED", "resolved ref missing in index", f"source_refs[{i}]"))
        if isinstance(view_of, str) and view_of not in index:
            errors.append(_err("REF.REF_UNRESOLVED", "view_of missing in index", "view_of"))

    return errors


def _shim_validate_artifact_envelope(artifact: dict, index: set[str] | None = None) -> list[dict]:
    errors = []
    required = ["id", "type", "schema_version", "hash", "loc", "refs", "created_at", "producer"]
    for key in required:
        if key not in artifact:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", f"missing: {key}", key))

    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str) or not _SHIM_ARTIFACT_ID_RE.fullmatch(artifact_id):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "id invalid", "id"))

    if artifact.get("schema_version") != "forge.internal.v1":
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "schema_version wrong", "schema_version"))

    if not isinstance(artifact.get("type"), str) or not artifact.get("type", "").strip():
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "type required", "type"))

    if not isinstance(artifact.get("loc"), str) or not artifact.get("loc", "").strip():
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "loc required", "loc"))

    hash_obj = artifact.get("hash")
    if not isinstance(hash_obj, dict):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "hash must be object", "hash"))
    else:
        if hash_obj.get("algorithm") not in {"sha256", "sha512", "blake3"}:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad hash algorithm", "hash.algorithm"))
        hv = hash_obj.get("value", "")
        if not isinstance(hv, str) or len(hv) < 16 or not re.fullmatch(r"[A-Fa-f0-9]+", hv):
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "bad hash value", "hash.value"))

    producer = artifact.get("producer")
    if not isinstance(producer, dict):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "producer must be object", "producer"))
    else:
        if not isinstance(producer.get("name"), str) or not producer.get("name", "").strip():
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "producer.name required", "producer.name"))
        if not isinstance(producer.get("role"), str) or not producer.get("role", "").strip():
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "producer.role required", "producer.role"))

    errors.extend(_shim_validate_ref_entries(artifact.get("refs"), "refs"))

    if index is not None:
        for i, entry in enumerate(artifact.get("refs", [])):
            if isinstance(entry, dict) and entry.get("state") == "resolved" and entry.get("ref") not in index:
                errors.append(_err("REF.REF_UNRESOLVED", "resolved ref missing in index", f"refs[{i}]"))

    return errors


def _shim_validate_absence_field(field_obj: dict) -> list[dict]:
    errors = []
    for key in ["field", "value", "state"]:
        if key not in field_obj:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", f"missing: {key}", key))

    state = field_obj.get("state")
    if state not in _SHIM_ABSENCE_STATES:
        errors.append(_err("ABSENCE.MISSING_STATE_LABEL", "invalid state", "state"))

    return errors


def _shim_validate_dict_entry(entry: dict) -> list[dict]:
    errors = []
    for key in ["proto", "version", "domain", "code", "meaning", "human_decode", "severity", "lifecycle"]:
        if key not in entry:
            errors.append(_err("REVISION.REV_BLOCK_SCHEMA", f"missing: {key}", key))

    if entry.get("proto") != "forge.internal.v1":
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "proto wrong", "proto"))

    code = entry.get("code", "")
    domain = entry.get("domain", "")
    if not _SHIM_CODE_RE.match(code):
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "code format invalid", "code"))
    elif code.split(".", 1)[0] != domain:
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "domain must match code prefix", "domain"))

    if entry.get("severity") not in _SHIM_SEVERITIES:
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "severity invalid", "severity"))

    if entry.get("lifecycle") not in _SHIM_LIFECYCLES:
        errors.append(_err("REVISION.REV_BLOCK_SCHEMA", "lifecycle invalid", "lifecycle"))

    return errors


if __name__ == "__main__":
    print(f"=== forge_v1_bridge.py — Validator: {get_validator_source()} ===\n")

    codes = load_protocol_dict()
    print(f"1. Loaded {len(codes)} code entries (canonical + compatibility aliases)")
    print(f"   Sample canonical: STOP.STOP_TIMEOUT -> {codes.get('STOP.STOP_TIMEOUT', {}).get('meaning', 'NOT FOUND')}")
    print(f"   Sample canonical: SUMMARY.MISSING_SOURCE_REFS -> {codes.get('SUMMARY.MISSING_SOURCE_REFS', {}).get('meaning', 'NOT FOUND')}\n")

    print("2. Canonical code normalization (passthrough):")
    print(f"   STOP.STOP_TIMEOUT -> {normalize_code('STOP.STOP_TIMEOUT')}")
    print(f"   REVISION.REV_BLOCK_SCHEMA -> {normalize_code('REVISION.REV_BLOCK_SCHEMA')}\n")

    print("All bridge checks passed.")
