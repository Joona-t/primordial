"""Integration tests for the AG2 forge adapter.

Validates AG2ForgeAdapter against all forge structural guarantees:
  1. Null discipline: every absent output carries typed absence state
  2. Provenance: all artifacts reachable from chamber root (reversibility >= 0.95)
  3. Trace integrity: sealed chambers round-trip losslessly (hash_match = True)
  4. Fault injection: injected structural violations are detected
  5. Multi-agent scenarios: GroupChat produces valid provenance DAGs

Phase 8, Plan 01 of Primordial v2.0 (RQ4: cross-architecture generalization).
Target: >= 30 tests, all passing.
"""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from forge_adapter import AG2ForgeAdapter, InterceptionEvent
from forge_nulls import AbsenceState
from forge_chamber import validate_chamber, create_chamber, register_stage, seal_chamber
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from findings_ledger import FindingsLedger, Finding
from ag2_integration_harness import (
    AG2ForgeHarness,
    MockConversableAgent,
    MockGroupChat,
    MockHookList,
    SimpleConversation,
    ToolUseSession,
    MultiAgentGroupChat,
    ErrorAndAbsence,
    CompactionTrigger,
    SCENARIOS,
    compute_reversibility,
    run_all_scenarios,
)


# ============================================================
# 1. Null Discipline Tests (8 tests)
# ============================================================

