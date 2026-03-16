"""
test_openclaw_adapter.py -- Unit tests for the OpenClaw forge integration adapter.

Tests cover all 4 interception points:
1. Per-turn registration (task lifecycle -> forge artifacts)
2. Per-tool-call registration (patch events -> child artifacts)
3. Cursor advancement detection (state loss -> forge compaction artifacts)
4. Chamber lifecycle (create -> register -> seal)

Plus: typed absence, provenance chain, validate_chamber, reversibility,
and post-hoc ledger processing against real sample data.

Plan: 02-02 (Adapter Build and Validation)
Phase: 02-integration-and-baseline-establishment
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent))

from forge_chamber import (
    ForgeChamberError,
    validate_chamber,
)
from forge_nulls import AbsenceState
from openclaw_adapter import (
    OpenClawAdapter,
    compute_provenance_depth,
    compute_reversibility_score,
    group_events_by_task,
    parse_ledger_events,
    process_ledger,
    run_openclaw_analysis,
)

# Path to real sample ledger from integration_samples
SAMPLE_LEDGER = str(
    Path(__file__).parent.parent / "integration_samples" / "openclaw" / "queue_ledger.sample.jsonl"
)


# ---------------------------------------------------------------------------
# Test: Chamber creation (adapter creates valid chamber with correct ID format)
# ---------------------------------------------------------------------------


class TestChamberCreation(unittest.TestCase):
    """Adapter creates valid chamber with correct ID format."""

    def test_chamber_id_format(self):
        adapter = OpenClawAdapter("test_session_001")
        self.assertEqual(adapter.chamber["chamber_id"], "chamber:openclaw:test_session_001:v1")

    def test_chamber_starts_open(self):
        adapter = OpenClawAdapter("test_open")
        self.assertEqual(adapter.chamber["status"], "open")

    def test_chamber_has_schema_version(self):
        adapter = OpenClawAdapter("test_schema")
        self.assertEqual(adapter.chamber["schema_version"], "forge.internal.v1")

    def test_chamber_starts_with_empty_stages(self):
        adapter = OpenClawAdapter("test_empty")
        self.assertEqual(len(adapter.chamber["stages"]), 0)

    def test_session_id_property(self):
        adapter = OpenClawAdapter("test_sid")
        self.assertEqual(adapter.session_id, "test_sid")


# ---------------------------------------------------------------------------
# Test: Per-turn artifacts (3 turns, correct source_refs chain)
# ---------------------------------------------------------------------------


class TestPerTurnArtifacts(unittest.TestCase):
    """Simulate 3 turns, verify source_refs chain and artifact structure."""

    def setUp(self):
        self.adapter = OpenClawAdapter("test_turns")
        self.art0 = self.adapter.register_task("t0", output="first output", ok=True, detail="write_file")
        self.art1 = self.adapter.register_task("t1", output="second output", ok=True, detail="exec")
        self.art2 = self.adapter.register_task("t2", output="third output", ok=True, detail="patch")

    def test_three_artifacts_in_chamber(self):
        self.assertEqual(len(self.adapter.chamber["stages"]), 3)

    def test_artifact_id_format(self):
        self.assertEqual(self.art0, "artifact:openclaw:test_turns:iter:0:r1")
        self.assertEqual(self.art1, "artifact:openclaw:test_turns:iter:1:r1")
        self.assertEqual(self.art2, "artifact:openclaw:test_turns:iter:2:r1")

    def test_turn_0_has_no_refs(self):
        """First turn should have no source_refs (it is the root)."""
        art = self.adapter.chamber["stages"][0]["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        self.assertEqual(len(resolved_refs), 0)

    def test_turn_1_refs_turn_0(self):
        """Second turn should reference first turn."""
        art = self.adapter.chamber["stages"][1]["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        self.assertIn(self.art0, resolved_refs)

    def test_turn_2_refs_turn_1(self):
        """Third turn should reference second turn (not first)."""
        art = self.adapter.chamber["stages"][2]["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        self.assertIn(self.art1, resolved_refs)
        self.assertNotIn(self.art0, resolved_refs)

    def test_each_artifact_has_output(self):
        for i, stage in enumerate(self.adapter.chamber["stages"]):
            art = stage["artifact"]
            self.assertIsNotNone(art.get("output"), f"Stage {i} has no output")
            self.assertEqual(art["status"], "complete")

    def test_each_artifact_has_summary(self):
        for i, stage in enumerate(self.adapter.chamber["stages"]):
            self.assertIsNotNone(stage.get("summary"), f"Stage {i} has no summary")


# ---------------------------------------------------------------------------
# Test: Tool call artifacts (patch events reference parent iteration)
# ---------------------------------------------------------------------------


class TestToolCallArtifacts(unittest.TestCase):
    """Simulate a turn with 2 tool calls, verify refs to parent."""

    def setUp(self):
        self.adapter = OpenClawAdapter("test_patches")
        self.task_art = self.adapter.register_task("t1", output="task output", ok=True)
        self.patch0 = self.adapter.register_patch(
            "diff1.patch", "patch.proposed",
            parent_task_artifact=self.task_art,
            detail="proposed",
        )
        self.patch1 = self.adapter.register_patch(
            "diff2.patch", "patch.applied",
            parent_task_artifact=self.task_art,
            detail="applied",
            meta={"touched_files": ["a.py"], "pre_validate": "pass", "post_validate": "pass"},
        )

    def test_patch_artifacts_ref_parent_iteration(self):
        """Both patch artifacts should reference the parent task."""
        for stage_idx in [1, 2]:  # stages 1 and 2 are patches
            art = self.adapter.chamber["stages"][stage_idx]["artifact"]
            resolved_refs = [
                r["ref"] for r in art.get("refs", [])
                if isinstance(r, dict) and r.get("state") == "resolved"
            ]
            self.assertIn(self.task_art, resolved_refs,
                          f"Patch stage {stage_idx} should ref parent task")

    def test_subcall_counter_increments(self):
        self.assertEqual(self.patch0, "artifact:openclaw:test_patches:subcall:0:r1")
        self.assertEqual(self.patch1, "artifact:openclaw:test_patches:subcall:1:r1")

    def test_patch_output_contains_kind(self):
        art0 = self.adapter.chamber["stages"][1]["artifact"]
        self.assertIn("patch.proposed", art0["output"])
        art1 = self.adapter.chamber["stages"][2]["artifact"]
        self.assertIn("patch.applied", art1["output"])

    def test_patch_with_default_parent(self):
        """If no parent_task_artifact given, uses most recent task."""
        adapter = OpenClawAdapter("test_default_parent")
        task1 = adapter.register_task("t1", output="one", ok=True)
        task2 = adapter.register_task("t2", output="two", ok=True)
        patch = adapter.register_patch("d.patch", "patch.proposed")
        art = adapter.chamber["stages"][2]["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        self.assertIn(task2, resolved_refs, "Should ref most recent task")


# ---------------------------------------------------------------------------
# Test: Cursor advancement (compaction artifact with refs to compacted items)
# ---------------------------------------------------------------------------


class TestCursorAdvancement(unittest.TestCase):
    """Simulate cursor advancement after 5 turns, verify compaction artifact."""

    def setUp(self):
        self.adapter = OpenClawAdapter("test_cursor")
        self.task_arts = []
        for i in range(5):
            art = self.adapter.register_task(f"t{i}", output=f"output_{i}", ok=True)
            self.task_arts.append(art)
        self.compact_art = self.adapter.register_cursor_advancement(
            old_cursor=0,
            new_cursor=500,
            task_ids_behind_cursor=self.task_arts,
        )

    def test_compaction_artifact_refs_all_5_tasks(self):
        """Cursor advancement artifact should ref all 5 compacted iterations."""
        compact_stage = self.adapter.chamber["stages"][5]
        art = compact_stage["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        for task_art in self.task_arts:
            self.assertIn(task_art, resolved_refs,
                          f"{task_art} should be in cursor advancement refs")

    def test_compaction_artifact_id_format(self):
        self.assertEqual(self.compact_art, "artifact:openclaw:test_cursor:compact:1:r1")

    def test_compaction_output_describes_cursor(self):
        art = self.adapter.chamber["stages"][5]["artifact"]
        self.assertIn("Cursor advanced", art["output"])
        self.assertIn("pruned_recoverable", art["output"])

    def test_multiple_cursor_advancements(self):
        """Multiple cursor advancements get incrementing IDs."""
        compact2 = self.adapter.register_cursor_advancement(
            task_ids_behind_cursor=[self.task_arts[0]],
        )
        self.assertEqual(compact2, "artifact:openclaw:test_cursor:compact:2:r1")

    def test_cursor_advancement_with_default_refs(self):
        """Without explicit task_ids, uses all registered task artifacts."""
        adapter = OpenClawAdapter("test_default_cursor")
        for i in range(3):
            adapter.register_task(f"t{i}", output=f"out_{i}", ok=True)
        compact = adapter.register_cursor_advancement()
        art = adapter.chamber["stages"][3]["artifact"]
        resolved_refs = [
            r["ref"] for r in art.get("refs", [])
            if isinstance(r, dict) and r.get("state") == "resolved"
        ]
        self.assertEqual(len(resolved_refs), 3)


# ---------------------------------------------------------------------------
# Test: NOT_GENERATED state (None output gets typed absence)
# ---------------------------------------------------------------------------


class TestNotGeneratedState(unittest.TestCase):
    """Simulate a turn where LLM produces no output."""

    def test_none_output_gets_not_generated(self):
        adapter = OpenClawAdapter("test_not_gen")
        adapter.register_task("t_fail", output=None, ok=False)
        art = adapter.chamber["stages"][0]["artifact"]
        self.assertIsNone(art["output"])
        self.assertEqual(art["output_state"], "not_generated")

    def test_none_output_ok_true_gets_not_generated(self):
        """Even successful task with no output gets NOT_GENERATED."""
        adapter = OpenClawAdapter("test_not_gen_ok")
        adapter.register_task("t_ok_none", output=None, ok=True)
        art = adapter.chamber["stages"][0]["artifact"]
        self.assertIsNone(art["output"])
        self.assertEqual(art["output_state"], "not_generated")

    def test_present_output_has_no_absence_state(self):
        """Task with output should NOT have output_state."""
        adapter = OpenClawAdapter("test_present")
        adapter.register_task("t_present", output="hello", ok=True)
        art = adapter.chamber["stages"][0]["artifact"]
        self.assertEqual(art["output"], "hello")
        # output_state should not be present (or should be the stop_reason_state etc)
        self.assertNotIn("output_state", art)


# ---------------------------------------------------------------------------
# Test: Chamber validation (validate_chamber returns empty list)
# ---------------------------------------------------------------------------


class TestChamberValidation(unittest.TestCase):
    """After processing a complete task, validate_chamber returns empty list."""

    def test_validate_simple_chamber(self):
        adapter = OpenClawAdapter("test_validate")
        adapter.register_task("t1", output="test", ok=True)
        adapter.register_task("t2", output="test2", ok=True)
        adapter.register_patch("p.diff", "patch.proposed")
        adapter.register_cursor_advancement(task_ids_behind_cursor=[
            "artifact:openclaw:test_validate:iter:0:r1",
        ])
        chamber = adapter.finalize()
        errors = validate_chamber(chamber)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    def test_chamber_status_is_sealed(self):
        adapter = OpenClawAdapter("test_seal")
        adapter.register_task("t1", output="test", ok=True)
        chamber = adapter.finalize()
        self.assertEqual(chamber["status"], "sealed")

    def test_finalize_is_idempotent(self):
        adapter = OpenClawAdapter("test_idempotent")
        adapter.register_task("t1", output="test", ok=True)
        chamber1 = adapter.finalize()
        chamber2 = adapter.finalize()
        self.assertIs(chamber1, chamber2)

    def test_cannot_register_after_finalize(self):
        adapter = OpenClawAdapter("test_sealed_reg")
        adapter.register_task("t1", output="test", ok=True)
        adapter.finalize()
        with self.assertRaises(ForgeChamberError):
            adapter.register_task("t2", output="test2", ok=True)


# ---------------------------------------------------------------------------
# Test: Provenance reachability (compute_reversibility_score = 1.0)
# ---------------------------------------------------------------------------


class TestProvenanceReachability(unittest.TestCase):
    """On a simple 3-turn task, compute_reversibility_score returns 1.0."""

    def test_reversibility_score_simple(self):
        adapter = OpenClawAdapter("test_reach")
        adapter.register_task("t0", output="first", ok=True)
        adapter.register_task("t1", output="second", ok=True)
        adapter.register_task("t2", output="third", ok=True)
        chamber = adapter.finalize()
        score = compute_reversibility_score(chamber)
        self.assertEqual(score, 1.0)

    def test_reversibility_with_patches_and_cursor(self):
        adapter = OpenClawAdapter("test_reach_full")
        art0 = adapter.register_task("t0", output="first", ok=True)
        adapter.register_patch("p.diff", "patch.proposed")
        art1 = adapter.register_task("t1", output="second", ok=True)
        adapter.register_cursor_advancement(task_ids_behind_cursor=[art0])
        chamber = adapter.finalize()
        score = compute_reversibility_score(chamber)
        self.assertEqual(score, 1.0)

    def test_provenance_depth_simple(self):
        adapter = OpenClawAdapter("test_depth")
        adapter.register_task("t0", output="first", ok=True)
        adapter.register_task("t1", output="second", ok=True)
        adapter.register_task("t2", output="third", ok=True)
        chamber = adapter.finalize()
        depth = compute_provenance_depth(chamber)
        self.assertGreaterEqual(depth["max_depth"], 2)
        self.assertTrue(depth["all_reach_root"])

    def test_empty_chamber_reversibility(self):
        adapter = OpenClawAdapter("test_empty_reach")
        chamber = adapter.finalize()
        score = compute_reversibility_score(chamber)
        self.assertEqual(score, 1.0)


# ---------------------------------------------------------------------------
# Test: Ledger parsing
# ---------------------------------------------------------------------------


class TestLedgerParsing(unittest.TestCase):
    """Tests for parse_ledger_events and group_events_by_task."""

    def _write_ledger(self, events: list[dict]) -> str:
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        return path

    def test_parse_valid_ledger(self):
        events = [
            {"ts": "2026-01-01T00:00:00Z", "kind": "task.start", "task_id": "t1"},
            {"ts": "2026-01-01T00:00:01Z", "kind": "task.done", "task_id": "t1", "ok": True},
        ]
        path = self._write_ledger(events)
        try:
            parsed = parse_ledger_events(path)
            self.assertEqual(len(parsed), 2)
            self.assertEqual(parsed[0]["kind"], "task.start")
        finally:
            os.unlink(path)

    def test_parse_missing_field_raises(self):
        events = [
            {"ts": "2026-01-01T00:00:00Z", "kind": "task.start"},  # missing task_id
        ]
        path = self._write_ledger(events)
        try:
            with self.assertRaises(ValueError):
                parse_ledger_events(path)
        finally:
            os.unlink(path)

    def test_parse_empty_lines_skipped(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            f.write("\n")
            f.write(json.dumps({"ts": "T", "kind": "task.start", "task_id": "t1"}) + "\n")
            f.write("\n")
        try:
            parsed = parse_ledger_events(path)
            self.assertEqual(len(parsed), 1)
        finally:
            os.unlink(path)

    def test_group_events_simple(self):
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1"},
            {"ts": "T2", "kind": "task.done", "task_id": "t1", "ok": True},
            {"ts": "T3", "kind": "task.start", "task_id": "t2"},
            {"ts": "T4", "kind": "task.done", "task_id": "t2", "ok": False},
        ]
        groups = group_events_by_task(events)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["task_id"], "t1")
        self.assertTrue(groups[0]["ok"])
        self.assertEqual(groups[1]["task_id"], "t2")
        self.assertFalse(groups[1]["ok"])

    def test_group_events_with_patches(self):
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1"},
            {"ts": "T2", "kind": "patch.proposed", "task_id": "p1"},
            {"ts": "T3", "kind": "patch.applied", "task_id": "p1"},
            {"ts": "T4", "kind": "task.done", "task_id": "t1", "ok": True},
        ]
        groups = group_events_by_task(events)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["events"]), 4)

    def test_group_orphan_patch(self):
        events = [
            {"ts": "T1", "kind": "patch.proposed", "task_id": "p1"},
        ]
        groups = group_events_by_task(events)
        self.assertEqual(len(groups), 1)
        self.assertFalse(groups[0]["started"])

    def test_group_unclosed_task(self):
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1"},
            {"ts": "T2", "kind": "task.start", "task_id": "t2"},
            {"ts": "T3", "kind": "task.done", "task_id": "t2", "ok": True},
        ]
        groups = group_events_by_task(events)
        self.assertEqual(len(groups), 2)
        self.assertFalse(groups[0]["completed"])  # t1 unclosed
        self.assertTrue(groups[1]["completed"])  # t2 closed


# ---------------------------------------------------------------------------
# Test: Post-hoc ledger processing
# ---------------------------------------------------------------------------


class TestProcessLedger(unittest.TestCase):
    """Test process_ledger against synthetic and real data."""

    def _write_ledger(self, events: list[dict]) -> str:
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        return path

    def test_process_simple_ledger(self):
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1", "detail": "test"},
            {"ts": "T2", "kind": "task.done", "task_id": "t1", "ok": True},
        ]
        path = self._write_ledger(events)
        try:
            chamber = process_ledger(path, "simple_test")
            self.assertEqual(chamber["status"], "sealed")
            self.assertGreaterEqual(len(chamber["stages"]), 1)
            errors = validate_chamber(chamber)
            self.assertEqual(errors, [])
        finally:
            os.unlink(path)

    def test_process_ledger_with_patches(self):
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1", "detail": "patch.propose"},
            {"ts": "T2", "kind": "patch.proposed", "task_id": "p1.diff", "detail": "proposed"},
            {"ts": "T3", "kind": "patch.applied", "task_id": "p1.diff", "detail": "applied"},
            {"ts": "T4", "kind": "task.done", "task_id": "t1", "ok": True},
        ]
        path = self._write_ledger(events)
        try:
            chamber = process_ledger(path, "patch_test")
            self.assertEqual(chamber["status"], "sealed")
            # 1 task + 2 patches + 1 cursor advancement = 4 stages
            self.assertGreaterEqual(len(chamber["stages"]), 3)
            errors = validate_chamber(chamber)
            self.assertEqual(errors, [])
        finally:
            os.unlink(path)

    @unittest.skipUnless(os.path.exists(SAMPLE_LEDGER), "Sample ledger not available")
    def test_process_real_sample_ledger(self):
        """Process the real 47-event sample ledger."""
        chamber = process_ledger(SAMPLE_LEDGER, "real_sample")
        self.assertEqual(chamber["status"], "sealed")
        self.assertGreater(len(chamber["stages"]), 10)
        errors = validate_chamber(chamber)
        self.assertEqual(errors, [], f"Validation errors on real ledger: {errors}")
        score = compute_reversibility_score(chamber)
        self.assertEqual(score, 1.0)

    @unittest.skipUnless(os.path.exists(SAMPLE_LEDGER), "Sample ledger not available")
    def test_real_sample_full_analysis(self):
        """Full analysis on real sample data."""
        chamber = process_ledger(SAMPLE_LEDGER, "real_analysis")
        analysis = run_openclaw_analysis(chamber)
        self.assertEqual(analysis["validation_errors"], 0)
        self.assertTrue(analysis["trace_verified"])
        self.assertEqual(analysis["reversibility_score"], 1.0)
        self.assertGreater(analysis["stage_count"], 10)

    def test_process_no_cursor_advancement(self):
        """Test with cursor advancement detection disabled."""
        events = [
            {"ts": "T1", "kind": "task.start", "task_id": "t1", "detail": "test"},
            {"ts": "T2", "kind": "task.done", "task_id": "t1", "ok": True},
        ]
        path = self._write_ledger(events)
        try:
            chamber = process_ledger(path, "no_cursor", detect_cursor_advancement=False)
            # Should have 1 task, no cursor advancement
            task_stages = [s for s in chamber["stages"] if s["seat"] == "openclaw-task"]
            cursor_stages = [s for s in chamber["stages"] if s["seat"] == "openclaw-cursor"]
            self.assertEqual(len(task_stages), 1)
            self.assertEqual(len(cursor_stages), 0)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Test: Error handling and edge cases
# ---------------------------------------------------------------------------


class TestErrorHandling(unittest.TestCase):
    """Test error handling in the adapter."""

    def test_finalize_on_error_preserves_partial(self):
        adapter = OpenClawAdapter("test_error")
        adapter.register_task("t1", output="before error", ok=True)
        error = RuntimeError("test error")
        chamber = adapter.finalize_on_error(error)
        self.assertEqual(chamber["status"], "sealed")
        # Should have original task + error artifact
        self.assertGreaterEqual(len(chamber["stages"]), 1)
        errors = validate_chamber(chamber)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    def test_finalize_on_error_idempotent(self):
        adapter = OpenClawAdapter("test_error_idem")
        adapter.register_task("t1", output="test", ok=True)
        adapter.finalize_on_error(RuntimeError("first"))
        chamber2 = adapter.finalize_on_error(RuntimeError("second"))
        self.assertEqual(chamber2["status"], "sealed")

    def test_parse_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_ledger_events("/nonexistent/path/ledger.jsonl")

    def test_parse_invalid_json(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            f.write("not valid json\n")
        try:
            with self.assertRaises(ValueError):
                parse_ledger_events(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Test: Convention compliance
# ---------------------------------------------------------------------------


class TestConventionCompliance(unittest.TestCase):
    """Verify adapter follows project conventions."""

    def test_artifact_ids_match_convention_5(self):
        """All artifact IDs follow artifact:openclaw:... pattern."""
        import re
        pattern = re.compile(r"^artifact:openclaw:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$")
        adapter = OpenClawAdapter("test_conv")
        adapter.register_task("t1", output="test", ok=True)
        adapter.register_patch("p.diff", "patch.proposed")
        adapter.register_cursor_advancement()
        for stage in adapter.chamber["stages"]:
            art_id = stage["artifact"]["id"]
            self.assertTrue(pattern.match(art_id), f"Bad artifact ID: {art_id}")

    def test_chamber_id_matches_convention_5(self):
        """Chamber ID follows chamber:openclaw:... pattern."""
        import re
        pattern = re.compile(r"^chamber:openclaw:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$")
        adapter = OpenClawAdapter("test_cid")
        self.assertTrue(pattern.match(adapter.chamber["chamber_id"]))

    def test_no_unqualified_compaction_in_source(self):
        """Adapter source code does not use unqualified 'compaction'."""
        import re as _re

        adapter_path = Path(__file__).parent / "openclaw_adapter.py"
        source = adapter_path.read_text(encoding="utf-8")

        # Qualifiers that make a use of 'compaction' acceptable
        qualifiers = [
            "llm compaction", "forge compaction", "trace compression",
            "cursor-based", "compaction artifact", "compaction event",
            "compact:", "compaction characterization", "compaction detection",
            "context-window compaction", "compaction-characterization",
        ]

        # Every use of 'compaction' should be qualified
        for i, line in enumerate(source.split("\n"), 1):
            lower = line.lower()
            if "compaction" not in lower:
                continue
            # Skip code identifiers (_compaction_count, etc.)
            code_stripped = _re.sub(
                r"_compaction_\w+|compaction_count|detect_cursor_advancement",
                "", lower,
            )
            if "compaction" not in code_stripped:
                continue
            # Check for any qualifier
            has_qualifier = any(q in code_stripped for q in qualifiers)
            self.assertTrue(
                has_qualifier,
                f"Line {i} may have unqualified 'compaction': {line.strip()[:80]}",
            )


# ---------------------------------------------------------------------------
# Test: Integration with run_openclaw_analysis
# ---------------------------------------------------------------------------


class TestRunAnalysis(unittest.TestCase):
    """Test the full analysis pipeline."""

    def test_analysis_returns_all_fields(self):
        adapter = OpenClawAdapter("test_analysis")
        adapter.register_task("t0", output="first", ok=True)
        adapter.register_task("t1", output="second", ok=True)
        adapter.register_patch("p.diff", "patch.applied")
        adapter.register_cursor_advancement()
        chamber = adapter.finalize()
        result = run_openclaw_analysis(chamber)

        expected_keys = {
            "validation_errors", "validation_details",
            "trace_verified", "hash_match", "content_match",
            "reversibility_score", "provenance", "overhead",
            "stage_count",
        }
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result["validation_errors"], 0)
        self.assertTrue(result["trace_verified"])
        self.assertEqual(result["reversibility_score"], 1.0)
        self.assertEqual(result["stage_count"], 4)

    def test_analysis_trace_round_trips(self):
        adapter = OpenClawAdapter("test_roundtrip")
        adapter.register_task("t0", output="hello world", ok=True)
        chamber = adapter.finalize()
        result = run_openclaw_analysis(chamber)
        self.assertTrue(result["hash_match"])
        self.assertTrue(result["content_match"])


if __name__ == "__main__":
    unittest.main()
