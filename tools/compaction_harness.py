"""
compaction_harness.py -- Measurement harness for provenance survival through
LLM context-window compaction events.

Provides pre/post compaction snapshots, three-tier ref classification
(resolved/degraded/broken), BFS reachability analysis, simulated compaction
via programmatic deletion, and violation detection regression.

Convention compliance:
  - "LLM compaction" = lossy semantic summarization (measurement target)
  - "Forge trace compression" = lossless structural dedup (secondary metric)
  - Unqualified "compaction" FORBIDDEN per Convention #6
  - All metrics dimensionless ratios in [0, 1] or counts >= 0
  - Hash: SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True)
  - CI: Bootstrap 95% (B=10000, seed=42) for interior; Clopper-Pearson for boundary
  - BFS: stdlib collections.deque only (no networkx dependency)

Phase: 04-compaction-survival-measurement
Plan: 01
"""

# ASSERT_CONVENTION: natural_units=N/A, compaction_layer=LLM_context_window, reachability=BFS_fraction, hash=SHA-256_canonical_JSON

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pathlib import Path

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from forge_chamber import validate_chamber
from forge_trace_codec import encode_trace, trace_stats, verify_trace


# --- Deterministic hashing (matches Convention #10) ---


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON for hashing. Convention #10: sort_keys, ensure_ascii."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True)


def _content_hash(obj: Any) -> str:
    """SHA-256 of canonical JSON representation of an artifact."""
    return hashlib.sha256(
        _canonical_json(obj).encode("utf-8")
    ).hexdigest()


# --- CompactionSnapshot ---


@dataclass
class CompactionSnapshot:
    """Snapshot of a forge chamber's artifact state at a point in time.

    Used for pre/post LLM compaction comparison.
    """

    timestamp: str
    artifact_ids: list[str]
    content_hashes: dict[str, str]   # artifact_id -> SHA-256 hash
    ref_graph: dict[str, list[str]]  # artifact_id -> list of referenced artifact IDs
    stage_count: int

    @classmethod
    def from_chamber(cls, chamber: dict) -> "CompactionSnapshot":
        """Build a snapshot from a forge chamber dict.

        Extracts all artifact IDs, computes content hashes, and builds
        the reference graph from source_refs.
        """
        now = datetime.now(timezone.utc).isoformat()
        stages = chamber.get("stages", [])

        artifact_ids: list[str] = []
        content_hashes: dict[str, str] = {}
        ref_graph: dict[str, list[str]] = {}

        for stage in stages:
            artifact = stage.get("artifact", {})
            art_id = artifact.get("id", stage.get("stage_id", ""))
            if not art_id:
                continue

            artifact_ids.append(art_id)

            # Compute content hash of the full artifact dict
            content_hashes[art_id] = _content_hash(artifact)

            # Build reference graph from refs list
            refs = artifact.get("refs", [])
            ref_targets: list[str] = []
            for ref_entry in refs:
                if isinstance(ref_entry, dict):
                    ref_id = ref_entry.get("ref", "")
                    if ref_id and ref_id.startswith("artifact:"):
                        ref_targets.append(ref_id)
                elif isinstance(ref_entry, str) and ref_entry.startswith("artifact:"):
                    ref_targets.append(ref_entry)
            ref_graph[art_id] = ref_targets

        return cls(
            timestamp=now,
            artifact_ids=artifact_ids,
            content_hashes=content_hashes,
            ref_graph=ref_graph,
            stage_count=len(stages),
        )


# --- Three-tier ref classification ---


