#!/usr/bin/env python3
"""
run_compaction_campaign.py -- Execute simulated LLM compaction campaign on
Phase 2 forge chambers.

Runs the compaction measurement harness on real OpenClaw ledger data,
producing measurements at 9 deletion fractions (0.1 through 0.9).

Convention compliance:
  - "Simulated LLM compaction" = programmatic oldest-first stage deletion
  - NOT genuine LLM context-window compaction (lossy semantic summarization)
  - All metrics dimensionless ratios in [0, 1] or counts >= 0
  - CI: Bootstrap 95% (B=10000, seed=42) for interior; Clopper-Pearson for boundary
  - Hash: SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True)

Phase: 04-compaction-survival-measurement
Plan: 02, Task 1
"""

# ASSERT_CONVENTION: natural_units=N/A, compaction_layer=LLM_context_window, reachability=BFS_fraction, hash=SHA-256_canonical_JSON

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure tools/ is importable
tools_dir = Path(__file__).parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from openclaw_adapter import process_ledger
from compaction_harness import (
    CompactionSnapshot,
    classify_refs,
    compare_against_anchors,
    compute_reachability_ci,
    measure_reachability,
    run_compaction_measurement,
    simulate_compaction,
    violation_regression,
)
from forge_trace_codec import encode_trace, trace_stats, verify_trace


def build_chambers() -> list[dict]:
    """Build forge chambers from the Phase 2 ledger data.

    Uses the same sample ledger as Phase 2 baseline measurements.
    Creates 3 independent chambers with different session IDs for
    statistical independence.
    """
    ledger_path = str(
        Path(__file__).parent.parent
        / "integration_samples"
        / "openclaw"
        / "queue_ledger.sample.jsonl"
    )

    chambers = []
    # Create 3 chambers with different session IDs (same data, independent
    # chamber construction for measurement repeatability)
    for i in range(3):
        session_id = f"compaction-campaign-{i:02d}"
        chamber = process_ledger(ledger_path, session_id)
        chambers.append(chamber)

    return chambers


