"""
forge_nulls.py — Typed absence enforcement for The Forge.

No empty string, empty dict, or empty list passes validation without
an explicit absence state. Ambiguity is a protocol violation.

v1 convergence:
- v1 canonical output uses `state` (not `absence_state`)
- PRUNED_RECOVERABLE is canonical; PRUNED is a deprecated alias
- legacy standalone {"value": null, "absence_state": ...} is tolerated at ingress
"""

from __future__ import annotations

import warnings
from enum import Enum
from typing import Any


# v1 canonical absence states
V1_ABSENCE_STATES = frozenset({
    "not_generated",
    "not_invoked",
    "unknown",
    "withheld",
    "invalid",
    "deleted",
    "pruned_recoverable",
    "unresolved",
})

# Legacy state values accepted during normalization
_LEGACY_ALIASES = {
    "pruned": "pruned_recoverable",
}


class AbsenceState(str, Enum):
    UNKNOWN = "unknown"
    NOT_GENERATED = "not_generated"
    NOT_INVOKED = "not_invoked"
    INVALID = "invalid"
    WITHHELD = "withheld"
    PRUNED_RECOVERABLE = "pruned_recoverable"
    DELETED = "deleted"
    UNRESOLVED = "unresolved"

    # Deprecated alias — use PRUNED_RECOVERABLE instead
    PRUNED = "pruned"


# ---------------------------------------------------------------------------
# State transition table — 8x8 (64 entries)
#
# Classification:
#   True  = legal (a realistic agent event can cause this transition)
#   False = illegal (no valid agent event should cause this)
#
# Design rules:
#   1. not_invoked and not_generated are INITIAL states — nothing transitions
#      INTO them (except self-transitions, which are idempotent).
#   2. deleted is a TERMINAL state — nothing transitions OUT of it (except
#      self-transition, which is idempotent re-confirmation).
#   3. Self-transitions are legal for all states (idempotent re-evaluation).
#   4. All other transitions from non-terminal states to non-initial states
#      are legal, reflecting valid agent lifecycle events:
#        - Recovery / retry: not_generated -> unknown (retry produced unclear result)
#        - Compaction: any active state -> pruned_recoverable
#        - Cleanup: any active state -> deleted
#        - Investigation: unknown -> unresolved (started looking into it)
#        - Resolution: unresolved -> withheld (resolved by withholding)
#        - Degradation: pruned_recoverable -> unknown (recovery failed)
#        - etc.
#
# Ref states (resolved/unresolved for source_ref links) are orthogonal to
# absence states and NOT part of this table.
# ---------------------------------------------------------------------------

# Initial states: nothing transitions INTO these (column all-False except self)
_INITIAL_STATES = frozenset({"not_invoked", "not_generated"})

# Terminal states: nothing transitions OUT of these (row all-False except self)
_TERMINAL_STATES = frozenset({"deleted"})


def _build_transition_table() -> dict[tuple[str, str], bool]:
    """Build the complete 64-entry transition table.

    The table is constructed programmatically from the three structural rules
    (initial, terminal, self-transition) so that it is manifestly complete and
    consistent.  Every entry is explicit — there are no implicit defaults.
    """
    table: dict[tuple[str, str], bool] = {}
    states = sorted(V1_ABSENCE_STATES)  # deterministic order

    for src in states:
        for tgt in states:
            if src == tgt:
                # Rule 3: self-transitions always legal
                table[(src, tgt)] = True
            elif tgt in _INITIAL_STATES:
                # Rule 1: cannot transition INTO an initial state
                table[(src, tgt)] = False
            elif src in _TERMINAL_STATES:
                # Rule 2: cannot transition OUT of a terminal state
                table[(src, tgt)] = False
            else:
                # Rule 4: all other transitions are legal
                table[(src, tgt)] = True

    return table


TRANSITION_TABLE: dict[tuple[str, str], bool] = _build_transition_table()


def validate_transition(from_state: str, to_state: str) -> bool:
    """Check if a state transition is legal.

    Args:
        from_state: Current absence state (must be in V1_ABSENCE_STATES).
        to_state:   Target absence state (must be in V1_ABSENCE_STATES).

    Returns:
        True if the transition is legal, False if illegal.

    Raises:
        ValueError: If either state is not in V1_ABSENCE_STATES.
    """
    if from_state not in V1_ABSENCE_STATES:
        raise ValueError(
            f"Unknown from_state: {from_state!r}. "
            f"Valid absence states: {sorted(V1_ABSENCE_STATES)}"
        )
    if to_state not in V1_ABSENCE_STATES:
        raise ValueError(
            f"Unknown to_state: {to_state!r}. "
            f"Valid absence states: {sorted(V1_ABSENCE_STATES)}"
        )
    return TRANSITION_TABLE[(from_state, to_state)]


