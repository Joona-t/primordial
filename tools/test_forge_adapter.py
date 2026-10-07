"""Tests for forge_adapter.py — ForgeAdapter ABC, AG2, and LangGraph adapters."""

import tempfile
import unittest

from forge_adapter import (
    InterceptionEvent,
    ForgeAdapter,
    AG2ForgeAdapter,
    LangGraphForgeAdapter,
)
from forge_nulls import AbsenceState
from findings_ledger import FindingsLedger


class TestAG2Adapter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)
        self.adapter = AG2ForgeAdapter(run_id="test-ag2", ledger=self.ledger)

    def test_session_lifecycle(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "hello", "world")
        result = self.adapter.end_session()
        self.assertEqual(result["framework"], "ag2")
        self.assertEqual(result["total_stages"], 1)
        self.assertTrue(result["trace_verified"])
        self.assertEqual(len(result["validation_errors"]), 0)

    def test_multi_turn(self):
        self.adapter.start_session()
        self.adapter.on_turn("architect", "design", "plan A")
        self.adapter.on_turn("builder", "implement", "code here")
        self.adapter.on_turn("critic", "review", "looks good")
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 3)

    def test_tool_call(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "q", "response")
        aid = self.adapter.on_tool_call("agent", "search", "query", "results")
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 2)
        self.assertIn("tool-search", aid)

    def test_none_output_typed_as_absent(self):
        self.adapter.start_session()
        aid = self.adapter.on_turn("agent", "prompt", None)
        result = self.adapter.end_session()
        # Should succeed — None output is properly typed
        self.assertEqual(result["total_stages"], 1)
        self.assertEqual(len(result["validation_errors"]), 0)

    def test_error_handling(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "q", "ok")
        aid = self.adapter.on_error("agent", RuntimeError("test error"))
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 2)

    def test_compaction(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "q1", "long output 1")
        self.adapter.on_turn("agent", "q2", "long output 2")
        self.adapter.on_compaction("full history", "summary")
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 3)

    def test_findings_logged(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "q", "response")
        self.adapter.end_session()
        findings = self.ledger.query(tag="XARCH-01")
        self.assertGreater(len(findings), 0)

    def test_metrics(self):
        self.adapter.start_session()
        self.adapter.on_turn("agent", "q", "response")
        metrics = self.adapter.get_metrics()
        self.assertEqual(metrics["framework"], "ag2")
        self.assertEqual(metrics["stages"], 1)

    def test_artifact_ref_chain(self):
        self.adapter.start_session()
        aid1 = self.adapter.on_turn("a", "q1", "r1")
        aid2 = self.adapter.on_turn("b", "q2", "r2")
        aid3 = self.adapter.on_turn("c", "q3", "r3")
        # Each should ref the previous
        metrics = self.adapter.get_metrics()
        self.assertEqual(len(metrics["artifact_ids"]), 3)

    def test_no_session_raises(self):
        with self.assertRaises(RuntimeError):
            self.adapter.on_turn("agent", "q", "r")


class TestLangGraphAdapter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)
        self.adapter = LangGraphForgeAdapter(run_id="test-lg", ledger=self.ledger)

    def test_session_lifecycle(self):
        self.adapter.start_session()
        self.adapter.on_turn("classify_node", {"input": "text"}, {"label": "spam"})
        result = self.adapter.end_session()
        self.assertEqual(result["framework"], "langgraph")
        self.assertTrue(result["trace_verified"])

    def test_dict_output_serialized(self):
        self.adapter.start_session()
        self.adapter.on_turn("node", None, {"key": "value", "nested": [1, 2]})
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 1)

    def test_tool_call(self):
        self.adapter.start_session()
        self.adapter.on_tool_call("agent_node", "search", "query", "results")
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 1)

    def test_compaction(self):
        self.adapter.start_session()
        self.adapter.on_turn("n1", None, "output")
        self.adapter.on_compaction("long original", "short summary")
        result = self.adapter.end_session()
        self.assertEqual(result["total_stages"], 2)


class TestViolationDetection(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_d5_bare_none_in_dict(self):
        adapter = AG2ForgeAdapter(run_id="test-d5", ledger=self.ledger)
        adapter.start_session()
        # Manually craft an event with bare None in dict output
        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="agent",
            output_data={"result": None},  # bare None without result_state
        )
        adapter._events.append(event)
        adapter._check_violation(event)
        self.assertGreater(len(adapter._violations), 0)
        self.assertEqual(adapter._violations[0]["type"], "D5")

    def test_no_violation_on_clean_output(self):
        adapter = AG2ForgeAdapter(run_id="test-clean", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("agent", "q", "clean response")
        self.assertEqual(len(adapter._violations), 0)


class TestEdgeCases(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_empty_session(self):
        adapter = AG2ForgeAdapter(run_id="test-empty", ledger=self.ledger)
        adapter.start_session()
        result = adapter.end_session()
        self.assertEqual(result["total_stages"], 0)
        self.assertTrue(result["trace_verified"])

    def test_end_without_start(self):
        adapter = AG2ForgeAdapter(run_id="test-nostart", ledger=self.ledger)
        result = adapter.end_session()
        self.assertIn("error", result)

    def test_many_turns(self):
        adapter = AG2ForgeAdapter(run_id="test-many", ledger=self.ledger)
        adapter.start_session()
        for i in range(50):
            adapter.on_turn(f"agent-{i%3}", f"prompt {i}", f"response {i}")
        result = adapter.end_session()
        self.assertEqual(result["total_stages"], 50)
        self.assertTrue(result["trace_verified"])


if __name__ == "__main__":
    unittest.main()