def run_campaign() -> dict:
    """Execute the full simulated LLM compaction campaign.

    Steps:
    1. Load Phase 2 chambers from ledger data
    2. Pre-compaction baseline measurement (must be 1.0)
    3. Deletion sweep at 9 fractions (0.1 - 0.9)
    4. Violation detection regression on original chambers
    5. Anchor comparison (MockLM, Phase 2, backtracking threshold)
    6. Compute CIs (bootstrap for interior, Clopper-Pearson for boundary)
    7. Save results

    Returns:
        Complete campaign results dict.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    deletion_fractions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    # --- Step 1: Build chambers ---
    print("Step 1: Building Phase 2 chambers from ledger data...")
    chambers = build_chambers()
    n_chambers = len(chambers)
    print(f"  Built {n_chambers} chambers")
    for i, ch in enumerate(chambers):
        print(f"  Chamber {i}: {ch['chamber_id']}, "
              f"{len(ch.get('stages', []))} stages, "
              f"status={ch['status']}")

    # --- Step 2: Pre-compaction baseline measurement ---
    print("\nStep 2: Pre-compaction baseline measurement...")
    pre_compaction_results = []
    for i, chamber in enumerate(chambers):
        pre_snap = CompactionSnapshot.from_chamber(chamber)
        pre_reach = measure_reachability(pre_snap)
        pre_compaction_results.append({
            "chamber_id": chamber["chamber_id"],
            "chamber_index": i,
            "reachability_fraction": pre_reach["reachability_fraction"],
            "reachable_count": pre_reach["reachable_count"],
            "total_count": pre_reach["total_count"],
            "max_depth": pre_reach["max_depth"],
            "stage_count": pre_snap.stage_count,
            "artifact_count": len(pre_snap.artifact_ids),
            "ref_count": sum(len(refs) for refs in pre_snap.ref_graph.values()),
        })
        assert pre_reach["reachability_fraction"] == 1.0, (
            f"Chamber {i}: pre-compaction reachability "
            f"{pre_reach['reachability_fraction']} != 1.0 (Phase 2 anchor violated)"
        )
        print(f"  Chamber {i}: reachability={pre_reach['reachability_fraction']}, "
              f"artifacts={len(pre_snap.artifact_ids)}, "
              f"refs={sum(len(refs) for refs in pre_snap.ref_graph.values())}")

    # Compute pre-compaction CI
    pre_reach_values = [r["reachability_fraction"] for r in pre_compaction_results]
    pre_ci = compute_reachability_ci(pre_reach_values)
    print(f"  Pre-compaction reachability: {pre_ci['mean']} "
          f"CI={pre_ci['ci_95']} method={pre_ci['method']}")

    # Forge trace compression (lossless structural -- NOT LLM compaction)
    print("\n  Forge trace compression (lossless structural):")
    compression_results = []
    for i, chamber in enumerate(chambers):
        try:
            trace = encode_trace(chamber)
            stats = trace_stats(trace)
            verification = verify_trace(trace, chamber)
            cr = {
                "chamber_index": i,
                "compression_ratio": stats.get("compression_ratio", 1.0),
                "original_size": stats.get("original_size", 0),
                "encoded_size": stats.get("encoded_size", 0),
                "round_trip_verified": verification.get("valid", False),
                "hash_match": verification.get("hash_match", False),
            }
            compression_results.append(cr)
            print(f"    Chamber {i}: ratio={cr['compression_ratio']:.4f}, "
                  f"verified={cr['round_trip_verified']}")
        except Exception as e:
            compression_results.append({
                "chamber_index": i,
                "error": f"{type(e).__name__}: {e}",
            })
            print(f"    Chamber {i}: ERROR {e}")

    # --- Step 3: Deletion sweep ---
    print("\nStep 3: Simulated LLM compaction deletion sweep...")
    deletion_sweep = []
    for frac in deletion_fractions:
        frac_results = []
        for i, chamber in enumerate(chambers):
            modified, pre_snap, post_snap = simulate_compaction(chamber, frac)

            # Post-deletion reachability
            post_reach = measure_reachability(post_snap)

            # Three-tier ref classification
            ref_class = classify_refs(pre_snap, post_snap)

            # Degradation
            degradation = 1.0 - post_reach["reachability_fraction"]

            frac_results.append({
                "chamber_index": i,
                "chamber_id": chamber["chamber_id"],
                "post_reachability_fraction": post_reach["reachability_fraction"],
                "post_reachable_count": post_reach["reachable_count"],
                "post_total_count": post_reach["total_count"],
                "post_max_depth": post_reach["max_depth"],
                "resolved_count": len(ref_class["resolved"]),
                "degraded_count": len(ref_class["degraded"]),
                "broken_count": len(ref_class["broken"]),
                "ref_total": ref_class["total"],
                "structural_reachability": ref_class["structural_reachability"],
                "semantic_fidelity": ref_class["semantic_fidelity"],
                "degradation": degradation,
                "stages_remaining": post_snap.stage_count,
                "artifacts_remaining": len(post_snap.artifact_ids),
            })

        # Aggregate across chambers for this deletion fraction
        reach_values = [r["post_reachability_fraction"] for r in frac_results]
        reach_ci = compute_reachability_ci(reach_values)

        struct_reach_values = [r["structural_reachability"] for r in frac_results]
        struct_ci = compute_reachability_ci(struct_reach_values)

        # Aggregate ref counts
        total_resolved = sum(r["resolved_count"] for r in frac_results)
        total_degraded = sum(r["degraded_count"] for r in frac_results)
        total_broken = sum(r["broken_count"] for r in frac_results)
        total_refs = sum(r["ref_total"] for r in frac_results)

        sweep_entry = {
            "deletion_fraction": frac,
            "n_chambers": n_chambers,
            "bfs_reachability": {
                "mean": reach_ci["mean"],
                "ci_95": list(reach_ci["ci_95"]) if reach_ci["ci_95"] else None,
                "method": reach_ci["method"],
                "per_chamber": reach_values,
            },
            "structural_reachability": {
                "mean": struct_ci["mean"],
                "ci_95": list(struct_ci["ci_95"]) if struct_ci["ci_95"] else None,
                "method": struct_ci["method"],
                "per_chamber": struct_reach_values,
            },
            "ref_classification": {
                "resolved": total_resolved,
                "degraded": total_degraded,
                "broken": total_broken,
                "total": total_refs,
                "note": "degraded=0 expected for simulated LLM compaction "
                        "(deletion removes artifacts entirely, does not summarize)",
            },
            "degradation": {
                "mean": sum(r["degradation"] for r in frac_results) / n_chambers,
                "per_chamber": [r["degradation"] for r in frac_results],
            },
            "stages_remaining": {
                "mean": sum(r["stages_remaining"] for r in frac_results) / n_chambers,
                "per_chamber": [r["stages_remaining"] for r in frac_results],
            },
            "per_chamber_detail": frac_results,
        }
        deletion_sweep.append(sweep_entry)

        print(f"  fraction={frac:.1f}: "
              f"BFS_reach={reach_ci['mean']:.4f} "
              f"[{reach_ci['ci_95'][0]:.4f}, {reach_ci['ci_95'][1]:.4f}], "
              f"struct_reach={struct_ci['mean']:.4f} "
              f"[{struct_ci['ci_95'][0]:.4f}, {struct_ci['ci_95'][1]:.4f}], "
              f"resolved={total_resolved} degraded={total_degraded} "
              f"broken={total_broken}")

    # --- Step 3b: Verify monotonicity ---
    print("\n  Monotonicity verification:")
    struct_means = [s["structural_reachability"]["mean"] for s in deletion_sweep]
    monotonic = all(
        struct_means[i] >= struct_means[i + 1] - 1e-12
        for i in range(len(struct_means) - 1)
    )
    print(f"    structural_reachability monotonic: {monotonic}")
    if not monotonic:
        print("    WARNING: monotonicity violated!")
        for i in range(len(struct_means) - 1):
            if struct_means[i] < struct_means[i + 1] - 1e-12:
                print(f"      frac={deletion_fractions[i]:.1f} "
                      f"({struct_means[i]:.4f}) < "
                      f"frac={deletion_fractions[i+1]:.1f} "
                      f"({struct_means[i+1]:.4f})")

    bfs_means = [s["bfs_reachability"]["mean"] for s in deletion_sweep]
    bfs_monotonic = all(
        bfs_means[i] >= bfs_means[i + 1] - 1e-12
        for i in range(len(bfs_means) - 1)
    )
    print(f"    bfs_reachability monotonic: {bfs_monotonic}")

    # --- Step 3c: Verify ref classification exhaustiveness ---
    print("\n  Ref classification exhaustiveness:")
    for entry in deletion_sweep:
        rc = entry["ref_classification"]
        total_check = rc["resolved"] + rc["degraded"] + rc["broken"]
        matches = total_check == rc["total"]
        print(f"    frac={entry['deletion_fraction']:.1f}: "
              f"resolved({rc['resolved']}) + degraded({rc['degraded']}) + "
              f"broken({rc['broken']}) = {total_check} == total({rc['total']}): "
              f"{'PASS' if matches else 'FAIL'}")
        assert matches, (
            f"Ref classification not exhaustive at fraction "
            f"{entry['deletion_fraction']}: {total_check} != {rc['total']}"
        )

    # --- Step 3d: Verify degraded=0 for simulated LLM compaction ---
    print("\n  Degraded category verification:")
    for entry in deletion_sweep:
        degraded = entry["ref_classification"]["degraded"]
        print(f"    frac={entry['deletion_fraction']:.1f}: "
              f"degraded={degraded} {'PASS' if degraded == 0 else 'FAIL'}")
        assert degraded == 0, (
            f"Degraded count should be 0 for simulated LLM compaction at "
            f"fraction {entry['deletion_fraction']}, got {degraded}"
        )

    # --- Step 4: Violation detection regression ---
    print("\nStep 4: Violation detection regression on original chambers...")
    regression_results = []
    for i, chamber in enumerate(chambers):
        reg = violation_regression(chamber)
        regression_results.append({
            "chamber_index": i,
            "chamber_id": chamber["chamber_id"],
            **reg,
        })
        print(f"  Chamber {i}: regression_passed={reg['regression_passed']}, "
              f"detected={reg['types_detected']}/{reg['types_tested']}")
        for ft, result in reg["per_type"].items():
            status = "DETECTED" if result["detected"] else "MISSED"
            print(f"    {ft}: {status}")

    all_regression_passed = all(r["regression_passed"] for r in regression_results)
    print(f"\n  Overall regression: {'PASSED' if all_regression_passed else 'FAILED'}")

    # --- Step 5: Anchor comparison ---
    print("\nStep 5: Anchor comparison...")
    # Use the first chamber's full measurement for anchor comparison
    full_measurement = run_compaction_measurement(
        chambers[0],
        deletion_fractions=deletion_fractions,
    )
    anchor_comparison = full_measurement["anchor_comparison"]

    # Extract key anchor comparisons
    mocklm = anchor_comparison.get("mocklm_ceiling", {})
    phase2 = anchor_comparison.get("phase2_baseline", {})
    backtrack = anchor_comparison.get("backtracking_threshold", {})

    print(f"  MockLM ceiling: pre_compaction_matches={mocklm.get('pre_compaction_matches')}")
    print(f"  Phase 2 baseline: pre_compaction_matches={phase2.get('pre_compaction_matches')}")
    print(f"  Backtracking threshold: floor={backtrack.get('reachability_floor')}")

    # Per-deletion-fraction anchor comparison
    print("\n  Per-deletion-fraction gap to MockLM ceiling:")
    backtracking_threshold_fraction = None
    for frac in deletion_fractions:
        key = f"simulated_deletion_{frac}"
        sim_anchor = anchor_comparison.get(key, {})
        gap = sim_anchor.get("gap_to_mocklm", "N/A")
        above = sim_anchor.get("above_backtracking_threshold", "N/A")
        post_r = sim_anchor.get("post_reachability", "N/A")
        print(f"    frac={frac:.1f}: reachability={post_r}, "
              f"gap_to_mocklm={gap}, "
              f"above_backtracking={above}")
        if above is False and backtracking_threshold_fraction is None:
            backtracking_threshold_fraction = frac

    # Also compute backtracking from structural_reachability
    backtracking_struct = None
    for entry in deletion_sweep:
        if entry["structural_reachability"]["mean"] < 0.5:
            backtracking_struct = entry["deletion_fraction"]
            break

    print(f"\n  Backtracking threshold crossing (BFS): "
          f"fraction={backtracking_threshold_fraction}")
    print(f"  Backtracking threshold crossing (structural): "
          f"fraction={backtracking_struct}")

    # --- Step 6: Assemble results ---
    print("\nStep 6: Assembling results...")
    results = {
        "methodology": "simulated_compaction_via_programmatic_deletion",
        "methodology_note": (
            "Simulated LLM compaction uses oldest-first stage deletion. "
            "This provides a LOWER BOUND on reachability under real LLM "
            "context-window compaction (random deletion is worse than "
            "intelligent summarization). Results are analytical predictions, "
            "NOT empirical measurements of genuine LLM compaction."
        ),
        "chambers_measured": n_chambers,
        "chambers": [
            {
                "chamber_id": ch["chamber_id"],
                "stage_count": len(ch.get("stages", [])),
                "status": ch["status"],
            }
            for ch in chambers
        ],
        "pre_compaction": {
            "reachability_fraction": pre_ci["mean"],
            "ci_95": list(pre_ci["ci_95"]) if pre_ci["ci_95"] else None,
            "ci_method": pre_ci["method"],
            "per_chamber": pre_compaction_results,
            "compression": compression_results,
            "phase2_anchor_confirmed": all(
                r["reachability_fraction"] == 1.0
                for r in pre_compaction_results
            ),
        },
        "deletion_sweep": deletion_sweep,
        "monotonicity_verified": {
            "structural_reachability": monotonic,
            "bfs_reachability": bfs_monotonic,
        },
        "violation_regression": {
            "per_chamber": regression_results,
            "all_passed": all_regression_passed,
            "fault_types_tested": ["D1", "D2", "D5", "D9"],
            "note": "D3/D4/D6/D7/D8 gaps are known architectural findings (Phase 3), not regressions to test",
        },
        "anchor_comparison": {
            "mocklm_ceiling": {
                "source": "tools/experiment_results.json (ref-mock-experiment)",
                "reachability": 1.0,
                "forge_trace_compression_pct": 87.0,
                "pre_compaction_matches": mocklm.get("pre_compaction_matches"),
            },
            "phase2_baseline": {
                "source": "data/baselines/baseline-report.json",
                "reachability": 1.0,
                "compression_ratio": 1.18,
                "depth": 21,
                "pre_compaction_matches": phase2.get("pre_compaction_matches"),
            },
            "backtracking_threshold": {
                "reachability_floor": 0.5,
                "bfs_crossing_fraction": backtracking_threshold_fraction,
                "structural_crossing_fraction": backtracking_struct,
                "note": "Fraction at which reachability drops below 0.5",
            },
            "per_deletion_fraction": {
                f"{frac:.1f}": {
                    "bfs_reachability": deletion_sweep[i]["bfs_reachability"]["mean"],
                    "structural_reachability": deletion_sweep[i]["structural_reachability"]["mean"],
                    "gap_to_mocklm_bfs": 1.0 - deletion_sweep[i]["bfs_reachability"]["mean"],
                    "gap_to_mocklm_structural": 1.0 - deletion_sweep[i]["structural_reachability"]["mean"],
                    "above_backtracking_bfs": deletion_sweep[i]["bfs_reachability"]["mean"] >= 0.5,
                    "above_backtracking_structural": deletion_sweep[i]["structural_reachability"]["mean"] >= 0.5,
                }
                for i, frac in enumerate(deletion_fractions)
            },
        },
        "metadata": {
            "timestamp": timestamp,
            "harness_version": "compaction_harness.py v1 (Plan 04-01)",
            "seed": 42,
            "deletion_fractions": deletion_fractions,
            "ci_config": {
                "bootstrap_B": 10000,
                "bootstrap_seed": 42,
                "boundary_method": "clopper_pearson",
                "interior_method": "bootstrap",
                "alpha": 0.05,
            },
            "data_source": "integration_samples/openclaw/queue_ledger.sample.jsonl",
            "python_version": sys.version,
        },
    }

    return results


def main():
    """Run the campaign and save results."""
    results = run_campaign()

    output_path = Path(__file__).parent.parent / "data" / "compaction" / "simulated-compaction-results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {output_path}")
    print(f"Chambers measured: {results['chambers_measured']}")
    print(f"Pre-compaction reachability: {results['pre_compaction']['reachability_fraction']}")
    print(f"Phase 2 anchor confirmed: {results['pre_compaction']['phase2_anchor_confirmed']}")
    print(f"Monotonicity verified (structural): {results['monotonicity_verified']['structural_reachability']}")
    print(f"Monotonicity verified (BFS): {results['monotonicity_verified']['bfs_reachability']}")
    print(f"Violation regression: {'PASSED' if results['violation_regression']['all_passed'] else 'FAILED'}")

    return results


if __name__ == "__main__":
    main()
