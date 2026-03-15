"""
forge_orchestrator.py — Drives multi-seat agent chambers.

Phase 5: One function (run_chamber) that iterates seats, calls agent fns,
wraps output in grammar structures, reacts to protocol codes (CRITIQUE
triggers revision, STOP halts, ERROR records failures), and produces
sealed+validated+compressed chambers.

Uses Phase 1-4 APIs unmodified.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from forge_chamber import (
    create_chamber,
    get_context_view,
    register_stage,
    seal_chamber,
    validate_chamber,
)
from forge_nulls import AbsenceState
from forge_stage_output import (
    create_v1_stage_artifact,
    create_v1_stage_summary,
    load_protocol_codes,
)
from forge_trace_codec import encode_trace, trace_stats, verify_trace


class ForgeOrchestratorError(Exception):
    """Orchestrator-level error."""


# --- Run ID generation ---

_run_counter = 499  # first call yields "run500"


def _generate_run_id() -> str:
    global _run_counter
    _run_counter += 1
    return f"run{_run_counter}"


# --- Policy defaults ---

_DEFAULT_POLICY = {
    "max_revisions": 3,
    "on_med_critique": "continue",
    "on_agent_error": "halt",
}


def _fill_policy_defaults(policy: dict | None) -> dict:
    if policy is None:
        return dict(_DEFAULT_POLICY)
    out = dict(_DEFAULT_POLICY)
    out.update(policy)
    return out


# --- CRITIQUE severity classification ---

_BLOCK_CRITIQUE_CODES = frozenset({
    "CRITIQUE.CRIT_SECURITY",
    "CRITIQUE.CRIT_PERMISSIONS",
    "CRITIQUE.CRIT_INVARIANT",
})

_MED_CRITIQUE_CODES = frozenset({
    "CRITIQUE.CRIT_SCHEMA",
    "CRITIQUE.CRIT_ARCHITECTURE",
    "CRITIQUE.CRIT_TESTING",
})


def _evaluate_critique_findings(findings: list[dict], policy: dict) -> str:
    """Return "revise" if findings warrant revision, else "continue"."""
    if not findings:
        return "continue"

    codes = load_protocol_codes()

    for f in findings:
        code = f.get("code", "")
        if code in _BLOCK_CRITIQUE_CODES:
            return "revise"

        entry = codes.get(code)
        if entry and entry.get("domain") == "CRITIQUE":
            severity = entry.get("severity", "")
            if severity == "block":
                return "revise"

    if policy.get("on_med_critique") == "revise":
        for f in findings:
            code = f.get("code", "")
            if code in _MED_CRITIQUE_CODES:
                return "revise"
            entry = codes.get(code)
            if entry and entry.get("domain") == "CRITIQUE" and entry.get("severity") == "med":
                return "revise"

    return "continue"


# --- Error handling ---

def _handle_agent_exception(exc: Exception, seat_name: str) -> dict:
    """Build an agent-result-shaped dict from an exception."""
    return {
        "output": None,
        "summary_text": None,
        "findings": [
            {"code": "ERROR.ERR_API_FAIL", "detail": f"{seat_name} raised {type(exc).__name__}: {exc}"},
        ],
        "stop_reason": None,
    }


# --- Stage registration helper ---

def _register_stage_from_result(
    chamber: dict,
    stage_id: str,
    spec: dict,
    agent_result: dict,
    source_refs: list[str],
    stop_reason_override: str | None = None,
) -> dict:
    """Create artifact+summary from agent result and register in chamber."""
    output = agent_result.get("output")
    findings = agent_result.get("findings")
    stop_reason = stop_reason_override or agent_result.get("stop_reason")

    output_state = AbsenceState.NOT_GENERATED if output is None else None

    artifact = create_v1_stage_artifact(
        stage_id=stage_id,
        seat=spec["name"],
        producer_name=spec["producer_name"],
        producer_role=spec["role"],
        output=output,
        output_state=output_state,
        source_refs=source_refs if source_refs else None,
        findings=findings,
        stop_reason=stop_reason,
    )

    summary = None
    summary_state = None
    summary_text = agent_result.get("summary_text")

    if output is not None:
        if not summary_text:
            summary_text = f"Output produced by {spec['name']}."
        extra_refs = source_refs if source_refs else None
        summary = create_v1_stage_summary(artifact, summary_text, extra_source_refs=extra_refs)
    else:
        summary_state = "not_generated"

    register_stage(chamber, artifact, summary, summary_state=summary_state)
    return artifact


# --- Revision target lookup ---

def _find_revision_target(seat_specs: list[dict], critic_idx: int) -> int | None:
    """Find the seat index before the critic in the original spec order."""
    if critic_idx <= 0:
        return None
    return critic_idx - 1


# --- Main orchestration ---

def run_chamber(
    seat_specs: list[dict],
    *,
    run_id: str | None = None,
    policy: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    """Run a multi-seat agent chamber.

    Creates chamber, iterates seats, calls agent fns, wraps output in
    grammar, registers stages, reacts to protocol codes, seals/validates/
    compresses. Returns RunResult.
    """
    if not seat_specs:
        raise ForgeOrchestratorError("seat_specs must not be empty")

    if run_id is None:
        run_id = _generate_run_id()
    policy = _fill_policy_defaults(policy)

    chamber_id = f"chamber:{run_id}:v1"
    chamber = create_chamber(chamber_id, metadata=metadata)

    seat_sequence = [s["name"] for s in seat_specs]
    actual_seat_sequence: list[str] = []
    revision_cycles = 0
    errors_list: list[dict] = []
    status = "complete"
    stop_reason_final = None
    stop_reason_state = "not_invoked"

    # Track revision numbers per seat
    revision_number: dict[str, int] = {}
    # Track revision feedback for revision targets
    revision_feedback: dict[str, list[dict] | None] = {}

    # Build exec queue with indices into original seat_specs
    exec_queue: deque[int] = deque(range(len(seat_specs)))

    while exec_queue:
        spec_idx = exec_queue.popleft()
        spec = seat_specs[spec_idx]
        seat_name = spec["name"]

        revision_number.setdefault(seat_name, 0)
        revision_number[seat_name] += 1
        rev = revision_number[seat_name]

        stage_id = f"artifact:{run_id}:stage:{seat_name}:r{rev}"
        actual_seat_sequence.append(seat_name)

        # 1. Context
        context = get_context_view(chamber, for_seat=seat_name)

        # 2. Build agent input
        agent_input = {
            "context_view": {
                "chamber_id": context["chamber_id"],
                "for_seat": context["for_seat"],
                "available_artifact_ids": sorted(context["available_artifact_ids"]),
                "stage_count": context["stage_count"],
            },
            "run_id": run_id,
            "seat_name": seat_name,
            "revision": rev,
            "revision_feedback": revision_feedback.pop(seat_name, None),
        }

        # 3. Call agent fn
        agent_result = None
        try:
            agent_result = spec["agent_fn"](agent_input)
            if agent_result is None:
                agent_result = {}
        except Exception as exc:
            agent_result = _handle_agent_exception(exc, seat_name)
            errors_list.append({
                "seat": seat_name,
                "revision": rev,
                "error": f"{type(exc).__name__}: {exc}",
            })

            # Build source refs
            source_refs = _build_source_refs(context, chamber_id)

            if policy["on_agent_error"] == "halt":
                _register_stage_from_result(
                    chamber, stage_id, spec, agent_result, source_refs,
                    stop_reason_override="STOP.STOP_ERROR",
                )
                status = "error"
                stop_reason_final = "STOP.STOP_ERROR"
                stop_reason_state = None
                break
            else:
                _register_stage_from_result(
                    chamber, stage_id, spec, agent_result, source_refs,
                )
                continue

        # 4. Check stop reason
        if agent_result.get("stop_reason"):
            source_refs = _build_source_refs(context, chamber_id)
            _register_stage_from_result(
                chamber, stage_id, spec, agent_result, source_refs,
            )
            status = "stopped"
            stop_reason_final = agent_result["stop_reason"]
            stop_reason_state = None
            break

        # 5. Source refs
        source_refs = _build_source_refs(context, chamber_id)

        # 6-8. Register stage
        _register_stage_from_result(
            chamber, stage_id, spec, agent_result, source_refs,
        )

        # 9. Critic revision check
        if spec.get("is_critic") and agent_result.get("findings"):
            decision = _evaluate_critique_findings(agent_result["findings"], policy)
            if decision == "revise":
                target_idx = _find_revision_target(seat_specs, spec_idx)
                if target_idx is not None:
                    revision_cycles += 1
                    if revision_cycles > policy["max_revisions"]:
                        status = "stopped"
                        stop_reason_final = "STOP.STOP_FORCED"
                        stop_reason_state = None
                        break

                    target_name = seat_specs[target_idx]["name"]
                    revision_feedback[target_name] = agent_result["findings"]
                    exec_queue.appendleft(spec_idx)       # critic again
                    exec_queue.appendleft(target_idx)     # target first
                    continue

    # Seal, validate, compress
    seal_chamber(chamber)
    validation_errors = validate_chamber(chamber)
    trace = encode_trace(chamber)
    verification = verify_trace(trace, chamber)

    return {
        "chamber": chamber,
        "trace": trace,
        "run_report": {
            "run_id": run_id,
            "status": status,
            "stop_reason": stop_reason_final,
            "stop_reason_state": stop_reason_state,
            "total_stages": len(chamber["stages"]),
            "revision_cycles": revision_cycles,
            "seat_sequence": seat_sequence,
            "actual_seat_sequence": actual_seat_sequence,
            "errors": errors_list,
            "chamber_validation": validation_errors,
            "trace_verification": verification,
        },
    }


def _build_source_refs(context: dict, chamber_id: str) -> list[str]:
    """Extract upstream artifact IDs from context, excluding chamber_id."""
    refs = sorted(context["available_artifact_ids"] - {chamber_id})
    return refs


# --- Mock agent functions for demo ---

def mock_architect(ctx: dict) -> dict:
    return {
        "output": "Build a schema validator with strict fail-closed defaults.",
        "summary_text": "Architect proposes strict fail-closed schema validator.",
        "findings": None,
        "stop_reason": None,
    }


def mock_builder(ctx: dict) -> dict:
    rev = ctx.get("revision", 1)
    if rev == 1:
        return {
            "output": "def validate(schema): return check(schema, strict=True)",
            "summary_text": "Builder implemented schema validation.",
            "findings": None,
            "stop_reason": None,
        }
    else:
        return {
            "output": "def validate(schema, max_size=1024): return check(schema, strict=True, max_size=max_size)",
            "summary_text": "Builder revised with size limit fix.",
            "findings": None,
            "stop_reason": None,
        }


def mock_critic_approve(ctx: dict) -> dict:
    return {
        "output": "Code looks correct. No blocking issues found.",
        "summary_text": "Critic approved with no blocking findings.",
        "findings": None,
        "stop_reason": None,
    }


def mock_critic_block_then_approve(ctx: dict) -> dict:
    rev = ctx.get("revision", 1)
    if rev == 1:
        return {
            "output": "Security concern: no input size limit.",
            "summary_text": "Critic found security issue.",
            "findings": [
                {"code": "CRITIQUE.CRIT_SECURITY", "detail": "No input size limit on schema"},
            ],
            "stop_reason": None,
        }
    else:
        return {
            "output": "Size limit added. Approved.",
            "summary_text": "Critic approved after revision.",
            "findings": None,
            "stop_reason": None,
        }


def mock_builder_crash(ctx: dict) -> dict:
    raise RuntimeError("API connection failed")


def mock_architect_stop(ctx: dict) -> dict:
    return {
        "output": "Consensus reached. No further work needed.",
        "summary_text": "Architect signals consensus.",
        "findings": None,
        "stop_reason": "STOP.STOP_CONSENSUS",
    }


# --- End-to-end demo ---

if __name__ == "__main__":
    print("=== forge_orchestrator.py — Phase 5 Orchestrator ===\n")

    # Reset counter for deterministic demo
    _run_counter = 499

    # Scenario 1: Happy path — 3 seats, no revisions
    print("1. Happy path — architect→builder→critic, no revisions:")
    result = run_chamber([
        {"name": "architect", "role": "architect", "agent_fn": mock_architect,
         "producer_name": "architect-agent", "is_critic": False},
        {"name": "builder", "role": "builder", "agent_fn": mock_builder,
         "producer_name": "builder-agent", "is_critic": False},
        {"name": "critic", "role": "critic", "agent_fn": mock_critic_approve,
         "producer_name": "critic-agent", "is_critic": True},
    ])
    rr = result["run_report"]
    print(f"   status: {rr['status']}")
    print(f"   total_stages: {rr['total_stages']}")
    print(f"   revision_cycles: {rr['revision_cycles']}")
    print(f"   actual_seat_sequence: {rr['actual_seat_sequence']}")
    print(f"   chamber_validation: {rr['chamber_validation']}")
    print(f"   trace_verification: {rr['trace_verification']['valid']}")
    stats = trace_stats(result["trace"])
    print(f"   trace compression: {stats['compression_ratio']}x, "
          f"{stats['shared_structures']} shared, {stats['ref_replacements']} refs")
    assert rr["status"] == "complete"
    assert rr["total_stages"] == 3
    assert rr["chamber_validation"] == []
    assert rr["trace_verification"]["valid"]
    print("   PASSED\n")

    # Scenario 2: Revision path — critic blocks, builder revises
    print("2. Revision path — CRIT_SECURITY triggers revision cycle:")
    result2 = run_chamber([
        {"name": "architect", "role": "architect", "agent_fn": mock_architect,
         "producer_name": "architect-agent", "is_critic": False},
        {"name": "builder", "role": "builder", "agent_fn": mock_builder,
         "producer_name": "builder-agent", "is_critic": False},
        {"name": "critic", "role": "critic", "agent_fn": mock_critic_block_then_approve,
         "producer_name": "critic-agent", "is_critic": True},
    ])
    rr2 = result2["run_report"]
    print(f"   status: {rr2['status']}")
    print(f"   total_stages: {rr2['total_stages']}")
    print(f"   revision_cycles: {rr2['revision_cycles']}")
    print(f"   actual_seat_sequence: {rr2['actual_seat_sequence']}")
    print(f"   chamber_validation: {rr2['chamber_validation']}")
    print(f"   trace_verification: {rr2['trace_verification']['valid']}")
    assert rr2["status"] == "complete"
    assert rr2["total_stages"] == 5
    assert rr2["revision_cycles"] == 1
    assert rr2["actual_seat_sequence"] == ["architect", "builder", "critic", "builder", "critic"]
    assert rr2["chamber_validation"] == []
    assert rr2["trace_verification"]["valid"]
    print("   PASSED\n")

    # Scenario 3: Error path — builder crashes, run halts
    print("3. Error path — builder raises exception, halt policy:")
    result3 = run_chamber([
        {"name": "architect", "role": "architect", "agent_fn": mock_architect,
         "producer_name": "architect-agent", "is_critic": False},
        {"name": "builder", "role": "builder", "agent_fn": mock_builder_crash,
         "producer_name": "builder-agent", "is_critic": False},
        {"name": "critic", "role": "critic", "agent_fn": mock_critic_approve,
         "producer_name": "critic-agent", "is_critic": True},
    ])
    rr3 = result3["run_report"]
    print(f"   status: {rr3['status']}")
    print(f"   total_stages: {rr3['total_stages']}")
    print(f"   errors: {rr3['errors']}")
    print(f"   stop_reason: {rr3['stop_reason']}")
    print(f"   chamber_validation: {rr3['chamber_validation']}")
    assert rr3["status"] == "error"
    assert rr3["total_stages"] == 2  # architect + error builder
    assert len(rr3["errors"]) == 1
    assert rr3["stop_reason"] == "STOP.STOP_ERROR"
    assert rr3["chamber_validation"] == []
    print("   PASSED\n")

    # Scenario 4: Stop path — architect returns STOP_CONSENSUS
    print("4. Stop path — architect signals STOP_CONSENSUS:")
    result4 = run_chamber([
        {"name": "architect", "role": "architect", "agent_fn": mock_architect_stop,
         "producer_name": "architect-agent", "is_critic": False},
        {"name": "builder", "role": "builder", "agent_fn": mock_builder,
         "producer_name": "builder-agent", "is_critic": False},
    ])
    rr4 = result4["run_report"]
    print(f"   status: {rr4['status']}")
    print(f"   total_stages: {rr4['total_stages']}")
    print(f"   stop_reason: {rr4['stop_reason']}")
    print(f"   chamber_validation: {rr4['chamber_validation']}")
    assert rr4["status"] == "stopped"
    assert rr4["total_stages"] == 1
    assert rr4["stop_reason"] == "STOP.STOP_CONSENSUS"
    assert rr4["chamber_validation"] == []
    print("   PASSED\n")

    print("All Phase 5 scenarios passed.")