class TestNullDiscipline(unittest.TestCase):
    """Validate that every absent output carries a typed absence state."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def _make_adapter(self, run_id="test-null"):
        adapter = AG2ForgeAdapter(run_id=run_id, ledger=self.ledger)
        adapter.start_session()
        return adapter

    def test_present_output_no_absence_state(self):
        """output present -> no absence state on artifact."""
        adapter = self._make_adapter("test-present")
        adapter.on_turn("agent", "prompt", "Hello world")
        result = adapter.end_session()
        # Artifact should have output present, no output_state
        chamber = adapter._chamber
        art = chamber["stages"][0]["artifact"]
        self.assertIsNotNone(art.get("output"))
        self.assertNotIn("output_state", art)

    def test_none_output_gets_not_generated(self):
        """output=None -> output_state='not_generated'."""
        adapter = self._make_adapter("test-none")
        adapter.on_turn("agent", "prompt", None)
        result = adapter.end_session()
        chamber = adapter._chamber
        art = chamber["stages"][0]["artifact"]
        self.assertIsNone(art.get("output"))
        self.assertEqual(art.get("output_state"), "not_generated")

    def test_empty_string_handling(self):
        """output='' -> treated as present (empty string is not absent)."""
        adapter = self._make_adapter("test-empty-str")
        adapter.on_turn("agent", "prompt", "")
        result = adapter.end_session()
        # Should succeed with 0 validation errors
        self.assertEqual(len(result["validation_errors"]), 0)
        chamber = adapter._chamber
        art = chamber["stages"][0]["artifact"]
        # Empty string converted to sentinel
        self.assertEqual(art.get("output"), "<empty_response>")
        self.assertNotIn("output_state", art)

    def test_tool_call_none_output(self):
        """tool returns None -> typed absence on tool artifact."""
        adapter = self._make_adapter("test-tool-none")
        adapter.on_turn("agent", "q", "starting")
        adapter.on_tool_call("agent", "search", "query", None)
        result = adapter.end_session()
        chamber = adapter._chamber
        tool_art = chamber["stages"][1]["artifact"]
        self.assertIsNone(tool_art.get("output"))
        self.assertEqual(tool_art.get("output_state"), "not_generated")

    def test_error_gets_invalid_state(self):
        """on_error -> output_state='invalid'."""
        adapter = self._make_adapter("test-error-state")
        adapter.on_turn("agent", "q", "ok")
        adapter.on_error("agent", RuntimeError("test error"))
        result = adapter.end_session()
        chamber = adapter._chamber
        error_art = chamber["stages"][1]["artifact"]
        self.assertIsNone(error_art.get("output"))
        self.assertEqual(error_art.get("output_state"), "invalid")

    def test_multi_agent_mixed_outputs(self):
        """4 agents, mix of present/None -> correct states on each."""
        adapter = self._make_adapter("test-mixed")
        adapter.on_turn("a1", "q", "present output")
        adapter.on_turn("a2", "q", None)
        adapter.on_turn("a3", "q", "also present")
        adapter.on_turn("a4", "q", None)
        result = adapter.end_session()

        chamber = adapter._chamber
        self.assertEqual(len(chamber["stages"]), 4)

        # a1: present
        self.assertIsNotNone(chamber["stages"][0]["artifact"].get("output"))
        self.assertNotIn("output_state", chamber["stages"][0]["artifact"])

        # a2: absent
        self.assertIsNone(chamber["stages"][1]["artifact"].get("output"))
        self.assertEqual(chamber["stages"][1]["artifact"].get("output_state"), "not_generated")

        # a3: present
        self.assertIsNotNone(chamber["stages"][2]["artifact"].get("output"))

        # a4: absent
        self.assertIsNone(chamber["stages"][3]["artifact"].get("output"))
        self.assertEqual(chamber["stages"][3]["artifact"].get("output_state"), "not_generated")

    def test_validate_chamber_zero_errors(self):
        """Sealed chamber passes validate_chamber() with 0 errors."""
        harness = AG2ForgeHarness(run_id="test-validate-zero", ledger=self.ledger)
        result = harness.run_scenario(SimpleConversation())
        self.assertEqual(len(result["validation_errors"]), 0)

    def test_no_bare_nones_in_chamber(self):
        """Scan all artifacts for bare None without state."""
        harness = AG2ForgeHarness(run_id="test-no-bare-none", ledger=self.ledger)
        result = harness.run_scenario(ErrorAndAbsence())
        chamber = result["chamber"]

        for stage in chamber["stages"]:
            art = stage["artifact"]
            # If output is None, output_state must be present
            if art.get("output") is None:
                self.assertIn("output_state", art,
                    f"Bare None in {stage['stage_id']}: output=None without output_state")
            # If output is present, output_state must NOT be present
            if art.get("output") is not None:
                self.assertNotIn("output_state", art,
                    f"Conflicting state in {stage['stage_id']}: output present with output_state")


# ============================================================
# 2. Provenance Tests (6 tests)
# ============================================================

class TestProvenance(unittest.TestCase):
    """Validate provenance chains and reversibility."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_sequential_turns_form_chain(self):
        """Each artifact refs previous (linear chain)."""
        adapter = AG2ForgeAdapter(run_id="test-chain", ledger=self.ledger)
        adapter.start_session()
        a1 = adapter.on_turn("a", "q1", "r1")
        a2 = adapter.on_turn("b", "q2", "r2")
        a3 = adapter.on_turn("c", "q3", "r3")
        adapter.end_session()

        chamber = adapter._chamber
        # Stage 1 should ref Stage 0
        refs_1 = [r["ref"] for r in chamber["stages"][1]["artifact"]["refs"]]
        self.assertIn(a1, refs_1)
        # Stage 2 should ref Stage 1
        refs_2 = [r["ref"] for r in chamber["stages"][2]["artifact"]["refs"]]
        self.assertIn(a2, refs_2)

    def test_tool_call_refs_parent_turn(self):
        """Tool artifact refs the turn that invoked it."""
        adapter = AG2ForgeAdapter(run_id="test-tool-ref", ledger=self.ledger)
        adapter.start_session()
        turn_id = adapter.on_turn("agent", "q", "response")
        tool_id = adapter.on_tool_call("agent", "search", "query", "results")
        adapter.end_session()

        chamber = adapter._chamber
        tool_refs = [r["ref"] for r in chamber["stages"][1]["artifact"]["refs"]]
        self.assertIn(turn_id, tool_refs)

    def test_compaction_refs_all_prior(self):
        """Compaction artifact refs all pre-compaction artifacts."""
        adapter = AG2ForgeAdapter(run_id="test-compact-refs", ledger=self.ledger)
        adapter.start_session()
        a1 = adapter.on_turn("a", "q1", "r1")
        a2 = adapter.on_turn("b", "q2", "r2")
        a3 = adapter.on_turn("c", "q3", "r3")
        comp_id = adapter.on_compaction("full history", "summary")
        adapter.end_session()

        chamber = adapter._chamber
        comp_stage = chamber["stages"][3]
        comp_refs = [r["ref"] for r in comp_stage["artifact"]["refs"]]
        # Should ref all 3 prior artifacts
        self.assertIn(a1, comp_refs)
        self.assertIn(a2, comp_refs)
        self.assertIn(a3, comp_refs)

    def test_all_reach_root(self):
        """BFS from every artifact reaches chamber root."""
        harness = AG2ForgeHarness(run_id="test-reach-root", ledger=self.ledger)
        result = harness.run_scenario(SimpleConversation())
        rev = compute_reversibility(result["chamber"])
        self.assertTrue(rev["all_reach_root"])

    def test_reversibility_score_above_threshold(self):
        """reversibility_score >= 0.95 for all scenarios."""
        for name, scenario in SCENARIOS.items():
            with self.subTest(scenario=name):
                harness = AG2ForgeHarness(run_id=f"test-rev-{name}", ledger=self.ledger)
                result = harness.run_scenario(scenario)
                rev = compute_reversibility(result["chamber"])
                self.assertGreaterEqual(rev["score"], 0.95,
                    f"Reversibility {rev['score']:.2f} < 0.95 for {name}")

    def test_multi_agent_provenance_graph(self):
        """4-agent scenario maintains valid DAG (not just linear chain)."""
        harness = AG2ForgeHarness(run_id="test-dag", ledger=self.ledger)
        result = harness.run_scenario(MultiAgentGroupChat())
        chamber = result["chamber"]

        # Verify it's a valid DAG: no artifact refs itself
        for stage in chamber["stages"]:
            art = stage["artifact"]
            stage_id = stage["stage_id"]
            for ref_entry in art.get("refs", []):
                if isinstance(ref_entry, dict):
                    self.assertNotEqual(ref_entry.get("ref"), stage_id,
                        f"Self-reference in {stage_id}")

        # Verify all refs point to existing artifacts
        valid_ids = chamber["artifact_index"]
        for stage in chamber["stages"]:
            for ref_entry in stage["artifact"].get("refs", []):
                if isinstance(ref_entry, dict) and ref_entry.get("state") == "resolved":
                    self.assertIn(ref_entry["ref"], valid_ids,
                        f"Dangling ref: {ref_entry['ref']}")