class ForgeNullError(Exception):
    """Raised when an ambiguous empty value is encountered."""


def normalize_absence_state(state: str) -> str:
    """Normalize an absence state string to v1 canonical form.

    Maps legacy aliases (e.g. 'pruned' -> 'pruned_recoverable').
    Raises ValueError if the state is not recognized.
    """
    if state in V1_ABSENCE_STATES:
        return state
    if state in _LEGACY_ALIASES:
        canonical = _LEGACY_ALIASES[state]
        warnings.warn(
            f"Absence state '{state}' is deprecated, use '{canonical}'",
            DeprecationWarning,
            stacklevel=2,
        )
        return canonical
    raise ValueError(f"Unknown absence state: {state!r}. Valid: {V1_ABSENCE_STATES}")


def normalize_absent_object(value: dict, warn_on_legacy: bool = True) -> dict:
    """Normalize a standalone absent object to canonical v1 shape.

    Canonical shape:
      {"value": None, "state": "<AbsenceState>", ...}

    Legacy ingress shape accepted:
      {"value": None, "absence_state": "<AbsenceState>", ...}
    """
    if not isinstance(value, dict):
        raise ForgeNullError(f"Expected absent object dict, got {type(value).__name__}")

    out = dict(value)

    if out.get("value") is not None:
        raise ForgeNullError("Absent object must have value=None")

    if "state" in out:
        out["state"] = normalize_absence_state(out["state"])
        out.pop("absence_state", None)
        return out

    if "absence_state" in out:
        if warn_on_legacy:
            warnings.warn(
                "Legacy absent object uses 'absence_state'; normalize to 'state'",
                DeprecationWarning,
                stacklevel=2,
            )
        out["state"] = normalize_absence_state(out.pop("absence_state"))
        return out

    raise ForgeNullError("Absent object missing 'state' (or legacy 'absence_state')")


def absent(
    state: AbsenceState | str,
    reason: str | None = None,
    *,
    mode: str = "v1",
) -> dict:
    """Create a properly typed absent field.

    Default output is v1 canonical (`state`).
    Use mode='legacy' only for compatibility wrappers at legacy ingress boundaries.
    Removal gate for mode='legacy': explicit deprecation window plus confirmed
    zero external callers.
    """
    raw_state = state.value if isinstance(state, AbsenceState) else str(state)
    canonical = normalize_absence_state(raw_state)

    if mode not in {"v1", "legacy"}:
        raise ValueError("mode must be 'v1' or 'legacy'")

    if mode == "legacy":
        from forge_v1_bridge import record_legacy_usage

        record_legacy_usage(
            "absent.mode_legacy",
            detail=f"state={canonical}",
            stacklevel=2,
        )
        result = {"value": None, "absence_state": canonical}
    else:
        result = {"value": None, "state": canonical}

    if reason is not None:
        result["reason"] = reason
    return result


def is_absent(value: Any) -> bool:
    """Check if a value represents typed absence (v1 or legacy)."""
    if not isinstance(value, dict):
        return False
    if value.get("value") is not None:
        return False
    if "state" in value:
        try:
            normalize_absence_state(value["state"])
            return True
        except Exception:
            return False
    if "absence_state" in value:
        try:
            normalize_absence_state(value["absence_state"])
            return True
        except Exception:
            return False
    return False


def _is_ambiguous_empty(value: Any) -> bool:
    """Check if a value is an ambiguous empty (untyped null/empty)."""
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def validate_field(key: str, value: Any) -> Any:
    """Validate a single field value.

    Raises ForgeNullError if value is an ambiguous empty without typed state.
    Returns value unchanged if valid.
    """
    if is_absent(value):
        # Ingress compatibility: accept legacy absent object.
        # Keep object unchanged here; normalization is available via normalize_record().
        return value

    if _is_ambiguous_empty(value):
        raise ForgeNullError(
            f"Ambiguous empty value for field '{key}': {value!r}. "
            f"Use absent(AbsenceState.XXX) or add a '{key}_state' sibling field."
        )

    return value


# Keys where an empty list/collection is semantically valid (not absent).
# Matches v1 spec: refs and source_refs are legitimate empty collections.
V1_REF_CONTAINER_KEYS = frozenset({"refs", "source_refs"})