def classify_refs(
    pre: CompactionSnapshot,
    post: CompactionSnapshot,
) -> dict:
    """Classify all refs in the post-compaction snapshot against the pre snapshot.

    Three-tier classification:
      - resolved: ref target exists in post AND content hash matches pre
      - degraded: ref target exists in post BUT content hash differs
                  (content was lossy-summarized during LLM compaction)
      - broken:   ref target does NOT exist in post
                  (artifact was removed by LLM compaction)

    Returns:
        Dict with classification lists and aggregate metrics:
        - resolved, degraded, broken: lists of (source_id, target_id) tuples
        - total: total number of refs classified
        - structural_reachability: (resolved + degraded) / total
        - semantic_fidelity: resolved / total
    """
    resolved: list[tuple[str, str]] = []
    degraded: list[tuple[str, str]] = []
    broken: list[tuple[str, str]] = []

    post_ids = set(post.artifact_ids)

    for art_id in post.artifact_ids:
        for ref_target in post.ref_graph.get(art_id, []):
            if ref_target not in post_ids:
                # Target was removed during LLM compaction
                broken.append((art_id, ref_target))
            elif ref_target in pre.content_hashes:
                post_hash = post.content_hashes.get(ref_target)
                pre_hash = pre.content_hashes.get(ref_target)
                if post_hash == pre_hash:
                    resolved.append((art_id, ref_target))
                else:
                    # Content changed (lossy summarization)
                    degraded.append((art_id, ref_target))
            else:
                # Target exists in post but was not in pre
                # (new artifact created during compaction -- treat as resolved)
                resolved.append((art_id, ref_target))

    total = len(resolved) + len(degraded) + len(broken)

    # Edge case: no refs to break -> both metrics = 1.0 (vacuously true)
    if total == 0:
        structural_reachability = 1.0
        semantic_fidelity = 1.0
    else:
        structural_reachability = (len(resolved) + len(degraded)) / total
        semantic_fidelity = len(resolved) / total

    # Dimensional check: both in [0.0, 1.0]
    assert 0.0 <= structural_reachability <= 1.0, (
        f"structural_reachability={structural_reachability} out of [0, 1]"
    )
    assert 0.0 <= semantic_fidelity <= 1.0, (
        f"semantic_fidelity={semantic_fidelity} out of [0, 1]"
    )
    # Constraint: structural_reachability >= semantic_fidelity
    assert structural_reachability >= semantic_fidelity - 1e-12, (
        f"structural_reachability ({structural_reachability}) < "
        f"semantic_fidelity ({semantic_fidelity})"
    )

    return {
        "resolved": resolved,
        "degraded": degraded,
        "broken": broken,
        "total": total,
        "structural_reachability": structural_reachability,
        "semantic_fidelity": semantic_fidelity,
    }


# --- BFS reachability (stdlib only, no networkx) ---


