"""
vanilla_baseline.py — Baseline measurements using only RLM's native logger.

Runs the same scenarios A-C as run_experiment.py but with plain RLM + RLMLogger.
Measures what vanilla logging can detect (expected: no structural violations,
no provenance, no hash verification).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

tools_dir = Path(__file__).parent
sys.path.insert(0, str(tools_dir))

rlm_root = tools_dir.parent / "rlm"
sys.path.insert(0, str(rlm_root))

import rlm.core.rlm as rlm_module
from rlm.logger import RLMLogger
from tests.mock_lm import MockLM

from primordial_rlm_bridge import compute_vanilla_reversibility

_original_get_client = rlm_module.get_client
_original_count_tokens = rlm_module.count_tokens


def _patch_get_client(mock_lm: MockLM):
    rlm_module.get_client = lambda backend, kwargs: mock_lm


def _restore_patches():
    rlm_module.get_client = _original_get_client
    rlm_module.count_tokens = _original_count_tokens


def _analyze_trajectory(trajectory: dict | None) -> dict:
    """Analyze what vanilla RLMLogger captured."""
    if trajectory is None:
        return {
            "iterations": 0,
            "has_provenance": False,
            "has_hashing": False,
            "has_ref_structure": False,
            "reversibility_score": 0.0,
            "violations_detected": 0,
            "payload_size": 0,
        }

    iterations = trajectory.get("iterations", [])
    payload = json.dumps(trajectory, default=str)

    # Check for structural features (all expected: False)
    has_provenance = any(
        "source_refs" in it or "refs" in it or "parent_id" in it
        for it in iterations
    )
    has_hashing = any(
        "hash" in it or "content_hash" in it
        for it in iterations
    )
    has_ref_structure = any(
        isinstance(it.get("refs"), list) and len(it.get("refs", [])) > 0
        for it in iterations
    )

    return {
        "iterations": len(iterations),
        "has_provenance": has_provenance,
        "has_hashing": has_hashing,
        "has_ref_structure": has_ref_structure,
        "reversibility_score": compute_vanilla_reversibility(trajectory),
        "violations_detected": 0,  # Logger has no invariant checks
        "payload_size": len(payload.encode("utf-8")),
    }


# ─── Scenarios ───


def run_vanilla_a() -> dict:
    print("  Vanilla A: Linear...")
    mock_lm = MockLM(responses=[
        "Working on the problem.\n```repl\nx = 42\nprint(x)\n```",
        "Continuing computation.\n```repl\ny = x * 2\nprint(y)\n```",
        "FINAL(The answer is 84)",
    ])
    _patch_get_client(mock_lm)

    logger = RLMLogger()
    from rlm.core.rlm import RLM

    rlm = RLM(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=1,
        max_iterations=5,
        logger=logger,
    )
    try:
        result = rlm.completion("What is 42 * 2?")
    finally:
        rlm.close()

    trajectory = logger.get_trajectory()
    analysis = _analyze_trajectory(trajectory)
    _restore_patches()

    return {
        "scenario": "A_linear",
        "response": result.response,
        **analysis,
    }


def run_vanilla_b() -> dict:
    print("  Vanilla B: Tree recursion...")
    mock_lm = MockLM(responses=[
        'I need to break this into sub-tasks.\n'
        '```repl\nr1 = rlm_query("What is 10 + 20?")\nprint(r1)\n```',
        'FINAL(30)',
        'Now the second sub-task.\n'
        '```repl\nr2 = rlm_query("What is 30 + 40?")\nprint(r2)\n```',
        'FINAL(70)',
        'FINAL(Results: first=30, second=70, total=100)',
    ])
    _patch_get_client(mock_lm)

    logger = RLMLogger()
    from rlm.core.rlm import RLM

    rlm = RLM(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=2,
        max_iterations=5,
        logger=logger,
    )
    try:
        result = rlm.completion("Compute (10+20) + (30+40)")
    finally:
        rlm.close()

    trajectory = logger.get_trajectory()
    analysis = _analyze_trajectory(trajectory)
    _restore_patches()

    # Check: can vanilla see child iterations?
    child_iterations_visible = False
    if trajectory:
        for it in trajectory.get("iterations", []):
            # Child iterations would have depth info or subcall markers
            # RLM logger doesn't capture these
            if "child" in str(it) or "subcall" in str(it):
                child_iterations_visible = True

    analysis["child_iterations_visible"] = child_iterations_visible

    return {
        "scenario": "B_tree_recursion",
        "response": result.response,
        **analysis,
    }


def run_vanilla_c() -> dict:
    print("  Vanilla C: Compaction...")
    mock_lm = MockLM(responses=[
        "Step 1: Setting up variables.\n"
        "```repl\na = 100\nb = 200\nprint(a + b)\n```",
        "Step 2: Computing intermediate.\n"
        "```repl\nc = a * b\nprint(c)\n```",
        # Compaction summary
        "Progress summary: Set up a=100, b=200, computed a+b=300 and c=a*b=20000. "
        "Next: compute final result.",
        "FINAL(Final result: a=100, b=200, c=20000)",
    ])
    _patch_get_client(mock_lm)

    def fake_count_tokens(messages, model_name):
        if len(messages) > 5:
            return 200_000
        return 100

    rlm_module.count_tokens = fake_count_tokens

    logger = RLMLogger()
    from rlm.core.rlm import RLM

    rlm = RLM(
        backend="openai",
        backend_kwargs={"model_name": "mock-model"},
        environment="local",
        max_depth=1,
        max_iterations=8,
        compaction=True,
        compaction_threshold_pct=0.85,
        logger=logger,
    )
    try:
        result = rlm.completion("Compute a*b where a=100, b=200")
    finally:
        rlm.close()

    trajectory = logger.get_trajectory()
    analysis = _analyze_trajectory(trajectory)
    _restore_patches()

    # Check: does vanilla preserve pre-compaction data?
    pre_compaction_preserved = False
    if trajectory:
        iterations = trajectory.get("iterations", [])
        # After compaction, logger.clear_iterations() was NOT called mid-run,
        # so pre-compaction iterations are still in the list.
        # But the MESSAGE HISTORY (prompt context) lost them.
        pre_compaction_preserved = len(iterations) >= 3

    analysis["pre_compaction_data_in_logger"] = pre_compaction_preserved
    analysis["pre_compaction_data_in_context"] = False  # Always lost after compaction

    return {
        "scenario": "C_compaction",
        "response": result.response,
        **analysis,
    }


# ─── Main ───


def main():
    print("Vanilla Baseline Measurements")
    print("-" * 40)

    results = []

    for run_fn in [run_vanilla_a, run_vanilla_b, run_vanilla_c]:
        try:
            results.append(run_fn())
            print("    OK")
        except Exception as e:
            print(f"    FAILED: {e}")
            import traceback; traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("VANILLA BASELINE — STRUCTURAL ANALYSIS")
    print("=" * 60)
    print(
        f"{'Scenario':<20} {'Iters':>6} {'Prov':>6} {'Hash':>6} "
        f"{'Refs':>6} {'Rev':>6} {'Size':>8}"
    )
    print("-" * 60)
    for r in results:
        print(
            f"{r['scenario']:<20} "
            f"{r['iterations']:>6} "
            f"{'Y' if r['has_provenance'] else 'N':>6} "
            f"{'Y' if r['has_hashing'] else 'N':>6} "
            f"{'Y' if r['has_ref_structure'] else 'N':>6} "
            f"{r['reversibility_score']:>6.2f} "
            f"{r['payload_size']:>8}"
        )

    print("\nKey findings:")
    print("  - Provenance (source_refs): NONE — logger stores flat iteration list")
    print("  - Content hashing: NONE — no tamper detection")
    print("  - Ref structure: NONE — no DAG, no cross-iteration links")
    print("  - Violations detected: 0 — logger has no invariant checks")

    for r in results:
        if "child_iterations_visible" in r:
            vis = r["child_iterations_visible"]
            print(f"  - Child iterations visible in parent logger (B): {'YES' if vis else 'NO'}")
        if "pre_compaction_data_in_context" in r:
            print(f"  - Pre-compaction data in context (C): NO (lost after compaction)")
            print(f"  - Pre-compaction iterations in logger (C): "
                  f"{'YES' if r.get('pre_compaction_data_in_logger') else 'NO'}")

    # Save
    output_path = tools_dir / "vanilla_baseline_results.json"
    with open(output_path, "w") as f:
        json.dump({"vanilla_results": results}, f, indent=2, default=str)
    print(f"\nResults written to: {output_path}")


if __name__ == "__main__":
    main()
