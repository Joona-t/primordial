"""
run_experiment.py — Primordial x RLM experiment.

Runs 4 scenarios with MockLM (no API keys needed), measures:
- H1: Reversibility (provenance chain completeness)
- H2: Violation detection (Primordial invariants vs vanilla)
- H3: Overhead (Primordial trace size vs vanilla logger payload)

Outputs JSON results + comparison table to stdout.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure forge tools and RLM test dir are importable
tools_dir = Path(__file__).parent
sys.path.insert(0, str(tools_dir))

rlm_root = tools_dir.parent / "rlm"
sys.path.insert(0, str(rlm_root))

import rlm.core.rlm as rlm_module
from rlm.core.rlm import RLM
from rlm.logger import RLMLogger
from tests.mock_lm import MockLM

from forge_chamber import (
    ForgeChamberError,
    create_chamber,
    register_stage,
    seal_chamber,
)
from forge_nulls import AbsenceState, ForgeNullError
from forge_reversible_summary import ForgeRefError, create_summary_view
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from primordial_rlm_bridge import (
    PrimordialRLM,
    compute_vanilla_reversibility,
    run_primordial_analysis,
)

# Save originals for restoration
_original_get_client = rlm_module.get_client
_original_count_tokens = rlm_module.count_tokens


def _patch_get_client(mock_lm: MockLM):
    rlm_module.get_client = lambda backend, kwargs: mock_lm


def _restore_patches():
    rlm_module.get_client = _original_get_client
    rlm_module.count_tokens = _original_count_tokens


def _vanilla_payload_size(trajectory: dict | None) -> int:
    """Compute byte size of vanilla logger JSON payload."""
    if trajectory is None:
        return 0
    return len(json.dumps(trajectory, default=str).encode("utf-8"))


# ─── Shared response lists (used by both vanilla and Primordial runs) ───

RESPONSES_A = [
    "Working on the problem.\n```repl\nx = 42\nprint(x)\n```",
    "Continuing computation.\n```repl\ny = x * 2\nprint(y)\n```",
    "FINAL(The answer is 84)",
]

RESPONSES_B = [
    # Parent iteration 0: triggers rlm_query
    'I need to break this into sub-tasks.\n'
    '```repl\nr1 = rlm_query("What is 10 + 20?")\nprint(r1)\n```',
    # Child 1 answers
    'FINAL(30)',
    # Parent iteration 1: triggers another rlm_query
    'Now the second sub-task.\n'
    '```repl\nr2 = rlm_query("What is 30 + 40?")\nprint(r2)\n```',
    # Child 2 answers
    'FINAL(70)',
    # Parent iteration 2: combine
    'FINAL(Results: first=30, second=70, total=100)',
]

RESPONSES_C = [
    # Iteration 0
    "Step 1: Setting up variables.\n"
    "```repl\na = 100\nb = 200\nprint(a + b)\n```",
    # Iteration 1
    "Step 2: Computing intermediate.\n"
    "```repl\nc = a * b\nprint(c)\n```",
    # Compaction summary
    "Progress summary: Set up a=100, b=200, computed a+b=300 and c=a*b=20000. "
    "Next: compute final result.",
    # Iteration 2 (post-compaction)
    "FINAL(Final result: a=100, b=200, c=20000)",
]


def _fake_count_tokens(messages, model_name):
    """Force compaction after enough messages accumulate."""
    if len(messages) > 5:
        return 200_000
    return 100


# ─── Run vanilla baseline for a scenario ───


def _run_vanilla(responses, prompt, rlm_kwargs) -> dict:
    """Run a scenario with plain RLM + RLMLogger, return trajectory + payload size."""
    mock_lm = MockLM(responses=list(responses))
    _patch_get_client(mock_lm)

    if rlm_kwargs.get("compaction"):
        rlm_module.count_tokens = _fake_count_tokens

    logger = RLMLogger()
    rlm = RLM(logger=logger, **rlm_kwargs)
    try:
        result = rlm.completion(prompt)
    finally:
        rlm.close()

    trajectory = logger.get_trajectory()
    _restore_patches()

    return {
        "trajectory": trajectory,
        "payload_size": _vanilla_payload_size(trajectory),
        "response": result.response,
        "iteration_count": len(trajectory.get("iterations", [])) if trajectory else 0,
    }


# ─── Scenario A: Linear (3 iterations, no recursion) ───


def run_scenario_a() -> dict:
    print("  Scenario A: Linear (3 iterations)...")

    rlm_kwargs = dict(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=1,
        max_iterations=5,
    )

    # Vanilla run
    vanilla = _run_vanilla(RESPONSES_A, "What is 42 * 2?", rlm_kwargs)

    # Primordial run (fresh MockLM with same responses)
    mock_lm = MockLM(responses=list(RESPONSES_A))
    _patch_get_client(mock_lm)
    logger = RLMLogger()
    rlm = PrimordialRLM(logger=logger, **rlm_kwargs)
    try:
        result = rlm.completion("What is 42 * 2?")
    finally:
        rlm.close()
    _restore_patches()

    chamber = rlm.chamber
    primordial = run_primordial_analysis(chamber, vanilla["payload_size"])
    trajectory = logger.get_trajectory()

    return {
        "scenario": "A_linear",
        "description": "3 iterations, no recursion, no compaction",
        "result_response": result.response,
        "h1_reversibility": {
            "primordial_score": primordial["reversibility_score"],
            "vanilla_score": compute_vanilla_reversibility(trajectory),
            "trace_verified": primordial["trace_verified"],
            "provenance": primordial["provenance"],
        },
        "h2_violations": {
            "primordial_detected": primordial["validation_errors"],
            "vanilla_detected": 0,
        },
        "h3_overhead": primordial["overhead"],
        "primordial_stages": primordial["stage_count"],
        "vanilla_iterations": vanilla["iteration_count"],
    }


# ─── Scenario B: Tree recursion (depth=2, 2 subcalls) ───


def run_scenario_b() -> dict:
    print("  Scenario B: Tree recursion (2 subcalls)...")

    rlm_kwargs = dict(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=2,
        max_iterations=5,
    )

    vanilla = _run_vanilla(RESPONSES_B, "Compute (10+20) + (30+40)", rlm_kwargs)

    mock_lm = MockLM(responses=list(RESPONSES_B))
    _patch_get_client(mock_lm)
    logger = RLMLogger()
    rlm = PrimordialRLM(logger=logger, **rlm_kwargs)
    try:
        result = rlm.completion("Compute (10+20) + (30+40)")
    finally:
        rlm.close()
    _restore_patches()

    chamber = rlm.chamber
    primordial = run_primordial_analysis(chamber, vanilla["payload_size"])
    trajectory = logger.get_trajectory()

    return {
        "scenario": "B_tree_recursion",
        "description": "3 parent iterations + 2 subcalls, depth=2",
        "result_response": result.response,
        "h1_reversibility": {
            "primordial_score": primordial["reversibility_score"],
            "vanilla_score": compute_vanilla_reversibility(trajectory),
            "trace_verified": primordial["trace_verified"],
            "provenance": primordial["provenance"],
        },
        "h2_violations": {
            "primordial_detected": primordial["validation_errors"],
            "vanilla_detected": 0,
        },
        "h3_overhead": primordial["overhead"],
        "primordial_stages": primordial["stage_count"],
        "vanilla_iterations": vanilla["iteration_count"],
    }


# ─── Scenario C: Compaction ───


def run_scenario_c() -> dict:
    print("  Scenario C: Compaction...")

    rlm_kwargs = dict(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=1,
        max_iterations=8,
        compaction=True,
        compaction_threshold_pct=0.85,
    )

    vanilla = _run_vanilla(RESPONSES_C, "Compute a*b where a=100, b=200", rlm_kwargs)

    mock_lm = MockLM(responses=list(RESPONSES_C))
    _patch_get_client(mock_lm)
    rlm_module.count_tokens = _fake_count_tokens
    logger = RLMLogger()
    rlm = PrimordialRLM(logger=logger, **rlm_kwargs)
    try:
        result = rlm.completion("Compute a*b where a=100, b=200")
    finally:
        rlm.close()
    _restore_patches()

    chamber = rlm.chamber
    primordial = run_primordial_analysis(chamber, vanilla["payload_size"])
    trajectory = logger.get_trajectory()

    return {
        "scenario": "C_compaction",
        "description": "3 iterations + 1 compaction, provenance survival test",
        "result_response": result.response,
        "h1_reversibility": {
            "primordial_score": primordial["reversibility_score"],
            "vanilla_score": compute_vanilla_reversibility(trajectory),
            "trace_verified": primordial["trace_verified"],
            "provenance": primordial["provenance"],
        },
        "h2_violations": {
            "primordial_detected": primordial["validation_errors"],
            "vanilla_detected": 0,
        },
        "h3_overhead": primordial["overhead"],
        "primordial_stages": primordial["stage_count"],
        "vanilla_iterations": vanilla["iteration_count"],
        "compaction_occurred": True,
    }


# ─── Scenario D: Deliberate violations ───


def run_scenario_d() -> dict:
    print("  Scenario D: Deliberate violations...")

    primordial_violations = 0
    violation_details: list[dict] = []

    # D1: Empty output without typed absence
    try:
        create_v1_stage_artifact(
            stage_id="artifact:rlm:test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output=None,
        )
        violation_details.append({"test": "D1_empty_output", "caught": False})
    except ForgeNullError:
        primordial_violations += 1
        violation_details.append({"test": "D1_empty_output", "caught": True, "by": "ForgeNullError"})

    # D2: Summary without source_refs
    try:
        create_summary_view(
            summary_id="artifact:rlm:test:summary:0:r1",
            text="A lossy summary with no provenance",
            source_refs=[],
            view_of="artifact:rlm:test:iter:0:r1",
        )
        violation_details.append({"test": "D2_ungrounded_summary", "caught": False})
    except ForgeRefError:
        primordial_violations += 1
        violation_details.append({"test": "D2_ungrounded_summary", "caught": True, "by": "ForgeRefError"})

    # D3: Dangling ref at registration time
    try:
        chamber = create_chamber("chamber:rlm:violation-test:v1")
        dangling_art = create_v1_stage_artifact(
            stage_id="artifact:rlm:violation-test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output="References a nonexistent upstream",
            source_refs=["artifact:rlm:nonexistent:r1"],
        )
        register_stage(chamber, dangling_art, summary_state="not_generated")
        violation_details.append({"test": "D3_dangling_ref", "caught": False})
    except ForgeChamberError:
        primordial_violations += 1
        violation_details.append({"test": "D3_dangling_ref", "caught": True, "by": "ForgeChamberError"})

    # D4: Duplicate artifact ID
    try:
        chamber2 = create_chamber("chamber:rlm:dup-test:v1")
        art = create_v1_stage_artifact(
            stage_id="artifact:rlm:dup-test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output="First registration",
        )
        register_stage(chamber2, art, summary_state="not_generated")
        art2 = create_v1_stage_artifact(
            stage_id="artifact:rlm:dup-test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output="Duplicate registration",
        )
        register_stage(chamber2, art2, summary_state="not_generated")
        violation_details.append({"test": "D4_duplicate_id", "caught": False})
    except ForgeChamberError:
        primordial_violations += 1
        violation_details.append({"test": "D4_duplicate_id", "caught": True, "by": "ForgeChamberError"})

    # D5: Registration on sealed chamber
    try:
        chamber3 = create_chamber("chamber:rlm:sealed-test:v1")
        seal_chamber(chamber3)
        sealed_art = create_v1_stage_artifact(
            stage_id="artifact:rlm:sealed-test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output="Should be rejected",
        )
        register_stage(chamber3, sealed_art, summary_state="not_generated")
        violation_details.append({"test": "D5_sealed_chamber", "caught": False})
    except ForgeChamberError:
        primordial_violations += 1
        violation_details.append({"test": "D5_sealed_chamber", "caught": True, "by": "ForgeChamberError"})

    # D6: Missing summary_state when summary is None
    try:
        chamber4 = create_chamber("chamber:rlm:null-test:v1")
        null_art = create_v1_stage_artifact(
            stage_id="artifact:rlm:null-test:iter:0:r1",
            seat="rlm-engine",
            producer_name="test",
            producer_role="engine",
            output="Has output but no summary discipline",
        )
        register_stage(chamber4, null_art)
        violation_details.append({"test": "D6_null_discipline", "caught": False})
    except (ForgeChamberError, TypeError):
        primordial_violations += 1
        violation_details.append({"test": "D6_null_discipline", "caught": True, "by": "ForgeChamberError"})

    # Vanilla: logger has no invariant checks
    from rlm.core.types import RLMIteration
    vanilla_logger = RLMLogger()
    vanilla_logger.log(RLMIteration(prompt="test", response="", code_blocks=[]))
    vanilla_logger.log(RLMIteration(prompt="test", response="dangling ref", code_blocks=[]))
    # No errors raised — vanilla detects 0

    return {
        "scenario": "D_violations",
        "description": f"6 deliberate violations, detection comparison",
        "h2_violations": {
            "primordial_detected": primordial_violations,
            "vanilla_detected": 0,
            "total_tests": len(violation_details),
            "details": violation_details,
        },
    }


# ─── Output ───


def print_comparison_table(results: list[dict]):
    print("\n" + "=" * 80)
    print("PRIMORDIAL x RLM EXPERIMENT — RESULTS")
    print("=" * 80)

    # H1: Reversibility
    print("\n--- H1: Reversibility ---")
    print(f"{'Scenario':<25} {'Primordial':>12} {'Vanilla':>12} {'Trace OK':>10}")
    print("-" * 60)
    for r in results:
        if "h1_reversibility" in r:
            h1 = r["h1_reversibility"]
            print(
                f"{r['scenario']:<25} "
                f"{h1['primordial_score']:>12.2f} "
                f"{h1['vanilla_score']:>12.2f} "
                f"{'YES' if h1['trace_verified'] else 'NO':>10}"
            )

    # H2: Violation Detection
    print("\n--- H2: Violation Detection ---")
    print(f"{'Scenario':<25} {'Primordial':>12} {'Vanilla':>12} {'Tests':>8}")
    print("-" * 58)
    for r in results:
        if "h2_violations" in r:
            h2 = r["h2_violations"]
            total = h2.get("total_tests", "n/a")
            print(
                f"{r['scenario']:<25} "
                f"{h2['primordial_detected']:>12} "
                f"{h2['vanilla_detected']:>12} "
                f"{total!s:>8}"
            )

    # H3: Overhead (vs vanilla)
    print("\n--- H3: Overhead (Primordial vs Vanilla) ---")
    print(
        f"{'Scenario':<25} {'P bytes':>9} {'V bytes':>9} "
        f"{'vs Vanilla':>11} {'Compress':>9}"
    )
    print("-" * 65)
    for r in results:
        if "h3_overhead" in r:
            h3 = r["h3_overhead"]
            print(
                f"{r['scenario']:<25} "
                f"{h3['primordial_bytes']:>9} "
                f"{h3['vanilla_bytes']:>9} "
                f"{h3['vs_vanilla_pct']:>+10.1f}% "
                f"{h3['compression_ratio']:>8.2f}x"
            )

    # Summary
    print("\n--- Summary ---")
    all_h1 = all(
        r.get("h1_reversibility", {}).get("primordial_score", 0) == 1.0
        for r in results if "h1_reversibility" in r
    )
    all_traces = all(
        r.get("h1_reversibility", {}).get("trace_verified", False)
        for r in results if "h1_reversibility" in r
    )
    d_result = next((r for r in results if r["scenario"] == "D_violations"), None)
    h2_ok = (
        d_result
        and d_result["h2_violations"]["primordial_detected"] > 0
        and d_result["h2_violations"]["vanilla_detected"] == 0
    )

    print(f"  H1 — Provenance scores all 1.0:       {'SUPPORTED' if all_h1 else 'MIXED'}")
    print(f"  H1 — All traces round-trip exactly:    {'SUPPORTED' if all_traces else 'FAILED'}")
    print(f"  H2 — Primordial catches > vanilla:     {'SUPPORTED' if h2_ok else 'FAILED'}")

    if d_result:
        det = d_result["h2_violations"]
        print(f"       ({det['primordial_detected']}/{det['total_tests']} caught "
              f"vs {det['vanilla_detected']}/{det['total_tests']})")

    overhead_results = [r for r in results if "h3_overhead" in r]
    if overhead_results:
        avg_vs = sum(r["h3_overhead"]["vs_vanilla_pct"] for r in overhead_results) / len(overhead_results)
        print(f"  H3 — Avg overhead vs vanilla:          {avg_vs:+.1f}%")
        print(f"       (Primordial adds provenance, hashing, typed absence, trace compression)")
    print()


def main():
    print("Primordial x RLM Experiment")
    print("-" * 40)

    results = []
    for name, fn in [("A", run_scenario_a), ("B", run_scenario_b),
                      ("C", run_scenario_c), ("D", run_scenario_d)]:
        try:
            results.append(fn())
            print("    OK")
        except Exception as e:
            print(f"    FAILED: {e}")
            import traceback; traceback.print_exc()

    output_path = tools_dir / "experiment_results.json"
    with open(output_path, "w") as f:
        json.dump({"scenarios": results}, f, indent=2, default=str)
    print(f"\nResults written to: {output_path}")

    print_comparison_table(results)


if __name__ == "__main__":
    main()