def measure_reachability(snapshot: CompactionSnapshot) -> dict:
    """Measure provenance reachability via BFS from every artifact toward roots.

    An artifact is "reachable" if BFS from it can reach at least one root.
    Root nodes are artifacts with no outgoing refs (iteration-0 artifacts).

    Uses collections.deque for BFS queue (stdlib only, no networkx).

    Returns:
        Dict with reachability metrics:
        - reachability_fraction: reachable_count / total_count, in [0.0, 1.0]
        - reachable_count: number of artifacts that can reach a root
        - total_count: total number of artifacts
        - unreachable_ids: list of artifact IDs that cannot reach any root
        - max_depth: maximum BFS depth across all artifacts
    """
    all_ids = set(snapshot.artifact_ids)

    if not all_ids:
        # Empty chamber: vacuously reachable
        return {
            "reachability_fraction": 1.0,
            "reachable_count": 0,
            "total_count": 0,
            "unreachable_ids": [],
            "max_depth": 0,
        }

    # Identify root nodes: artifacts with no outgoing refs
    # (or only refs to non-artifact IDs like chamber IDs)
    roots = set()
    for art_id in all_ids:
        out_refs = snapshot.ref_graph.get(art_id, [])
        # Filter to refs that point to other artifacts in the snapshot
        artifact_refs = [r for r in out_refs if r in all_ids]
        if not artifact_refs:
            roots.add(art_id)

    if not roots:
        # No roots found: no artifact has empty refs
        # This means every artifact refs something, forming a cycle or
        # all refs point outside the snapshot. Treat all as unreachable.
        return {
            "reachability_fraction": 0.0,
            "reachable_count": 0,
            "total_count": len(all_ids),
            "unreachable_ids": sorted(all_ids),
            "max_depth": 0,
        }

    # BFS from each artifact following ref_graph edges toward roots
    reachable = set()
    max_depth = 0

    for start_id in all_ids:
        if start_id in roots:
            reachable.add(start_id)
            continue

        # BFS: follow outgoing refs (source_refs point to parents/upstream)
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        queue.append((start_id, 0))
        visited.add(start_id)
        found_root = False

        while queue:
            current, depth = queue.popleft()
            if current in roots:
                found_root = True
                max_depth = max(max_depth, depth)
                break

            for neighbor in snapshot.ref_graph.get(current, []):
                if neighbor in all_ids and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        if found_root:
            reachable.add(start_id)

    reachable_count = len(reachable)
    total_count = len(all_ids)
    unreachable_ids = sorted(all_ids - reachable)
    reachability_fraction = reachable_count / total_count

    # Dimensional check: reachability_fraction in [0.0, 1.0]
    assert 0.0 <= reachability_fraction <= 1.0, (
        f"reachability_fraction={reachability_fraction} out of [0, 1]"
    )

    return {
        "reachability_fraction": reachability_fraction,
        "reachable_count": reachable_count,
        "total_count": total_count,
        "unreachable_ids": unreachable_ids,
        "max_depth": max_depth,
    }


# --- Simulated LLM compaction (Approach 2 fallback) ---


def simulate_compaction(
    chamber: dict,
    deletion_fraction: float,
    seed: int = 42,
) -> tuple[dict, CompactionSnapshot, CompactionSnapshot]:
    """Simulate LLM context-window compaction by programmatic stage deletion.

    Deletes the oldest `deletion_fraction` of stages (by index order, since
    stages are chronologically ordered). This provides a LOWER BOUND on
    reachability under real LLM compaction (random deletion is worse than
    intelligent summarization).

    NOTE: This simulates LLM context-window compaction (lossy semantic
    summarization), NOT forge trace compression (lossless structural dedup).

    Args:
        chamber: A forge chamber dict (not modified; deep copy used).
        deletion_fraction: Fraction of stages to delete, in [0.0, 1.0].
        seed: Random seed for reproducibility (used for determinism, not
              randomized deletion -- deletion is oldest-first).

    Returns:
        Tuple of:
        - modified_chamber: chamber with oldest stages removed
        - pre_snapshot: snapshot before deletion
        - post_snapshot: snapshot after deletion
    """
    if not 0.0 <= deletion_fraction <= 1.0:
        raise ValueError(
            f"deletion_fraction must be in [0.0, 1.0], got {deletion_fraction}"
        )

    # Deep copy to avoid mutating original
    # Handle set -> list for deepcopy
    orig_index = chamber.get("artifact_index")
    if isinstance(orig_index, set):
        chamber["artifact_index"] = sorted(orig_index)
    modified = copy.deepcopy(chamber)
    if isinstance(orig_index, set):
        chamber["artifact_index"] = orig_index
    idx = modified.get("artifact_index")
    if isinstance(idx, list):
        modified["artifact_index"] = set(idx)

    # Take pre-deletion snapshot
    pre_snapshot = CompactionSnapshot.from_chamber(modified)

    stages = modified.get("stages", [])
    total_stages = len(stages)
    n_to_delete = int(total_stages * deletion_fraction)

    if n_to_delete == 0 or total_stages == 0:
        # No deletion: return chamber as-is with identical snapshots
        post_snapshot = CompactionSnapshot.from_chamber(modified)
        return modified, pre_snapshot, post_snapshot

    # Delete the oldest n_to_delete stages (by index order)
    deleted_stages = stages[:n_to_delete]
    remaining_stages = stages[n_to_delete:]

    # Collect IDs of deleted artifacts
    deleted_ids: set[str] = set()
    for stage in deleted_stages:
        art = stage.get("artifact", {})
        art_id = art.get("id", stage.get("stage_id", ""))
        if art_id:
            deleted_ids.add(art_id)
        # Also remove summary IDs
        summary = stage.get("summary")
        if summary is not None:
            sid = summary.get("id")
            if isinstance(sid, str):
                deleted_ids.add(sid)

    # Update modified chamber
    modified["stages"] = remaining_stages

    # Remove deleted IDs from artifact_index
    art_idx = modified.get("artifact_index", set())
    if isinstance(art_idx, list):
        art_idx = set(art_idx)
    art_idx -= deleted_ids
    modified["artifact_index"] = art_idx

    # Re-index stage indices
    for i, stage in enumerate(modified["stages"]):
        stage["stage_index"] = i

    # Take post-deletion snapshot
    post_snapshot = CompactionSnapshot.from_chamber(modified)

    return modified, pre_snapshot, post_snapshot


