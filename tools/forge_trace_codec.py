"""
forge_trace_codec.py — Structural trace compression with exact reversibility.

Compresses chamber stage traces by factoring out repeated substructures
into a shared dictionary, replacing occurrences with $ref strings.
Every compressed trace round-trips exactly to the original.

Phase 4 scope: dict-level dedup (producers, ref entries, hash objects).
Sequential deltas deferred until real traces prove the need.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

PROTOCOL_ID = "forge.internal.v1"
ENCODING_ID = "forge.trace.v1"
_REF_PREFIX = "$ref:shared."


class ForgeTraceError(Exception):
    """Trace codec invariant violation."""


# --- Deterministic hashing ---

def _canonical_json(obj: Any) -> str:
    """Deterministic JSON for comparison and hashing."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True)


def _hash_json(obj: Any) -> str:
    """SHA-256 of canonical JSON."""
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


# --- Shared structure collection ---

def _collect_dict_candidates(obj: Any) -> list[tuple[str, dict]]:
    """Recursively collect all dicts (2+ keys) with canonical JSON keys.

    Collects the object itself if it's a qualifying dict, then recurses
    into all values. This ensures dicts inside lists are found.
    """
    candidates: list[tuple[str, dict]] = []
    if isinstance(obj, dict):
        if len(obj) >= 2:
            candidates.append((_canonical_json(obj), obj))
        for value in obj.values():
            candidates.extend(_collect_dict_candidates(value))
    elif isinstance(obj, list):
        for item in obj:
            candidates.extend(_collect_dict_candidates(item))
    return candidates


def _build_shared(stages: list[dict]) -> tuple[dict[str, Any], dict[str, str]]:
    """Identify dict values that appear 2+ times across stages.

    Returns:
        shared: {key: dict_value} for each repeated structure
        replacements: {canonical_json: "$ref:shared.<key>"} for replacement
    """
    counts: dict[str, tuple[dict, int]] = {}
    for stage in stages:
        for canonical, value in _collect_dict_candidates(stage):
            if canonical in counts:
                counts[canonical] = (value, counts[canonical][1] + 1)
            else:
                counts[canonical] = (value, 1)

    shared: dict[str, Any] = {}
    replacements: dict[str, str] = {}
    idx = 0
    # Sort by canonical form for deterministic key assignment
    for canonical in sorted(counts.keys()):
        value, count = counts[canonical]
        if count >= 2:
            key = f"s{idx}"
            shared[key] = copy.deepcopy(value)
            replacements[canonical] = f"{_REF_PREFIX}{key}"
            idx += 1

    return shared, replacements


# --- $ref application ---

def _apply_refs(obj: Any, replacements: dict[str, str]) -> None:
    """Replace matching dict values with $ref strings. Mutates in place.

    Top-down: checks value before recursing. If matched, replaced and
    children are not visited (they're now in the shared dict).
    """
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            value = obj[key]
            if isinstance(value, dict) and len(value) >= 2:
                canonical = _canonical_json(value)
                if canonical in replacements:
                    obj[key] = replacements[canonical]
                else:
                    _apply_refs(value, replacements)
            elif isinstance(value, list):
                _apply_refs_list(value, replacements)
    elif isinstance(obj, list):
        _apply_refs_list(obj, replacements)


def _apply_refs_list(lst: list, replacements: dict[str, str]) -> None:
    for i, item in enumerate(lst):
        if isinstance(item, dict) and len(item) >= 2:
            canonical = _canonical_json(item)
            if canonical in replacements:
                lst[i] = replacements[canonical]
            else:
                _apply_refs(item, replacements)
        elif isinstance(item, list):
            _apply_refs_list(item, replacements)


# --- $ref resolution ---

def _resolve_path(shared: dict, path: str) -> Any:
    """Resolve a dotted path in the shared dict."""
    parts = path.split(".")
    current: Any = shared
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            raise ForgeTraceError(f"Cannot resolve shared path: {path!r}")
        current = current[part]
    return current