# ============================================================
# 3. Trace Integrity Tests (4 tests)
# ============================================================

class TestTraceIntegrity(unittest.TestCase):
    """Validate trace encoding/decoding round-trips."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_encode_decode_roundtrip(self):
        """encode_trace + verify_trace -> hash_match=True."""
        harness = AG2ForgeHarness(run_id="test-roundtrip", ledger=self.ledger)
        result = harness.run_scenario(SimpleConversation())
        chamber = result["chamber"]

        trace = encode_trace(chamber)
        verification = verify_trace(trace, chamber)
        self.assertTrue(verification["hash_match"])
        self.assertTrue(verification["content_match"])
        self.assertTrue(verification["valid"])

    def test_trace_stats_reasonable(self):
        """Trace has expected number of stages."""
        harness = AG2ForgeHarness(run_id="test-stats", ledger=self.ledger)
        result = harness.run_scenario(MultiAgentGroupChat())
        chamber = result["chamber"]

        trace = encode_trace(chamber)
        stats = trace_stats(trace)
        self.assertEqual(stats["stage_count"], 10)
        self.assertGreaterEqual(stats["compression_ratio"], 1.0)

    def test_sealed_chamber_trace_valid(self):
        """Only sealed chambers produce valid traces (verify all scenarios)."""
        for name, scenario in SCENARIOS.items():
            with self.subTest(scenario=name):
                harness = AG2ForgeHarness(run_id=f"test-sealed-{name}", ledger=self.ledger)
                result = harness.run_scenario(scenario)
                self.assertTrue(result["trace_verified"],
                    f"Trace not verified for {name}")

    def test_multiple_sessions_independent(self):
        """Two AG2 sessions produce independent chambers."""
        h1 = AG2ForgeHarness(run_id="session-1", ledger=self.ledger)
        h2 = AG2ForgeHarness(run_id="session-2", ledger=self.ledger)

        r1 = h1.run_scenario(SimpleConversation())
        r2 = h2.run_scenario(ToolUseSession())

        # Different chamber IDs
        c1 = r1["chamber"]
        c2 = r2["chamber"]
        self.assertNotEqual(c1["chamber_id"], c2["chamber_id"])

        # Different artifact IDs (no cross-contamination)
        ids1 = {s["stage_id"] for s in c1["stages"]}
        ids2 = {s["stage_id"] for s in c2["stages"]}
        self.assertEqual(len(ids1 & ids2), 0, "Sessions share artifact IDs")


# ============================================================
# 4. Fault Injection Tests (6 tests)
# ============================================================

class TestFaultInjection(unittest.TestCase):
    """Validate that injected structural violations are detected."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def _build_clean_chamber(self):
        """Build a clean 3-stage chamber for fault injection."""
        adapter = AG2ForgeAdapter(run_id="test-fault", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("a", "q1", "r1")
        adapter.on_turn("b", "q2", "r2")
        adapter.on_turn("c", "q3", "r3")
        adapter.end_session()
        return adapter._chamber

    def test_d1_null_collapse_detected(self):
        """Inject bare None (no state) -> violation detected by adapter."""
        adapter = AG2ForgeAdapter(run_id="test-d1", ledger=self.ledger)
        adapter.start_session()
        # Manually craft event with bare None (bypassing adapter protection)
        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="agent",
            output_data=None,
            output_state=None,  # D1: no typed absence state
        )
        adapter._events.append(event)
        adapter._check_violation(event)
        # Should detect D1
        d1_violations = [v for v in adapter._violations if v["type"] == "D1"]
        self.assertGreater(len(d1_violations), 0)

    def test_d2_broken_provenance_detected(self):
        """Inject ref to nonexistent artifact -> validation error."""
        chamber = self._build_clean_chamber()
        # Tamper: add a ref to nonexistent artifact
        chamber["stages"][1]["artifact"]["refs"].append(
            {"ref": "artifact:nonexistent:fake:id:r1", "state": "resolved"}
        )
        errors = validate_chamber(chamber)
        ref_errors = [e for e in errors if "REF" in e.get("code", "")]
        self.assertGreater(len(ref_errors), 0)

    def test_d5_missing_state_label_detected(self):
        """Inject dict with None values, no _state -> detected."""
        adapter = AG2ForgeAdapter(run_id="test-d5", ledger=self.ledger)
        adapter.start_session()
        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="agent",
            output_data={"result": None},  # bare None without result_state
        )
        adapter._events.append(event)
        adapter._check_violation(event)
        d5_violations = [v for v in adapter._violations if v["type"] == "D5"]
        self.assertGreater(len(d5_violations), 0)

    def test_fault_on_sealed_chamber(self):
        """Inject fault before seal -> validation catches it."""
        adapter = AG2ForgeAdapter(run_id="test-seal-fault", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("a", "q", "r")
        adapter.on_turn("b", "q", "r")
        # Tamper before seal: corrupt stage index
        adapter._chamber["stages"][1]["stage_index"] = 999
        seal_chamber(adapter._chamber)
        errors = validate_chamber(adapter._chamber)
        index_errors = [e for e in errors if "INDEX" in e.get("code", "")]
        self.assertGreater(len(index_errors), 0)

    def test_clean_session_zero_violations(self):
        """Well-formed session -> 0 violations."""
        adapter = AG2ForgeAdapter(run_id="test-clean", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("a", "q1", "r1")
        adapter.on_turn("b", "q2", "r2")
        adapter.on_turn("c", "q3", "r3")
        result = adapter.end_session()
        self.assertEqual(result["violations_detected"], 0)
        self.assertEqual(len(result["validation_errors"]), 0)

    def test_violation_types_recorded(self):
        """Violations include type and description."""
        adapter = AG2ForgeAdapter(run_id="test-viol-types", ledger=self.ledger)
        adapter.start_session()
        # Inject D1
        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="agent",
            output_data=None,
            output_state=None,
        )
        adapter._events.append(event)
        adapter._check_violation(event)

        self.assertGreater(len(adapter._violations), 0)
        for v in adapter._violations:
            self.assertIn("type", v)
            self.assertIn("description", v)
            self.assertIsInstance(v["type"], str)
            self.assertIsInstance(v["description"], str)


# ============================================================
# 5. Multi-Agent Scenario Tests (6 tests)
# ============================================================

class TestMultiAgentScenarios(unittest.TestCase):
    """Validate multi-agent GroupChat scenarios."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_groupchat_4_agents_10_turns(self):
        """Full scenario produces valid chamber."""
        harness = AG2ForgeHarness(run_id="test-gc4", ledger=self.ledger)
        result = harness.run_scenario(MultiAgentGroupChat())
        self.assertEqual(result["session_result"]["total_stages"], 10)
        self.assertEqual(len(result["validation_errors"]), 0)
        self.assertTrue(result["trace_verified"])

    def test_speaker_selection_all_agents(self):
        """All agents appear in artifact seats."""
        harness = AG2ForgeHarness(run_id="test-speakers", ledger=self.ledger)
        result = harness.run_scenario(MultiAgentGroupChat())
        chamber = result["chamber"]

        seats = {stage["seat"] for stage in chamber["stages"]}
        # Round-robin with 4 agents over 10 turns: all should appear
        expected = {"architect", "builder", "tester", "reviewer"}
        self.assertEqual(seats, expected)

    def test_conversation_ordering_preserved(self):
        """Artifact timestamps monotonically increase."""
        harness = AG2ForgeHarness(run_id="test-order", ledger=self.ledger)
        result = harness.run_scenario(MultiAgentGroupChat())
        chamber = result["chamber"]

        timestamps = [s["registered_at"] for s in chamber["stages"]]
        for i in range(1, len(timestamps)):
            self.assertGreaterEqual(timestamps[i], timestamps[i-1],
                f"Timestamps not monotonic at index {i}")

    def test_metrics_reflect_session(self):
        """get_metrics() returns correct counts."""
        adapter = AG2ForgeAdapter(run_id="test-metrics", ledger=self.ledger)
        adapter.start_session()  # records 1 lifecycle event
        adapter.on_turn("a", "q1", "r1")
        adapter.on_turn("b", "q2", "r2")
        adapter.on_tool_call("a", "search", "q", "results")

        metrics = adapter.get_metrics()
        self.assertEqual(metrics["framework"], "ag2")
        self.assertEqual(metrics["stages"], 3)
        # events = 1 lifecycle (start) + 3 interception = 4
        self.assertEqual(metrics["events"], 4)
        self.assertEqual(len(metrics["artifact_ids"]), 3)

        adapter.end_session()

    def test_findings_ledger_integration(self):
        """Violations logged to FindingsLedger."""
        adapter = AG2ForgeAdapter(run_id="test-ledger", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("agent", "q", "response")
        adapter.end_session()

        findings = self.ledger.query(tag="XARCH-01")
        self.assertGreater(len(findings), 0)
        # Check finding structure (records wrap the Finding in a 'finding' key)
        for record in findings:
            finding = record.get("finding", record)
            self.assertIn("title", finding)
            self.assertIn("evidence", finding)

    def test_end_session_returns_complete_results(self):
        """All required fields in result dict."""
        adapter = AG2ForgeAdapter(run_id="test-complete", ledger=self.ledger)
        adapter.start_session()
        adapter.on_turn("agent", "q", "response")
        result = adapter.end_session()

        required_keys = [
            "run_id", "framework", "total_stages", "total_events",
            "violations_detected", "validation_errors", "trace_stats",
            "trace_verified", "timestamp",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")


# ============================================================
# 6. Anchor Comparison Tests (2 tests)
# ============================================================

class TestAnchorComparison(unittest.TestCase):
    """Compare AG2 adapter metrics against reference implementations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_ag2_reversibility_matches_openclaw_level(self):
        """AG2 reversibility comparable to OpenClaw adapter results.

        Reference: OpenClaw adapter (Phase 2 INTG-01) achieved 100% provenance
        reachability on well-formed sessions. AG2 should match.
        """
        results = run_all_scenarios(ledger=self.ledger)
        for name, result in results.items():
            with self.subTest(scenario=name):
                rev = compute_reversibility(result["chamber"])
                # OpenClaw baseline: 100% reversibility on clean sessions
                self.assertGreaterEqual(rev["score"], 0.95,
                    f"AG2 reversibility {rev['score']:.2f} below OpenClaw level for {name}")

    def test_ag2_trace_integrity_matches_mock_experiment(self):
        """AG2 trace integrity matches MockLM experiment results.

        Reference: MockLM experiment (Phase 2-5) achieved 100% trace integrity
        (hash_match=True) on all sessions. AG2 should match.
        """
        results = run_all_scenarios(ledger=self.ledger)
        for name, result in results.items():
            with self.subTest(scenario=name):
                self.assertTrue(result["trace_verified"],
                    f"AG2 trace not verified for {name}, "
                    f"MockLM baseline: 100% trace integrity")


# ============================================================
# 7. Harness Component Tests (4 tests)
# ============================================================

class TestHarnessComponents(unittest.TestCase):
    """Test mock AG2 framework components independently."""

    def test_mock_hook_list_registration(self):
        """Hooks register and fire correctly."""
        hooks = MockHookList()
        results = []
        hooks.register_hook("safeguard_llm_outputs", lambda x: (results.append(x), x)[1])
        output = hooks.fire("safeguard_llm_outputs", "test value")
        self.assertEqual(output, "test value")
        self.assertEqual(results, ["test value"])

    def test_mock_hook_list_rejects_unknown(self):
        """Unknown hook names are rejected."""
        hooks = MockHookList()
        with self.assertRaises(ValueError):
            hooks.register_hook("nonexistent_hook", lambda x: x)

    def test_mock_agent_generate_reply(self):
        """Agent generates reply with hook firing."""
        fired_hooks = []
        agent = MockConversableAgent(
            "test", "assistant",
            reply_fn=lambda msgs: "test reply"
        )
        agent.hook_list.register_hook(
            "safeguard_llm_outputs",
            lambda x: (fired_hooks.append("llm_out"), x)[1]
        )
        reply = agent.generate_reply([])
        self.assertEqual(reply, "test reply")
        self.assertIn("llm_out", fired_hooks)

    def test_mock_groupchat_round_robin(self):
        """GroupChat round-robin covers all agents."""
        agents = [MockConversableAgent(n, n) for n in ["a", "b", "c"]]
        gc = MockGroupChat(agents, max_turns=6)
        messages = gc.run("start", "system")
        # All agents should have spoken at least once
        speakers = {m["sender"] for m in messages if m["sender"] != "system"}
        self.assertEqual(speakers, {"a", "b", "c"})


if __name__ == "__main__":
    unittest.main()