# --- Violation detection regression ---


def violation_regression(
    chamber: dict,
    fault_types: list[str] | None = None,
) -> dict:
    """Verify that known fault types are still detected after harness changes.

    Reuses FaultInjector from tools/fault_injector.py. For each fault type
    in the list, injects the fault and verifies detection via validate_chamber().

    Default fault_types = ["D1", "D2", "D5", "D9"] (the types Phase 3
    detected at 100%).

    Args:
        chamber: A valid sealed forge chamber dict.
        fault_types: List of fault type strings to test.

    Returns:
        Dict with per-type results and overall regression status.
    """
    from fault_injector import FaultInjector, ForgeChamberError

    if fault_types is None:
        fault_types = ["D1", "D2", "D5", "D9"]

    injector = FaultInjector(chamber)
    per_type: dict[str, dict] = {}
    types_detected = 0

    for ft in fault_types:
        try:
            if ft == "D9":
                # D9 raises ForgeChamberError on injection (expected)
                try:
                    injector.inject_d9_post_seal_registration()
                    detected = False  # Should not reach here
                except ForgeChamberError:
                    detected = True
            else:
                # Inject at stage 0 (deterministic, always exists)
                inject_method = {
                    "D1": injector.inject_d1_null_collapse,
                    "D2": injector.inject_d2_broken_provenance,
                    "D5": injector.inject_d5_missing_state_label,
                }
                if ft in inject_method:
                    corrupted = inject_method[ft](0)
                else:
                    # Use random injection for other types
                    corrupted = injector.inject_random(ft, seed=42)

                errors = validate_chamber(corrupted)
                detected = len(errors) > 0

            per_type[ft] = {
                "injected": True,
                "detected": detected,
            }
            if detected:
                types_detected += 1

        except Exception as e:
            per_type[ft] = {
                "injected": False,
                "detected": False,
                "error": f"{type(e).__name__}: {e}",
            }

    return {
        "per_type": per_type,
        "regression_passed": types_detected == len(fault_types),
        "types_tested": len(fault_types),
        "types_detected": types_detected,
    }


# --- Anchor comparison ---


