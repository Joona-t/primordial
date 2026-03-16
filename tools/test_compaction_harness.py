"""
test_compaction_harness.py -- Unit tests for the compaction measurement harness.

Tests validate the harness against known scenarios:
1. Snapshot construction: empty, Phase 2-like, hash determinism
2. BFS reachability: pre-compaction=1.0 (Phase 2 anchor), broken ref, linear chain, diamond DAG
3. Three-tier ref classification: all resolved, degraded, broken, exhaustiveness
4. Simulated LLM compaction: deletion reduces structural_reachability, zero/full deletion limits
5. Violation regression: D1/D2/D5/D9 injected and detected
6. Anchor comparison: MockLM, Phase 2, backtracking threshold
7. Pipeline integration: full measurement produces all expected keys

Convention compliance:
  - "LLM compaction" = lossy semantic summarization (measurement target)
  - "Forge trace compression" = lossless structural dedup (secondary metric)
  - Unqualified "compaction" FORBIDDEN per Convention #6

Phase: 04-compaction-survival-measurement
Plan: 01
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from compaction_harness import (
    CompactionSnapshot,
    classify_refs,
    compare_against_anchors,
    compute_reachability_ci,
    measure_reachability,
    run_compaction_measurement,
    simulate_compaction,
    violation_regression,
    _content_hash,
)
from forge_chamber import (
    create_chamber,
    register_stage,
    seal_chamber,
    validate_chamber,
)
from forge_nulls import AbsenceState
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_linear_chamber(
    n_stages: int = 10,
    session_id: str = "test-linear",
) -> dict:
    """Build a sealed linear-chain chamber with n_stages.

    Stage i refs stage i-1 (except stage 0, which is root).
    """
    chamber = create_chamber(f"chamber:test:{session_id}:v1")
    prev_id = None
    for i in range(n_stages):
        stage_id = f"artifact:test:{session_id}:stage:{i}:r1"
        source_refs = [prev_id] if prev_id else None
        art = create_v1_stage_artifact(
            stage_id=stage_id,
            seat="test-seat",
            producer_name="test-producer",
            producer_role="test-role",
            output=f"Stage {i} output: working on iteration {i}",
            source_refs=source_refs,
        )
        sv = create_v1_stage_summary(
            art,
            f"Summary for stage {i}.",
            extra_source_refs=source_refs,
        )
        register_stage(chamber, art, sv)
        prev_id = stage_id
    seal_chamber(chamber)
    return chamber


def _make_diamond_chamber(session_id: str = "test-diamond") -> dict:
    """Build a sealed diamond DAG chamber: A -> {B, C} -> D.

    A is root (no refs). B and C both ref A. D refs B and C.
    """
    chamber = create_chamber(f"chamber:test:{session_id}:v1")

    a = create_v1_stage_artifact(
        stage_id=f"artifact:test:{session_id}:A:r1",
        seat="s", producer_name="p", producer_role="r",
        output="A output",
    )
    sv_a = create_v1_stage_summary(a, "A summary")
    register_stage(chamber, a, sv_a)

    b = create_v1_stage_artifact(
        stage_id=f"artifact:test:{session_id}:B:r1",
        seat="s", producer_name="p", producer_role="r",
        output="B output",
        source_refs=[f"artifact:test:{session_id}:A:r1"],
    )
    sv_b = create_v1_stage_summary(
        b, "B summary",
        extra_source_refs=[f"artifact:test:{session_id}:A:r1"],
    )
    register_stage(chamber, b, sv_b)

    c = create_v1_stage_artifact(
        stage_id=f"artifact:test:{session_id}:C:r1",
        seat="s", producer_name="p", producer_role="r",
        output="C output",
        source_refs=[f"artifact:test:{session_id}:A:r1"],
    )
    sv_c = create_v1_stage_summary(
        c, "C summary",
        extra_source_refs=[f"artifact:test:{session_id}:A:r1"],
    )
    register_stage(chamber, c, sv_c)

    d = create_v1_stage_artifact(
        stage_id=f"artifact:test:{session_id}:D:r1",
        seat="s", producer_name="p", producer_role="r",
        output="D output",
        source_refs=[
            f"artifact:test:{session_id}:B:r1",
            f"artifact:test:{session_id}:C:r1",
        ],
    )
    sv_d = create_v1_stage_summary(
        d, "D summary",
        extra_source_refs=[
            f"artifact:test:{session_id}:B:r1",
            f"artifact:test:{session_id}:C:r1",
        ],
    )
    register_stage(chamber, d, sv_d)

    seal_chamber(chamber)
    return chamber


def _make_empty_chamber(session_id: str = "test-empty") -> dict:
    """Build a sealed empty chamber (no stages)."""
    chamber = create_chamber(f"chamber:test:{session_id}:v1")
    seal_chamber(chamber)
    return chamber


def _make_deep_chamber(
    n_stages: int = 21,
    session_id: str = "test-deep",
) -> dict:
    """Build a sealed deep chain chamber matching Phase 2 depth=21.

    Includes cursor advancement artifacts to mimic real OpenClaw traces.
    """
    chamber = create_chamber(f"chamber:test:{session_id}:v1")
    prev_id = None
    all_task_ids = []

    for i in range(n_stages):
        stage_id = f"artifact:test:{session_id}:iter:{i}:r1"
        source_refs = [prev_id] if prev_id else None

        art = create_v1_stage_artifact(
            stage_id=stage_id,
            seat="test-task",
            producer_name="test-worker",
            producer_role="task-executor",
            output=f"Task {i} output: processing step {i}",
            source_refs=source_refs,
        )
        sv = create_v1_stage_summary(
            art,
            f"Task {i} completed.",
            extra_source_refs=source_refs,
        )
        register_stage(chamber, art, sv)
        prev_id = stage_id
        all_task_ids.append(stage_id)

    seal_chamber(chamber)
    return chamber


# ---------------------------------------------------------------------------
# 1. Snapshot construction tests
# ---------------------------------------------------------------------------


class TestSnapshotConstruction:
    """Tests for CompactionSnapshot.from_chamber()."""

    def test_snapshot_from_empty_chamber(self):
        """Empty chamber produces empty snapshot."""
        chamber = _make_empty_chamber()
        snap = CompactionSnapshot.from_chamber(chamber)
        assert snap.artifact_ids == []
        assert snap.content_hashes == {}
        assert snap.ref_graph == {}
        assert snap.stage_count == 0

    def test_snapshot_from_phase2_chamber(self):
        """Chamber matching Phase 2 structure produces correct snapshot."""
        chamber = _make_deep_chamber(n_stages=21)
        snap = CompactionSnapshot.from_chamber(chamber)
        assert snap.stage_count == 21
        assert len(snap.artifact_ids) == 21
        assert len(snap.content_hashes) == 21
        # All artifacts should have entries in ref_graph
        assert len(snap.ref_graph) == 21

    def test_snapshot_content_hash_deterministic(self):
        """Same content produces same hash across calls."""
        chamber = _make_linear_chamber(n_stages=3)
        snap1 = CompactionSnapshot.from_chamber(chamber)
        snap2 = CompactionSnapshot.from_chamber(chamber)
        assert snap1.content_hashes == snap2.content_hashes

    def test_snapshot_ref_graph_correct(self):
        """Ref graph captures source_refs correctly."""
        chamber = _make_linear_chamber(n_stages=3, session_id="ref-check")
        snap = CompactionSnapshot.from_chamber(chamber)

        # Stage 0 is root: no artifact refs
        root_id = "artifact:test:ref-check:stage:0:r1"
        assert snap.ref_graph[root_id] == []

        # Stage 1 refs stage 0
        s1_id = "artifact:test:ref-check:stage:1:r1"
        assert root_id in snap.ref_graph[s1_id]

        # Stage 2 refs stage 1
        s2_id = "artifact:test:ref-check:stage:2:r1"
        assert s1_id in snap.ref_graph[s2_id]

    def test_snapshot_all_ids_unique(self):
        """All artifact IDs in snapshot are unique."""
        chamber = _make_linear_chamber(n_stages=10)
        snap = CompactionSnapshot.from_chamber(chamber)
        assert len(snap.artifact_ids) == len(set(snap.artifact_ids))

    def test_snapshot_timestamp_populated(self):
        """Snapshot has a non-empty ISO 8601 timestamp."""
        chamber = _make_linear_chamber(n_stages=2)
        snap = CompactionSnapshot.from_chamber(chamber)
        assert snap.timestamp  # non-empty string
        assert "T" in snap.timestamp  # ISO format


# ---------------------------------------------------------------------------
# 2. BFS reachability tests
# ---------------------------------------------------------------------------


class TestBFSReachability:
    """Tests for measure_reachability()."""

    def test_pre_compaction_reachability_is_one(self):
        """Chamber with all refs resolved has reachability=1.0.

        This is the Phase 2 anchor: non-compacted chambers have perfect
        reachability.
        """
        chamber = _make_deep_chamber(n_stages=21)
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        assert result["reachability_fraction"] == 1.0
        assert result["reachable_count"] == 21
        assert result["total_count"] == 21
        assert result["unreachable_ids"] == []

    def test_single_root_reachable(self):
        """A single-artifact chamber (root only) has reachability=1.0."""
        chamber = create_chamber("chamber:test:single:v1")
        art = create_v1_stage_artifact(
            stage_id="artifact:test:single:stage:0:r1",
            seat="s", producer_name="p", producer_role="r",
            output="Only artifact",
        )
        sv = create_v1_stage_summary(art, "Summary")
        register_stage(chamber, art, sv)
        seal_chamber(chamber)

        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        assert result["reachability_fraction"] == 1.0
        assert result["reachable_count"] == 1

    def test_all_roots_reachable(self):
        """Root artifacts (no refs) are always reachable."""
        chamber = _make_linear_chamber(n_stages=5)
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        # Stage 0 is root, always reachable
        root_id = "artifact:test:test-linear:stage:0:r1"
        assert root_id not in result["unreachable_ids"]

    def test_linear_chain_full_reachability(self):
        """Linear chain A->B->C->D: all reachable via root A."""
        chamber = _make_linear_chamber(n_stages=4, session_id="chain4")
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        assert result["reachability_fraction"] == 1.0
        assert result["max_depth"] > 0

    def test_diamond_dag_full_reachability(self):
        """Diamond DAG A->{B,C}->D: all reachable via root A."""
        chamber = _make_diamond_chamber()
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        assert result["reachability_fraction"] == 1.0
        assert result["reachable_count"] == 4

    def test_empty_chamber_vacuously_reachable(self):
        """0 artifacts produces reachability=1.0 (vacuously true)."""
        chamber = _make_empty_chamber()
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        assert result["reachability_fraction"] == 1.0
        assert result["reachable_count"] == 0
        assert result["total_count"] == 0

    def test_max_depth_correct(self):
        """Max depth is the longest BFS path to any root."""
        chamber = _make_linear_chamber(n_stages=5, session_id="depth5")
        snap = CompactionSnapshot.from_chamber(chamber)
        result = measure_reachability(snap)
        # Linear chain of 5: deepest is stage 4, depth 4 from root
        assert result["max_depth"] == 4

    def test_reachability_fraction_bounds(self):
        """reachability_fraction is always in [0.0, 1.0]."""
        for n in [1, 2, 5, 10, 21]:
            chamber = _make_linear_chamber(n_stages=n, session_id=f"bounds-{n}")
            snap = CompactionSnapshot.from_chamber(chamber)
            result = measure_reachability(snap)
            assert 0.0 <= result["reachability_fraction"] <= 1.0


# ---------------------------------------------------------------------------
# 3. Three-tier ref classification tests
# ---------------------------------------------------------------------------


class TestRefClassification:
    """Tests for classify_refs()."""

    def test_ref_classification_all_resolved(self):
        """No deletions, no content changes -> all resolved."""
        chamber = _make_linear_chamber(n_stages=5, session_id="all-resolved")
        snap1 = CompactionSnapshot.from_chamber(chamber)
        snap2 = CompactionSnapshot.from_chamber(chamber)
        result = classify_refs(snap1, snap2)
        assert len(result["degraded"]) == 0
        assert len(result["broken"]) == 0
        assert result["structural_reachability"] == 1.0
        assert result["semantic_fidelity"] == 1.0

    def test_ref_classification_degraded(self):
        """Same artifacts but content hashes differ -> degraded."""
        chamber = _make_linear_chamber(n_stages=3, session_id="degraded")
        pre = CompactionSnapshot.from_chamber(chamber)

        # Modify content of one artifact in the chamber (simulate lossy LLM compaction)
        # We'll build a post snapshot with modified hashes
        post = CompactionSnapshot.from_chamber(chamber)
        # Change the hash of stage 0 to simulate content degradation
        stage0_id = "artifact:test:degraded:stage:0:r1"
        post.content_hashes[stage0_id] = "deadbeef" * 8  # fake hash

        result = classify_refs(pre, post)
        # Stage 1 refs stage 0 -- hash differs -> degraded
        assert len(result["degraded"]) >= 1
        assert result["structural_reachability"] == 1.0  # ref still resolves
        assert result["semantic_fidelity"] < 1.0  # content changed

    def test_ref_classification_broken(self):
        """Artifact deleted from post snapshot -> broken."""
        chamber = _make_linear_chamber(n_stages=5, session_id="broken-ref")
        _, pre, post = simulate_compaction(chamber, 0.4)

        result = classify_refs(pre, post)
        # At least one ref should be broken (first remaining stage refs deleted stage)
        assert len(result["broken"]) >= 1

    def test_ref_classification_exhaustive(self):
        """resolved + degraded + broken == total for all test chambers."""
        for n in [3, 5, 10]:
            chamber = _make_linear_chamber(n_stages=n, session_id=f"exhaust-{n}")
            for frac in [0.0, 0.3, 0.5, 0.7]:
                _, pre, post = simulate_compaction(chamber, frac)
                result = classify_refs(pre, post)
                total = (
                    len(result["resolved"])
                    + len(result["degraded"])
                    + len(result["broken"])
                )
                assert total == result["total"], (
                    f"n={n}, frac={frac}: "
                    f"resolved+degraded+broken={total} != total={result['total']}"
                )

    def test_structural_ge_semantic(self):
        """structural_reachability >= semantic_fidelity for all scenarios."""
        for n in [3, 5, 10]:
            chamber = _make_linear_chamber(n_stages=n, session_id=f"ge-{n}")
            for frac in [0.0, 0.3, 0.5, 0.7]:
                _, pre, post = simulate_compaction(chamber, frac)
                result = classify_refs(pre, post)
                assert result["structural_reachability"] >= result["semantic_fidelity"] - 1e-12

    def test_zero_refs_edge_case(self):
        """Chamber with no inter-artifact refs -> both metrics = 1.0."""
        # Single artifact, no refs
        chamber = create_chamber("chamber:test:noref:v1")
        art = create_v1_stage_artifact(
            stage_id="artifact:test:noref:stage:0:r1",
            seat="s", producer_name="p", producer_role="r",
            output="Standalone artifact",
        )
        sv = create_v1_stage_summary(art, "Summary")
        register_stage(chamber, art, sv)
        seal_chamber(chamber)

        snap = CompactionSnapshot.from_chamber(chamber)
        result = classify_refs(snap, snap)
        assert result["total"] == 0
        assert result["structural_reachability"] == 1.0
        assert result["semantic_fidelity"] == 1.0


# ---------------------------------------------------------------------------
# 4. Simulated LLM compaction tests
# ---------------------------------------------------------------------------


class TestSimulatedCompaction:
    """Tests for simulate_compaction()."""

    def test_simulated_deletion_reduces_structural_reachability(self):
        """deletion_fraction=0.5 on chain -> structural_reachability < 1.0.

        BFS reachability may remain 1.0 for linear chains (sub-chain is
        still internally connected), but structural_reachability from
        classify_refs captures the broken provenance link.
        """
        chamber = _make_linear_chamber(n_stages=10, session_id="sim-del")
        _, pre, post = simulate_compaction(chamber, 0.5)

        ref_class = classify_refs(pre, post)
        # At least one broken ref (first remaining stage refs deleted stage)
        assert ref_class["structural_reachability"] < 1.0 or len(ref_class["broken"]) >= 1

    def test_zero_deletion_preserves_reachability(self):
        """deletion_fraction=0.0 -> reachability unchanged."""
        chamber = _make_linear_chamber(n_stages=5, session_id="zero-del")
        _, pre, post = simulate_compaction(chamber, 0.0)

        pre_reach = measure_reachability(pre)
        post_reach = measure_reachability(post)
        assert pre_reach["reachability_fraction"] == post_reach["reachability_fraction"]
        assert pre_reach["total_count"] == post_reach["total_count"]

    def test_full_deletion_empties_chamber(self):
        """deletion_fraction=1.0 -> no artifacts remain."""
        chamber = _make_linear_chamber(n_stages=5, session_id="full-del")
        modified, pre, post = simulate_compaction(chamber, 1.0)
        assert post.stage_count == 0
        assert len(post.artifact_ids) == 0

        reach = measure_reachability(post)
        assert reach["total_count"] == 0
        assert reach["reachability_fraction"] == 1.0  # vacuously true

    def test_deletion_structural_reachability_monotonic(self):
        """Higher deletion -> lower or equal structural_reachability.

        Tests at 0.0, 0.1, 0.3, 0.5, 0.7, 0.9 deletion fractions.
        structural_reachability from classify_refs should be monotonically
        non-increasing as more stages are deleted.
        """
        chamber = _make_linear_chamber(n_stages=20, session_id="monotonic")
        fractions = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9]
        prev_sr = 1.1  # start above max

        for frac in fractions:
            _, pre, post = simulate_compaction(chamber, frac)
            ref_class = classify_refs(pre, post)
            sr = ref_class["structural_reachability"]
            assert sr <= prev_sr + 1e-9, (
                f"Non-monotonic: sr={sr} at frac={frac}, prev_sr={prev_sr}"
            )
            prev_sr = sr

    def test_deletion_is_deterministic(self):
        """Same seed produces same result."""
        chamber = _make_linear_chamber(n_stages=10, session_id="deterministic")
        mod1, pre1, post1 = simulate_compaction(chamber, 0.5, seed=42)
        mod2, pre2, post2 = simulate_compaction(chamber, 0.5, seed=42)
        assert post1.artifact_ids == post2.artifact_ids
        assert post1.content_hashes == post2.content_hashes

    def test_deletion_fraction_bounds(self):
        """Invalid deletion_fraction raises ValueError."""
        chamber = _make_linear_chamber(n_stages=3, session_id="bounds")
        with pytest.raises(ValueError):
            simulate_compaction(chamber, -0.1)
        with pytest.raises(ValueError):
            simulate_compaction(chamber, 1.1)

    def test_deletion_preserves_remaining_content(self):
        """After deletion, remaining artifacts have identical content hashes."""
        chamber = _make_linear_chamber(n_stages=10, session_id="content-preserve")
        pre_snap = CompactionSnapshot.from_chamber(chamber)
        _, _, post_snap = simulate_compaction(chamber, 0.3)

        for art_id in post_snap.artifact_ids:
            if art_id in pre_snap.content_hashes:
                assert post_snap.content_hashes[art_id] == pre_snap.content_hashes[art_id], (
                    f"Content hash changed for {art_id} after deletion"
                )


# ---------------------------------------------------------------------------
# 5. Violation regression tests
# ---------------------------------------------------------------------------


class TestViolationRegression:
    """Tests for violation_regression()."""

    def test_violation_regression_on_clean_chamber(self):
        """D1/D2/D5/D9 injected and detected on valid chamber."""
        chamber = _make_linear_chamber(n_stages=5, session_id="regression")
        result = violation_regression(chamber)
        assert result["regression_passed"] is True
        assert result["types_tested"] == 4
        assert result["types_detected"] == 4

    def test_violation_regression_returns_per_type(self):
        """Output has per_type dict with all 4 default types."""
        chamber = _make_linear_chamber(n_stages=5, session_id="per-type")
        result = violation_regression(chamber)
        assert "per_type" in result
        for ft in ["D1", "D2", "D5", "D9"]:
            assert ft in result["per_type"]
            assert result["per_type"][ft]["injected"] is True
            assert result["per_type"][ft]["detected"] is True

    def test_violation_regression_custom_types(self):
        """Custom fault types list is respected."""
        chamber = _make_linear_chamber(n_stages=5, session_id="custom-types")
        result = violation_regression(chamber, fault_types=["D1", "D2"])
        assert result["types_tested"] == 2

    def test_violation_regression_d9_detection(self):
        """D9 (post-seal registration) is detected via ForgeChamberError."""
        chamber = _make_linear_chamber(n_stages=3, session_id="d9-test")
        result = violation_regression(chamber, fault_types=["D9"])
        assert result["per_type"]["D9"]["detected"] is True


# ---------------------------------------------------------------------------
# 6. Anchor comparison tests
# ---------------------------------------------------------------------------


class TestAnchorComparison:
    """Tests for compare_against_anchors()."""

    def _make_measurements(self) -> dict:
        """Build a sample measurements dict for anchor comparison."""
        chamber = _make_linear_chamber(n_stages=10, session_id="anchor")
        return run_compaction_measurement(chamber, deletion_fractions=[0.3, 0.5])

    def test_anchor_comparison_reports_mocklm(self):
        """MockLM ceiling (reachability=1.0) appears in output."""
        meas = self._make_measurements()
        anchors = meas["anchor_comparison"]
        assert "mocklm_ceiling" in anchors
        assert anchors["mocklm_ceiling"]["reachability"] == 1.0
        assert "forge_trace_compression_pct" in anchors["mocklm_ceiling"]

    def test_anchor_comparison_reports_phase2(self):
        """Phase 2 baseline appears in output."""
        meas = self._make_measurements()
        anchors = meas["anchor_comparison"]
        assert "phase2_baseline" in anchors
        assert anchors["phase2_baseline"]["reachability"] == 1.0
        assert anchors["phase2_baseline"]["depth"] == 21

    def test_anchor_comparison_reports_backtracking(self):
        """Backtracking threshold (reachability=0.5) appears in output."""
        meas = self._make_measurements()
        anchors = meas["anchor_comparison"]
        assert "backtracking_threshold" in anchors
        assert anchors["backtracking_threshold"]["reachability_floor"] == 0.5

    def test_anchor_comparison_per_deletion_fraction(self):
        """Each deletion fraction gets its own anchor comparison."""
        meas = self._make_measurements()
        anchors = meas["anchor_comparison"]
        assert "simulated_deletion_0.3" in anchors
        assert "simulated_deletion_0.5" in anchors

    def test_anchor_pre_compaction_matches_phase2(self):
        """Pre-compaction reachability matches Phase 2 (1.0)."""
        meas = self._make_measurements()
        anchors = meas["anchor_comparison"]
        assert anchors["mocklm_ceiling"]["pre_compaction_matches"] is True
        assert anchors["phase2_baseline"]["pre_compaction_matches"] is True


# ---------------------------------------------------------------------------
# 7. Pipeline integration test
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Tests for run_compaction_measurement()."""

    def test_run_compaction_measurement_complete(self):
        """Full pipeline produces all expected keys with valid ranges."""
        chamber = _make_deep_chamber(n_stages=21)
        result = run_compaction_measurement(
            chamber, deletion_fractions=[0.3, 0.5, 0.7]
        )

        # Required top-level keys
        assert "timestamp" in result
        assert "chamber_id" in result
        assert "pre_compaction_reachability" in result
        assert "pre_compaction_snapshot" in result
        assert "simulated_compaction_results" in result
        assert "violation_regression" in result
        assert "forge_trace_compression" in result
        assert "anchor_comparison" in result

        # Pre-compaction reachability
        pre_reach = result["pre_compaction_reachability"]
        assert pre_reach["reachability_fraction"] == 1.0
        assert pre_reach["total_count"] == 21

        # Simulated LLM compaction results
        sim = result["simulated_compaction_results"]
        assert len(sim) == 3
        for entry in sim:
            assert "deletion_fraction" in entry
            assert "post_reachability" in entry
            assert "ref_classification" in entry
            assert "degradation" in entry
            # Post reachability is valid
            post_r = entry["post_reachability"]["reachability_fraction"]
            assert 0.0 <= post_r <= 1.0

        # Violation regression passed
        assert result["violation_regression"]["regression_passed"] is True

        # Forge trace compression (lossless structural)
        ftc = result["forge_trace_compression"]
        assert "compression_ratio" in ftc
        assert ftc["compression_ratio"] > 0
        assert ftc["round_trip_verified"] is True

    def test_pipeline_ref_classification_complete(self):
        """Pipeline ref classification includes all required fields."""
        chamber = _make_linear_chamber(n_stages=10, session_id="pipeline-ref")
        result = run_compaction_measurement(chamber, deletion_fractions=[0.5])

        sim = result["simulated_compaction_results"][0]
        rc = sim["ref_classification"]
        assert "resolved_count" in rc
        assert "degraded_count" in rc
        assert "broken_count" in rc
        assert "total" in rc
        assert "structural_reachability" in rc
        assert "semantic_fidelity" in rc
        # Exhaustiveness
        assert rc["resolved_count"] + rc["degraded_count"] + rc["broken_count"] == rc["total"]

    def test_pipeline_default_deletion_fractions(self):
        """Default deletion fractions are [0.3, 0.5, 0.7]."""
        chamber = _make_linear_chamber(n_stages=10, session_id="default-frac")
        result = run_compaction_measurement(chamber)
        fracs = [s["deletion_fraction"] for s in result["simulated_compaction_results"]]
        assert fracs == [0.3, 0.5, 0.7]

    def test_pipeline_degradation_non_negative(self):
        """Degradation = pre - post reachability >= 0 for deletion."""
        chamber = _make_linear_chamber(n_stages=10, session_id="degrad-check")
        result = run_compaction_measurement(chamber, deletion_fractions=[0.3, 0.5, 0.7])
        for sim in result["simulated_compaction_results"]:
            assert sim["degradation"] >= -1e-12, (
                f"Negative degradation={sim['degradation']} at "
                f"frac={sim['deletion_fraction']}"
            )