def validate_record(record: dict, exempt_keys: frozenset[str] | None = None) -> dict:
    """Validate all fields in a record dict.

    For each field, if the value is None/empty, checks for a sibling
    '{key}_state' field that provides the typed absence state.
    Keys in exempt_keys (default: V1_REF_CONTAINER_KEYS) are skipped
    when they contain empty lists — per v1, empty refs is valid.

    Legacy standalone absent objects are tolerated at ingress.
    """
    if exempt_keys is None:
        exempt_keys = V1_REF_CONTAINER_KEYS

    if not isinstance(record, dict):
        raise ForgeNullError(f"Expected dict, got {type(record).__name__}")

    for key, value in record.items():
        if key.endswith("_state"):
            # Validate sibling state values directly
            if isinstance(value, str):
                normalize_absence_state(value)
            continue

        if key in exempt_keys and isinstance(value, list):
            continue

        if is_absent(value):
            # Legacy ingress tolerated; canonicalize only via normalize_record().
            normalize_absent_object(value, warn_on_legacy=False)
            continue

        if _is_ambiguous_empty(value):
            state_key = f"{key}_state"
            if state_key in record:
                state_val = record[state_key]
                # Accept both v1 canonical and legacy aliases
                valid_states = V1_ABSENCE_STATES | set(_LEGACY_ALIASES.keys())
                if state_val not in valid_states:
                    raise ForgeNullError(
                        f"Field '{key}' is empty and '{state_key}' has invalid "
                        f"absence state: {state_val!r}. Valid: {V1_ABSENCE_STATES}"
                    )
            else:
                raise ForgeNullError(
                    f"Ambiguous empty value for field '{key}': {value!r}. "
                    f"Add a '{state_key}' field with a valid AbsenceState value."
                )

    return record


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        if is_absent(value):
            return normalize_absent_object(value, warn_on_legacy=False)
        out = {}
        for k, v in value.items():
            if k.endswith("_state") and isinstance(v, str):
                out[k] = normalize_absence_state(v)
            else:
                out[k] = _normalize_value(v)
        return out
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    return value


def normalize_record(record: dict) -> dict:
    """Normalize a record to v1 canonical form.

    Rewrites any legacy absence state values (e.g. 'pruned' -> 'pruned_recoverable')
    in sibling _state fields and legacy standalone absent objects.
    Returns a new dict.
    """
    if not isinstance(record, dict):
        raise ForgeNullError(f"Expected dict, got {type(record).__name__}")
    return _normalize_value(record)


if __name__ == "__main__":
    print("=== forge_nulls.py — Typed Absence Enforcement (v1-aligned) ===\n")

    # 1. Create typed absent values (canonical v1)
    print("1. Creating canonical absent values:")
    a = absent(AbsenceState.NOT_GENERATED, "LLM did not produce output")
    print(f"   absent(NOT_GENERATED): {a}")
    print(f"   is_absent: {is_absent(a)}\n")

    # 2. PRUNED_RECOVERABLE is canonical
    print("2. PRUNED_RECOVERABLE is canonical:")
    a2 = absent(AbsenceState.PRUNED_RECOVERABLE, "compressed during context window reduction")
    print(f"   absent(PRUNED_RECOVERABLE): {a2}\n")

    # 3. Ingress compatibility: legacy absent object normalized to canonical v1
    print("3. Normalizing legacy ingress absent object:")
    legacy_record = {"data": {"value": None, "absence_state": "pruned"}}
    normalized = normalize_record(legacy_record)
    print(f"   Before: {legacy_record}")
    print(f"   After:  {normalized}\n")

    # 4. Canonical typed-empty record validates cleanly
    print("4. Validating canonical typed-empty record:")
    canonical_record = {
        "output": None,
        "output_state": "not_generated",
        "findings": None,
        "findings_state": "not_invoked",
    }
    validate_record(canonical_record)
    print("   PASSED\n")

    # 5. Reject ambiguous empties
    print("5. Rejecting ambiguous empties:")
    bad_cases = [
        ("empty string", {"name": ""}),
        ("empty dict", {"config": {}}),
        ("empty list", {"items": []}),
        ("bare None", {"output": None}),
    ]
    for label, bad_record in bad_cases:
        try:
            validate_record(bad_record)
            print(f"   UNEXPECTED PASS: {label}")
        except ForgeNullError as e:
            print(f"   Rejected {label}: {e}")

    print("\nAll checks passed.")