def compare_against_anchors(measurements: dict) -> dict:
    """Compare post-compaction metrics against known anchors.

    Anchors:
    - MockLM ceiling: reachability=1.0, forge trace compression=87%
      (ref-mock-experiment: tools/experiment_results.json)
    - Phase 2 baseline: reachability=1.0, forge trace compression=1.18x,
      depth=21 (data/baselines/baseline-report.json)
    - Backtracking threshold: reachability=0.5 (below this, provenance
      chain is too degraded for meaningful recovery)

    Args:
        measurements: Dict from run_compaction_measurement().

    Returns:
        Dict with gap analysis for each anchor comparison.
    """
    pre_reach = measurements.get("pre_compaction_reachability", {}).get(
        "reachability_fraction", 0.0
    )

    # Collect post-compaction reachabilities at each deletion fraction
    sim_results = measurements.get("simulated_compaction_results", [])

    anchors = {
        "mocklm_ceiling": {
            "source": "tools/experiment_results.json (ref-mock-experiment)",
            "reachability": 1.0,
            "forge_trace_compression_pct": 87.0,
            "pre_compaction_gap": abs(pre_reach - 1.0),
            "pre_compaction_matches": abs(pre_reach - 1.0) < 1e-9,
        },
        "phase2_baseline": {
            "source": "data/baselines/baseline-report.json",
            "reachability": 1.0,
            "forge_trace_compression_ratio": 1.18,
            "depth": 21,
            "pre_compaction_gap": abs(pre_reach - 1.0),
            "pre_compaction_matches": abs(pre_reach - 1.0) < 1e-9,
        },
        "backtracking_threshold": {
            "reachability_floor": 0.5,
            "purpose": "Below 0.5, provenance chain too degraded for recovery",
        },
    }

    # Add per-deletion-fraction comparisons
    for sim in sim_results:
        frac = sim.get("deletion_fraction")
        post_reach = sim.get("post_reachability", {}).get(
            "reachability_fraction", 0.0
        )
        anchors[f"simulated_deletion_{frac}"] = {
            "deletion_fraction": frac,
            "post_reachability": post_reach,
            "degradation": pre_reach - post_reach,
            "above_backtracking_threshold": post_reach >= 0.5,
            "gap_to_mocklm": abs(post_reach - 1.0),
        }

    return anchors


# --- Full measurement pipeline ---


def run_compaction_measurement(
    chamber: dict,
    deletion_fractions: list[float] | None = None,
) -> dict:
    """Orchestrate the full LLM compaction survival measurement for a single chamber.

    Steps:
    a. Take pre-compaction snapshot
    b. Measure pre-compaction reachability (should be 1.0 per Phase 2)
    c. For each deletion_fraction: simulate LLM compaction, measure
       post-compaction reachability, classify refs
    d. Run violation regression on original (non-deleted) chamber
    e. Compute forge trace compression via encode_trace/decode_trace
    f. Return complete measurement dict

    NOTE: "simulated LLM compaction" is used here because genuine
    LLM context-window compaction data requires Plan 02 execution.
    Simulated deletion provides a LOWER BOUND on reachability.

    Args:
        chamber: A sealed forge chamber dict.
        deletion_fractions: List of deletion fractions to test.
                           Default: [0.3, 0.5, 0.7].

    Returns:
        Complete measurement dict with all metrics and anchor comparisons.
    """
    if deletion_fractions is None:
        deletion_fractions = [0.3, 0.5, 0.7]

    timestamp = datetime.now(timezone.utc).isoformat()

    # a. Pre-compaction snapshot
    pre_snapshot = CompactionSnapshot.from_chamber(chamber)

    # b. Pre-compaction reachability
    pre_reachability = measure_reachability(pre_snapshot)

    # c. Simulated LLM compaction at each deletion fraction
    sim_results: list[dict] = []
    for frac in deletion_fractions:
        modified_chamber, pre_snap, post_snap = simulate_compaction(
            chamber, frac
        )

        # Post-compaction reachability
        post_reachability = measure_reachability(post_snap)

        # Three-tier ref classification
        ref_class = classify_refs(pre_snap, post_snap)

        # Degradation = pre - post reachability
        degradation = (
            pre_reachability["reachability_fraction"]
            - post_reachability["reachability_fraction"]
        )

        # Dimensional check: degradation in [0.0, 1.0]
        # (could be negative if post somehow gains reachability, but
        #  for deletion that shouldn't happen)

        sim_results.append({
            "deletion_fraction": frac,
            "post_reachability": post_reachability,
            "ref_classification": {
                "resolved_count": len(ref_class["resolved"]),
                "degraded_count": len(ref_class["degraded"]),
                "broken_count": len(ref_class["broken"]),
                "total": ref_class["total"],
                "structural_reachability": ref_class["structural_reachability"],
                "semantic_fidelity": ref_class["semantic_fidelity"],
            },
            "degradation": degradation,
            "stages_remaining": post_snap.stage_count,
            "artifacts_remaining": len(post_snap.artifact_ids),
        })

    # d. Violation regression on original chamber
    regression = violation_regression(chamber)

    # e. Forge trace compression (lossless structural -- NOT LLM compaction)
    trace_compression: dict[str, Any] = {}
    try:
        trace = encode_trace(chamber)
        stats = trace_stats(trace)
        verification = verify_trace(trace, chamber)
        trace_compression = {
            "compression_ratio": stats.get("compression_ratio", 1.0),
            "original_size": stats.get("original_size", 0),
            "encoded_size": stats.get("encoded_size", 0),
            "shared_structures": stats.get("shared_structures", 0),
            "ref_replacements": stats.get("ref_replacements", 0),
            "round_trip_verified": verification.get("valid", False),
            "hash_match": verification.get("hash_match", False),
        }
    except Exception as e:
        trace_compression = {
            "error": f"{type(e).__name__}: {e}",
        }

    # f. Assemble complete measurement
    measurements = {
        "timestamp": timestamp,
        "chamber_id": chamber.get("chamber_id", "unknown"),
        "pre_compaction_reachability": pre_reachability,
        "pre_compaction_snapshot": {
            "artifact_count": len(pre_snapshot.artifact_ids),
            "stage_count": pre_snapshot.stage_count,
            "ref_count": sum(
                len(refs) for refs in pre_snapshot.ref_graph.values()
            ),
        },
        "simulated_compaction_results": sim_results,
        "violation_regression": regression,
        "forge_trace_compression": trace_compression,
    }

    # Anchor comparison
    measurements["anchor_comparison"] = compare_against_anchors(measurements)

    return measurements