# ---------------------------------------------------------------------------
# 8. Content hash tests
# ---------------------------------------------------------------------------


class TestContentHash:
    """Tests for _content_hash determinism and correctness."""

    def test_hash_deterministic(self):
        """Same dict produces same hash."""
        d = {"key": "value", "nested": {"a": 1, "b": 2}}
        h1 = _content_hash(d)
        h2 = _content_hash(d)
        assert h1 == h2

    def test_hash_key_order_independent(self):
        """Hash is independent of key insertion order."""
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert _content_hash(d1) == _content_hash(d2)

    def test_hash_changes_with_content(self):
        """Different content produces different hash."""
        d1 = {"key": "value1"}
        d2 = {"key": "value2"}
        assert _content_hash(d1) != _content_hash(d2)

    def test_hash_is_sha256(self):
        """Hash is 64 hex characters (SHA-256)."""
        h = _content_hash({"test": True})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# 9. Reachability CI tests
# ---------------------------------------------------------------------------


class TestReachabilityCi:
    """Tests for compute_reachability_ci()."""

    def test_ci_all_ones(self):
        """All-1.0 values use Clopper-Pearson."""
        result = compute_reachability_ci([1.0, 1.0, 1.0])
        assert result["method"] == "clopper_pearson"
        assert result["mean"] == 1.0
        assert result["ci_95"][1] == 1.0  # upper bound is 1.0

    def test_ci_all_zeros(self):
        """All-0.0 values use Clopper-Pearson."""
        result = compute_reachability_ci([0.0, 0.0, 0.0])
        assert result["method"] == "clopper_pearson"
        assert result["mean"] == 0.0
        assert result["ci_95"][0] == 0.0  # lower bound is 0.0

    def test_ci_interior_uses_bootstrap(self):
        """Interior values use bootstrap."""
        result = compute_reachability_ci([0.8, 0.85, 0.9, 0.75])
        assert result["method"] == "bootstrap"
        assert 0.0 <= result["ci_95"][0] <= result["ci_95"][1] <= 1.0

    def test_ci_single_value(self):
        """Single value returns degenerate CI."""
        result = compute_reachability_ci([0.5])
        assert result["method"] == "single_value"
        assert result["ci_95"] == (0.5, 0.5)

    def test_ci_empty_returns_none(self):
        """Empty list returns None values."""
        result = compute_reachability_ci([])
        assert result["mean"] is None
        assert result["ci_95"] is None