def _resolve_refs(obj: Any, shared: dict) -> None:
    """Replace $ref strings with actual values from shared. Mutates in place."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            value = obj[key]
            if isinstance(value, str) and value.startswith(_REF_PREFIX):
                path = value[len(_REF_PREFIX):]
                obj[key] = copy.deepcopy(_resolve_path(shared, path))
            elif isinstance(value, dict):
                _resolve_refs(value, shared)
            elif isinstance(value, list):
                _resolve_refs_list(value, shared)
    elif isinstance(obj, list):
        _resolve_refs_list(obj, shared)


def _resolve_refs_list(lst: list, shared: dict) -> None:
    for i, item in enumerate(lst):
        if isinstance(item, str) and item.startswith(_REF_PREFIX):
            path = item[len(_REF_PREFIX):]
            lst[i] = copy.deepcopy(_resolve_path(shared, path))
        elif isinstance(item, dict):
            _resolve_refs(item, shared)
        elif isinstance(item, list):
            _resolve_refs_list(item, shared)


# --- Ref counting ---

def _count_refs(obj: Any) -> int:
    """Count $ref strings in a nested structure."""
    count = 0
    if isinstance(obj, str) and obj.startswith(_REF_PREFIX):
        return 1
    if isinstance(obj, dict):
        for value in obj.values():
            count += _count_refs(value)
    elif isinstance(obj, list):
        for item in obj:
            count += _count_refs(item)
    return count


# --- Public API ---

def encode_trace(chamber: dict) -> dict:
    """Compress a chamber's stages into a trace envelope.

    Factors out repeated substructures into a shared dict,
    replaces occurrences with $ref strings. The original stages
    can be exactly reconstructed via decode_trace().

    Args:
        chamber: A chamber dict (from forge_chamber.py)

    Returns:
        Trace envelope dict with shared structures and compressed stages.
    """
    stages = copy.deepcopy(chamber.get("stages", []))
    original_hash = _hash_json(stages)
    original_size = len(_canonical_json(stages))

    shared, replacements = _build_shared(stages)

    if replacements:
        _apply_refs(stages, replacements)

    encoded_size = len(_canonical_json(stages)) + len(_canonical_json(shared))
    ratio = original_size / encoded_size if encoded_size > 0 else 1.0

    return {
        "trace_id": f"trace:{chamber.get('chamber_id', 'unknown')}",
        "chamber_id": chamber.get("chamber_id", "unknown"),
        "schema_version": PROTOCOL_ID,
        "encoding": ENCODING_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "shared": shared,
        "stages": stages,
        "original_hash": original_hash,
        "compression_ratio": round(ratio, 4),
        "original_size": original_size,
        "encoded_size": encoded_size,
    }


def decode_trace(trace: dict) -> list[dict]:
    """Reconstruct full chamber stages from a trace envelope.

    Resolves all $ref strings using the trace's shared dict.
    Returns fully materialized stage dicts.

    Raises:
        ForgeTraceError: If encoding is unknown or a $ref path cannot resolve.
    """
    if trace.get("encoding") != ENCODING_ID:
        raise ForgeTraceError(
            f"Unknown trace encoding: {trace.get('encoding')!r}. "
            f"Expected {ENCODING_ID!r}"
        )

    shared = trace.get("shared", {})
    stages = copy.deepcopy(trace.get("stages", []))

    if shared:
        _resolve_refs(stages, shared)

    return stages


def verify_trace(trace: dict, chamber: dict | None = None) -> dict:
    """Verify a trace round-trips exactly.

    If chamber is provided, compares decoded stages to original.
    Always checks decoded hash against original_hash in trace.

    Returns:
        {"valid": bool, "hash_match": bool, "content_match": bool|None,
         "decoded_hash": str}
    """
    decoded_stages = decode_trace(trace)
    decoded_hash = _hash_json(decoded_stages)

    original_hash = trace.get("original_hash", "")
    hash_match = decoded_hash == original_hash

    content_match = None
    if chamber is not None:
        original_stages = chamber.get("stages", [])
        content_match = (
            _canonical_json(decoded_stages) == _canonical_json(original_stages)
        )

    return {
        "valid": hash_match and (content_match is not False),
        "hash_match": hash_match,
        "content_match": content_match,
        "decoded_hash": decoded_hash,
    }


def trace_stats(trace: dict) -> dict:
    """Return compression statistics for a trace."""
    shared = trace.get("shared", {})
    shared_count = len(shared)
    ref_count = _count_refs(trace.get("stages", []))

    return {
        "stage_count": len(trace.get("stages", [])),
        "shared_structures": shared_count,
        "ref_replacements": ref_count,
        "compression_ratio": trace.get("compression_ratio", 1.0),
        "original_size": trace.get("original_size", 0),
        "encoded_size": trace.get("encoded_size", 0),
        "encoding": trace.get("encoding", "unknown"),
    }


# --- End-to-end demo ---

if __name__ == "__main__":
    print("=== forge_trace_codec.py — Structural Trace Compression (Phase 4) ===\n")

    from forge_chamber import (
        create_chamber,
        register_stage,
        seal_chamber,
        validate_chamber,
    )
    from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary

    # 1. Build a 3-stage chamber
    print("1. Building 3-stage chamber (architect -> builder -> critic):")
    chamber = create_chamber("chamber:run200:v1")

    architect_art = create_v1_stage_artifact(
        stage_id="artifact:run200:stage:architect:r1",
        seat="architect",
        producer_name="architect-agent",
        producer_role="architect",
        output="Build a schema validator with strict fail-closed defaults.",
    )
    architect_sv = create_v1_stage_summary(
        architect_art,
        "Architect proposes strict fail-closed schema validator.",
    )
    register_stage(chamber, architect_art, architect_sv)

    builder_art = create_v1_stage_artifact(
        stage_id="artifact:run200:stage:builder:r1",
        seat="builder",
        producer_name="builder-agent",
        producer_role="builder",
        output="def validate(schema): return check(schema, strict=True)",
        source_refs=["artifact:run200:stage:architect:r1"],
    )
    builder_sv = create_v1_stage_summary(
        builder_art,
        "Builder implemented strict schema validation.",
        extra_source_refs=["artifact:run200:stage:architect:r1"],
    )
    register_stage(chamber, builder_art, builder_sv)

    critic_art = create_v1_stage_artifact(
        stage_id="artifact:run200:stage:critic:r1",
        seat="critic",
        producer_name="critic-agent",
        producer_role="critic",
        output="Schema validation correct. Concern: no input size limit.",
        source_refs=[
            "artifact:run200:stage:architect:r1",
            "artifact:run200:stage:builder:r1",
        ],
        findings=[
            {"code": "CRITIQUE.CRIT_SECURITY", "detail": "No input size limit"},
        ],
    )
    critic_sv = create_v1_stage_summary(
        critic_art,
        "Critic approved with one security concern about input size.",
        extra_source_refs=[
            "artifact:run200:stage:architect:r1",
            "artifact:run200:stage:builder:r1",
        ],
    )
    register_stage(chamber, critic_art, critic_sv)
    seal_chamber(chamber)

    errors = validate_chamber(chamber)
    assert errors == [], f"Chamber validation failed: {errors}"
    print(f"   3 stages registered, chamber sealed, validation clean")
    print()

    # 2. Encode trace
    print("2. Encoding trace:")
    trace = encode_trace(chamber)
    print(f"   trace_id: {trace['trace_id']}")
    print(f"   encoding: {trace['encoding']}")
    print(f"   shared structures: {len(trace['shared'])}")
    for key, value in trace["shared"].items():
        # Show compact representation of shared structure
        if "ref" in value:
            print(f"     {key}: ref_entry -> {value['ref']}")
        elif "name" in value:
            print(f"     {key}: producer -> {value['name']}")
        elif "algorithm" in value:
            print(f"     {key}: hash -> {value['algorithm']}:{value['value'][:12]}...")
        else:
            keys = list(value.keys())
            print(f"     {key}: dict with keys {keys}")
    print()

    # 3. Compression stats
    print("3. Compression stats:")
    stats = trace_stats(trace)
    for k, v in stats.items():
        print(f"   {k}: {v}")
    print()

    # 4. Decode trace
    print("4. Decoding trace:")
    decoded_stages = decode_trace(trace)
    print(f"   decoded {len(decoded_stages)} stages")
    for stage in decoded_stages:
        art = stage.get("artifact", {})
        prod = art.get("producer", {})
        print(f"   stage {stage['stage_index']}: seat={stage['seat']}, "
              f"producer.name={prod.get('name', '?')}, "
              f"refs={len(art.get('refs', []))}")
    print()

    # 5. Verify round-trip
    print("5. Verifying round-trip:")
    result = verify_trace(trace, chamber)
    print(f"   valid: {result['valid']}")
    print(f"   hash_match: {result['hash_match']}")
    print(f"   content_match: {result['content_match']}")
    assert result["valid"], f"FAILED: {result}"
    print("   PASSED")
    print()

    # 6. Tamper detection
    print("6. Tamper detection:")
    tampered = copy.deepcopy(trace)
    tampered["stages"][0]["seat"] = "TAMPERED"
    tamper_result = verify_trace(tampered, chamber)
    print(f"   tampered trace valid: {tamper_result['valid']}")
    print(f"   hash_match: {tamper_result['hash_match']}")
    print(f"   content_match: {tamper_result['content_match']}")
    assert not tamper_result["valid"], "FAILED: tamper not detected"
    print("   Tamper correctly detected")
    print()

    # 7. Show a $ref in the encoded trace
    print("7. Sample $ref in encoded trace:")
    for stage in trace["stages"]:
        art = stage.get("artifact", {})
        refs = art.get("refs", [])
        for ref in refs:
            if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
                print(f"   stage {stage['stage_index']} artifact.refs: {ref}")
                break
        summary = stage.get("summary")
        if isinstance(summary, dict):
            srefs = summary.get("source_refs", [])
            for ref in srefs:
                if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
                    print(f"   stage {stage['stage_index']} summary.source_refs: {ref}")
                    break

    print("\nAll Phase 4 scenarios passed.")