# --- Bootstrap CI integration (reuse from existing tools) ---


def _import_ci_functions():
    """Import CI functions from existing tools to avoid reimplementation.

    Reuses:
    - bootstrap_ci from baseline_measurement.py (B=10000, seed=42)
    - clopper_pearson_ci and select_ci from fault_injector.py
    """
    from baseline_measurement import bootstrap_ci as bm_bootstrap_ci
    from fault_injector import (
        clopper_pearson_ci as fi_clopper_pearson_ci,
        select_ci as fi_select_ci,
    )
    return bm_bootstrap_ci, fi_clopper_pearson_ci, fi_select_ci


def compute_reachability_ci(
    reachability_values: list[float],
) -> dict:
    """Compute confidence interval for reachability measurements.

    Uses bootstrap for interior values, Clopper-Pearson for boundary.

    Args:
        reachability_values: List of reachability_fraction values.

    Returns:
        Dict with mean, CI bounds, and method used.
    """
    if not reachability_values:
        return {"mean": None, "ci_95": None, "method": None}

    n = len(reachability_values)
    mean_val = sum(reachability_values) / n

    # Check if boundary (all 0.0 or all 1.0)
    all_one = all(abs(v - 1.0) < 1e-12 for v in reachability_values)
    all_zero = all(abs(v) < 1e-12 for v in reachability_values)

    bm_bootstrap_ci, fi_clopper_pearson_ci, fi_select_ci = _import_ci_functions()

    if all_one:
        lower, upper = fi_clopper_pearson_ci(n, n)
        method = "clopper_pearson"
    elif all_zero:
        lower, upper = fi_clopper_pearson_ci(0, n)
        method = "clopper_pearson"
    elif n == 1:
        lower, upper = mean_val, mean_val
        method = "single_value"
    else:
        lower, upper = bm_bootstrap_ci(reachability_values)
        method = "bootstrap"

    return {
        "mean": mean_val,
        "ci_95": (lower, upper),
        "method": method,
        "n": n,
    }
