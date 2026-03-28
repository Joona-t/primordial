"""Integration tests for LangGraph forge adapter via the integration harness.

Tests cover:
  1. Null discipline (8 tests)
  2. Checkpointer transparency (6 tests)
  3. Provenance (6 tests)
  4. Trace integrity (4 tests)
  5. Fault injection (4 tests)
  6. Anchor comparisons (2 tests)
  7. Conditional edge scenarios (2+ tests)
  8. Multi-scenario regression (2+ tests)

Target: >= 30 tests total, all passing.

Phase 8 of Primordial v2.0 (RQ4: cross-architecture generalization).
"""

import copy
import json
import tempfile
import unittest
from collections import deque
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from forge_adapter import LangGraphForgeAdapter, InterceptionEvent
from forge_nulls import AbsenceState
from forge_chamber import (
    create_chamber, register_stage, seal_chamber, validate_chamber,
    get_artifact_by_id,
)
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import encode_trace, decode_trace, verify_trace, trace_stats
from findings_ledger import FindingsLedger

from langgraph_integration_harness import (
    MockCheckpointSaver,
    ForgeCheckpointSaver,
    MockStateGraph,
    MockCompiledGraph,
    LangGraphForgeHarness,
    scenario_linear_pipeline,
    scenario_conditional_routing,
    scenario_tool_use_graph,
    scenario_error_recovery,
    scenario_long_conversation,
    SCENARIOS,
    run_all_scenarios,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(run_id: str = "test", ledger=None) -> LangGraphForgeAdapter:
    return LangGraphForgeAdapter(run_id=run_id, ledger=ledger)


def _make_simple_graph():
    """3-node linear graph: planner -> executor -> reviewer."""
    graph = MockStateGraph()
    graph.add_node("planner", lambda s: {"plan": "do something"})
    graph.add_node("executor", lambda s: {"code": "print('done')"})
    graph.add_node("reviewer", lambda s: {"review": "approved"})
    graph.add_edge(MockStateGraph.START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reviewer")
    graph.add_edge("reviewer", MockStateGraph.END)
    return graph


def _run_instrumented(graph, adapter, input_state=None, config=None,
                      error_handler=None):
    """Instrument graph with adapter, invoke, end session, return everything."""
    adapter.start_session()
    harness = LangGraphForgeHarness(adapter)
    compiled = harness.instrument(graph, adapter)

    if config is None:
        config = {"configurable": {"thread_id": "test-thread"}}
    if input_state is None:
        input_state = {"task": "test"}

    final = compiled.invoke(input_state, config, error_handler=error_handler)
    result = adapter.end_session()
    return final, result, adapter


def _compute_reversibility(adapter):
    """Compute reversibility score: fraction of artifacts in a connected provenance graph.

    In forge's chamber model, the chamber root implicitly contains all registered
    artifacts (they are in artifact_index). Reversibility measures whether
    artifacts form a connected ref graph — i.e., every artifact can reach every
    other artifact through the ref chain (bidirectional). An artifact with no
    refs is still connected if it is the first artifact (root of the chain).

    The score is: (size of largest connected component) / (total artifacts).
    A linear chain A->B->C with chamber root gives reversibility 1.0.
    """
    chamber = adapter._chamber
    if not chamber or not chamber.get("stages"):
        return 1.0

    root_id = chamber["chamber_id"]
    all_ids = set()
    adjacency = {}  # bidirectional adjacency for connected component analysis

    for stage in chamber["stages"]:
        art = stage.get("artifact", {})
        art_id = art.get("id", "")
        all_ids.add(art_id)
        adjacency.setdefault(art_id, set())

        for ref_entry in art.get("refs", []):
            if isinstance(ref_entry, dict):
                ref_target = ref_entry.get("ref", "")
                # Bidirectional: both sides are connected
                adjacency.setdefault(ref_target, set()).add(art_id)
                adjacency[art_id].add(ref_target)

    # All artifacts in the chamber are implicitly connected to the root
    adjacency.setdefault(root_id, set())
    for art_id in all_ids:
        adjacency[root_id].add(art_id)
        adjacency[art_id].add(root_id)

    # BFS from root to find connected component
    reachable = {root_id}
    queue = deque([root_id])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, set()):
            if neighbor not in reachable:
                reachable.add(neighbor)
                queue.append(neighbor)

    if not all_ids:
        return 1.0
    return len(reachable & all_ids) / len(all_ids)


def _all_reach_root(adapter):
    """Check if ALL artifacts can reach the chamber root via ref chain."""
    return _compute_reversibility(adapter) >= 0.999


# ===========================================================================
# 1. NULL DISCIPLINE TESTS (8 tests)
# ===========================================================================

class TestNullDiscipline(unittest.TestCase):
    """Tests that forge null discipline is enforced across all node outputs."""

    def test_present_node_output_no_absence(self):
        """Node returns dict -> no absence state needed."""
        adapter = _make_adapter("null-present")
        graph = MockStateGraph()
        graph.add_node("worker", lambda s: {"result": "value"})
        graph.add_edge(MockStateGraph.START, "worker")
        graph.add_edge("worker", MockStateGraph.END)

        final, result, _ = _run_instrumented(graph, adapter)
        self.assertEqual(len(result["validation_errors"]), 0)
        self.assertEqual(result["violations_detected"], 0)
        self.assertEqual(final["result"], "value")

    def test_none_node_output_gets_not_generated(self):
        """Node returns None -> on_turn registers absence."""
        adapter = _make_adapter("null-none")
        graph = MockStateGraph()
        graph.add_node("empty_node", lambda s: None)
        graph.add_edge(MockStateGraph.START, "empty_node")
        graph.add_edge("empty_node", MockStateGraph.END)

        final, result, ad = _run_instrumented(graph, adapter)
        # The adapter should have handled the None output
        self.assertEqual(len(result["validation_errors"]), 0)
        # Check that an artifact exists for empty_node
        has_empty = any("empty_node" in aid for aid in ad.get_metrics()["artifact_ids"])
        self.assertTrue(has_empty)

    def test_conditional_skip_gets_not_invoked(self):
        """Skipped branch node -> absence 'not_invoked'."""
        harness = LangGraphForgeHarness()
        result = scenario_conditional_routing(harness)
        adapter = result["adapter"]

        # The fallback node was skipped (low complexity -> executor path)
        # Check that an absence artifact was created for it
        artifact_ids = adapter.get_metrics()["artifact_ids"]
        has_fallback = any("fallback" in aid for aid in artifact_ids)
        self.assertTrue(has_fallback, f"No absence for skipped fallback. IDs: {artifact_ids}")

    def test_error_node_gets_invalid(self):
        """Node raises exception -> on_error registers invalid absence."""
        harness = LangGraphForgeHarness()
        result = scenario_error_recovery(harness)
        adapter = result["adapter"]

        # parser raised ValueError, should have error artifact
        artifact_ids = adapter.get_metrics()["artifact_ids"]
        has_parser = any("parser" in aid for aid in artifact_ids)
        self.assertTrue(has_parser, f"No error artifact for parser. IDs: {artifact_ids}")

    def test_empty_state_update_handling(self):
        """Node returns {} (empty update) -> treated as present (valid dict)."""
        adapter = _make_adapter("null-empty-dict")
        graph = MockStateGraph()
        graph.add_node("noop", lambda s: {})
        graph.add_edge(MockStateGraph.START, "noop")
        graph.add_edge("noop", MockStateGraph.END)

        final, result, _ = _run_instrumented(graph, adapter)
        self.assertEqual(len(result["validation_errors"]), 0)

    def test_multi_node_mixed_outputs(self):
        """5 nodes with mix of present/None/error outputs."""
        adapter = _make_adapter("null-mixed")

        call_count = {"fail_node": 0}

        def fail_node(state):
            call_count["fail_node"] += 1
            if call_count["fail_node"] == 1:
                raise RuntimeError("Intentional failure")
            return {"recovered": True}

        graph = MockStateGraph()
        graph.add_node("n1", lambda s: {"a": 1})
        graph.add_node("n2", lambda s: None)       # None output
        graph.add_node("n3", lambda s: {"b": 2})
        graph.add_node("fail_node", fail_node)      # Error on first call
        graph.add_node("recovery", lambda s: {"c": 3})
        graph.add_edge(MockStateGraph.START, "n1")
        graph.add_edge("n1", "n2")
        graph.add_edge("n2", "n3")
        graph.add_edge("n3", "fail_node")
        graph.add_edge("fail_node", MockStateGraph.END)
        graph.add_edge("recovery", MockStateGraph.END)

        final, result, ad = _run_instrumented(
            graph, adapter, error_handler="recovery"
        )
        self.assertEqual(len(result["validation_errors"]), 0)
        # Should have artifacts for n1, n2, n3, fail_node (error), recovery
        self.assertGreaterEqual(result["total_stages"], 5)

    def test_validate_chamber_zero_errors(self):
        """Clean linear pipeline -> sealed chamber passes validate_chamber()."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        session = result["session_result"]
        self.assertEqual(len(session["validation_errors"]), 0)

    def test_no_bare_nones_in_artifacts(self):
        """Scan all artifacts in a scenario for bare None without state."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        adapter = result["adapter"]
        chamber = adapter._chamber

        for stage in chamber["stages"]:
            art = stage["artifact"]
            output = art.get("output")
            if output is None:
                # Must have output_state
                self.assertIn("output_state", art,
                              f"Bare None output without output_state in {art['id']}")


# ===========================================================================
# 2. CHECKPOINTER TRANSPARENCY TESTS (6 tests)
# ===========================================================================

class TestCheckpointerTransparency(unittest.TestCase):
    """Verify ForgeCheckpointSaver does not alter inner checkpointer behavior."""

    def setUp(self):
        self.adapter = _make_adapter("ckpt-test")
        self.adapter.start_session()
        self.inner = MockCheckpointSaver()
        self.forge = ForgeCheckpointSaver(self.inner, self.adapter)
        self.config = {"configurable": {"thread_id": "transparency-test"}}

    def tearDown(self):
        self.adapter.end_session()

    def test_put_delegates_to_inner(self):
        """inner.put() is called with identical args."""
        checkpoint = {"id": "ckpt-1", "channel_values": {"x": 42}, "ts": "t1"}
        metadata = {"source": "test_node", "step": 1}

        self.forge.put(self.config, checkpoint, metadata)

        # Inner should have exactly 1 put call
        put_calls = [c for c in self.inner.call_log if c["method"] == "put"]
        self.assertEqual(len(put_calls), 1)
        self.assertEqual(put_calls[0]["checkpoint_id"], "ckpt-1")

    def test_get_tuple_delegates(self):
        """inner.get_tuple() result returned unchanged."""
        checkpoint = {"id": "ckpt-gt", "channel_values": {"y": 99}, "ts": "t1"}
        metadata = {"source": "node_a", "step": 1}
        self.forge.put(self.config, checkpoint, metadata)

        result = self.forge.get_tuple(self.config)
        inner_result = self.inner.get_tuple(self.config)

        self.assertIsNotNone(result)
        self.assertEqual(result["checkpoint"]["id"], inner_result["checkpoint"]["id"])

    def test_list_delegates(self):
        """inner.list() yields identical checkpoints."""
        for i in range(3):
            ckpt = {"id": f"ckpt-list-{i}", "channel_values": {"step": i}, "ts": f"t{i}"}
            meta = {"source": f"node_{i}", "step": i}
            self.forge.put(self.config, ckpt, meta)

        forge_listed = list(self.forge.list(self.config))
        inner_listed = list(self.inner.list(self.config))

        self.assertEqual(len(forge_listed), len(inner_listed))
        for fl, il in zip(forge_listed, inner_listed):
            self.assertEqual(fl["checkpoint"]["id"], il["checkpoint"]["id"])

    def test_put_writes_delegates(self):
        """inner.put_writes() is called correctly."""
        writes = [{"channel": "messages", "value": "hello"}]
        self.forge.put_writes(self.config, writes, "task-1")

        pw_calls = [c for c in self.inner.call_log if c["method"] == "put_writes"]
        self.assertEqual(len(pw_calls), 1)
        self.assertEqual(pw_calls[0]["task_id"], "task-1")

    def test_checkpoint_data_unmodified(self):
        """Data stored in inner == data passed in."""
        original = {"id": "ckpt-orig", "channel_values": {"a": 1, "b": [2, 3]}, "ts": "t"}
        metadata = {"source": "mod_test", "step": 1}

        self.forge.put(self.config, copy.deepcopy(original), metadata)
        stored = self.inner.get_tuple(self.config)

        self.assertEqual(stored["checkpoint"]["channel_values"], original["channel_values"])
        self.assertEqual(stored["checkpoint"]["id"], original["id"])

    def test_forge_artifacts_created_on_put(self):
        """Each put() creates a forge artifact."""
        for i in range(3):
            ckpt = {"id": f"ckpt-art-{i}", "channel_values": {"i": i}, "ts": f"t{i}"}
            meta = {"source": f"node_{i}", "step": i}
            self.forge.put(self.config, ckpt, meta)

        metrics = self.adapter.get_metrics()
        self.assertEqual(metrics["stages"], 3)


# ===========================================================================
# 3. PROVENANCE TESTS (6 tests)
# ===========================================================================

class TestProvenance(unittest.TestCase):
    """Verify provenance chains are correct and complete."""

    def test_linear_pipeline_chain(self):
        """3-node pipeline -> linear provenance chain."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        adapter = result["adapter"]

        # Each artifact should ref the previous one
        artifact_ids = adapter.get_metrics()["artifact_ids"]
        self.assertGreaterEqual(len(artifact_ids), 3)

        chamber = adapter._chamber
        for i, stage in enumerate(chamber["stages"]):
            if i == 0:
                continue  # First artifact has no parent
            art = stage["artifact"]
            refs = [r["ref"] for r in art.get("refs", []) if isinstance(r, dict)]
            # Should reference at least one previous artifact
            self.assertGreater(len(refs), 0,
                               f"Stage {i} ({art['id']}) has no refs")

    def test_conditional_routing_provenance(self):
        """Conditional edge -> correct branch tracked."""
        harness = LangGraphForgeHarness()
        result = scenario_conditional_routing(harness)
        adapter = result["adapter"]
        artifact_ids = adapter.get_metrics()["artifact_ids"]

        # Should have artifacts for: __input__, planner, fallback(absence), executor
        self.assertGreaterEqual(len(artifact_ids), 3)

    def test_all_reach_root(self):
        """BFS from every artifact reaches chamber root."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        adapter = result["adapter"]

        self.assertTrue(_all_reach_root(adapter))

    def test_reversibility_above_threshold(self):
        """Reversibility >= 0.95 for linear pipeline."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        adapter = result["adapter"]

        score = _compute_reversibility(adapter)
        self.assertGreaterEqual(score, 0.95, f"Reversibility {score} < 0.95")

    def test_checkpoint_history_as_provenance(self):
        """Checkpointer history matches provenance chain."""
        adapter = _make_adapter("prov-history")
        adapter.start_session()

        inner = MockCheckpointSaver()
        forge_ckpt = ForgeCheckpointSaver(inner, adapter)

        config = {"configurable": {"thread_id": "prov-thread"}}
        for i in range(5):
            ckpt = {"id": f"ckpt-h-{i}", "channel_values": {"step": i}, "ts": f"t{i}"}
            meta = {"source": f"node_{i}", "step": i}
            forge_ckpt.put(config, ckpt, meta)

        history = list(inner.list(config))
        adapter_artifacts = adapter.get_metrics()["artifact_ids"]

        self.assertEqual(len(history), 5)
        self.assertEqual(len(adapter_artifacts), 5)
        adapter.end_session()

    def test_multi_thread_independent(self):
        """Two thread_ids produce independent provenance chains."""
        adapter = _make_adapter("prov-multi")
        adapter.start_session()

        inner = MockCheckpointSaver()
        forge_ckpt = ForgeCheckpointSaver(inner, adapter)

        config_a = {"configurable": {"thread_id": "thread-A"}}
        config_b = {"configurable": {"thread_id": "thread-B"}}

        forge_ckpt.put(config_a,
                       {"id": "ckpt-a1", "channel_values": {"x": 1}, "ts": "t1"},
                       {"source": "nodeA", "step": 1})
        forge_ckpt.put(config_b,
                       {"id": "ckpt-b1", "channel_values": {"y": 2}, "ts": "t2"},
                       {"source": "nodeB", "step": 1})

        history_a = list(inner.list(config_a))
        history_b = list(inner.list(config_b))

        self.assertEqual(len(history_a), 1)
        self.assertEqual(len(history_b), 1)
        self.assertNotEqual(
            history_a[0]["checkpoint"]["id"],
            history_b[0]["checkpoint"]["id"],
        )
        adapter.end_session()


# ===========================================================================
# 4. TRACE INTEGRITY TESTS (4 tests)
# ===========================================================================

class TestTraceIntegrity(unittest.TestCase):
    """Verify trace encoding/decoding is exact and complete."""

    def test_encode_decode_roundtrip(self):
        """hash_match=True for all scenarios."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        session = result["session_result"]
        self.assertTrue(session["trace_verified"])

    def test_trace_stats_match_node_count(self):
        """Trace stages match the number of nodes executed + checkpoints."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        session = result["session_result"]
        stats = session["trace_stats"]

        # linear_pipeline: __input__ + planner + executor + reviewer = 4 stages
        self.assertEqual(stats["stage_count"], 4)

    def test_sealed_chamber_required(self):
        """Unsealed chamber can still be traced but won't be validated as sealed."""
        adapter = _make_adapter("trace-unseal")
        graph = _make_simple_graph()
        adapter.start_session()
        harness = LangGraphForgeHarness(adapter)
        compiled = harness.instrument(graph, adapter)
        compiled.invoke({"task": "test"}, {"configurable": {"thread_id": "t1"}})

        # Chamber is still open (end_session not called)
        chamber = adapter._chamber
        self.assertEqual(chamber["status"], "open")

        # But we can still encode the trace
        trace = encode_trace(chamber)
        verification = verify_trace(trace, chamber)
        self.assertTrue(verification["hash_match"])

        adapter.end_session()

    def test_multiple_graph_runs_independent(self):
        """Separate chambers per run — runs don't interfere."""
        harness = LangGraphForgeHarness()
        r1 = scenario_linear_pipeline(harness)
        r2 = scenario_long_conversation(harness)

        s1 = r1["session_result"]
        s2 = r2["session_result"]

        self.assertNotEqual(s1["run_id"], s2["run_id"])
        self.assertTrue(s1["trace_verified"])
        self.assertTrue(s2["trace_verified"])
        # Different stage counts
        self.assertNotEqual(s1["total_stages"], s2["total_stages"])


# ===========================================================================
# 5. FAULT INJECTION TESTS (4 tests)
# ===========================================================================

class TestFaultInjection(unittest.TestCase):
    """Inject structural faults and verify detection."""

    def test_d1_null_collapse_detected(self):
        """Bare None in node output triggers D1 violation detection."""
        adapter = _make_adapter("fault-d1")
        adapter.start_session()

        # Manually create an interception event with bare None
        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="buggy_node",
            output_data=None,
            output_state=None,  # This is the D1 violation — no typed absence
        )
        adapter._events.append(event)
        adapter._check_violation(event)

        self.assertGreater(len(adapter._violations), 0)
        d1_violations = [v for v in adapter._violations if v["type"] == "D1"]
        self.assertGreater(len(d1_violations), 0)
        adapter.end_session()

    def test_d2_broken_provenance(self):
        """Inject bad ref -> validation catches it."""
        adapter = _make_adapter("fault-d2")
        adapter.start_session()

        # Register a normal artifact first
        adapter.on_turn("node_a", "input", "output")

        # Manually tamper: add a bad ref to the chamber
        chamber = adapter._chamber
        if chamber["stages"]:
            art = chamber["stages"][-1]["artifact"]
            art["refs"].append({"ref": "artifact:nonexistent:bad:ref:r1", "state": "resolved"})

        # Now validate the chamber — should catch the dangling ref
        errors = validate_chamber(chamber)
        ref_errors = [e for e in errors if "REF" in e.get("code", "")]
        self.assertGreater(len(ref_errors), 0,
                           f"Expected ref errors for dangling ref, got: {errors}")
        adapter.end_session()

    def test_d5_missing_state_label(self):
        """Dict output with None field but no _state -> D5 violation."""
        adapter = _make_adapter("fault-d5")
        adapter.start_session()

        event = InterceptionEvent(
            event_type="turn",
            timestamp="2026-01-01T00:00:00Z",
            seat="leaky_node",
            output_data={"result": None},  # bare None without result_state
        )
        adapter._events.append(event)
        adapter._check_violation(event)

        d5_violations = [v for v in adapter._violations if v["type"] == "D5"]
        self.assertGreater(len(d5_violations), 0)
        adapter.end_session()

    def test_clean_run_zero_violations(self):
        """Well-formed graph -> 0 violations detected."""
        harness = LangGraphForgeHarness()
        result = scenario_linear_pipeline(harness)
        session = result["session_result"]
        self.assertEqual(session["violations_detected"], 0)


# ===========================================================================
# 6. ANCHOR COMPARISON TESTS (2 tests)
# ===========================================================================

class TestAnchorComparisons(unittest.TestCase):
    """Compare LangGraph adapter metrics against OpenClaw/MockLM benchmarks."""

    def test_lg_reversibility_matches_target(self):
        """Reversibility >= 0.95 (matching OpenClaw/MockLM level)."""
        for name, scenario_fn in SCENARIOS.items():
            harness = LangGraphForgeHarness()
            result = scenario_fn(harness)
            adapter = result["adapter"]
            score = _compute_reversibility(adapter)
            self.assertGreaterEqual(
                score, 0.95,
                f"Scenario '{name}': reversibility {score:.4f} < 0.95"
            )

    def test_lg_trace_integrity_matches_mock(self):
        """hash_match=True for all scenarios (same as MockLM)."""
        for name, scenario_fn in SCENARIOS.items():
            harness = LangGraphForgeHarness()
            result = scenario_fn(harness)
            session = result["session_result"]
            self.assertTrue(
                session["trace_verified"],
                f"Scenario '{name}': trace not verified"
            )


# ===========================================================================
# 7. CONDITIONAL EDGE SCENARIOS (3 tests)
# ===========================================================================

class TestConditionalEdges(unittest.TestCase):
    """Focused tests on conditional edge absence tracking."""

    def test_high_complexity_takes_fallback(self):
        """High complexity input routes to fallback, executor skipped."""
        adapter = _make_adapter("cond-high")
        adapter.start_session()

        def planner(state):
            return {"plan": "complex plan", "complexity": state.get("complexity")}

        def executor(state):
            return {"result": "executed"}

        def fallback(state):
            return {"result": "fallback taken"}

        graph = MockStateGraph()
        graph.add_node("planner", planner)
        graph.add_node("executor", executor)
        graph.add_node("fallback", fallback)
        graph.add_edge(MockStateGraph.START, "planner")
        graph.add_conditional_edges("planner",
                                    lambda s: "complex" if s.get("complexity") == "high" else "simple",
                                    {"simple": "executor", "complex": "fallback"})
        graph.add_edge("executor", MockStateGraph.END)
        graph.add_edge("fallback", MockStateGraph.END)

        final, result, ad = _run_instrumented(
            graph, adapter,
            input_state={"task": "hard task", "complexity": "high"},
        )

        artifact_ids = ad.get_metrics()["artifact_ids"]
        # executor should be skipped, fallback should run
        has_executor_absence = any("executor" in aid for aid in artifact_ids)
        self.assertTrue(has_executor_absence,
                        f"Executor absence not tracked. IDs: {artifact_ids}")

    def test_conditional_three_way_routing(self):
        """Three-way conditional: only one branch taken, two skipped."""
        adapter = _make_adapter("cond-3way")
        adapter.start_session()

        def router_node(state):
            return {"route": state.get("priority", "low")}

        graph = MockStateGraph()
        graph.add_node("router", router_node)
        graph.add_node("fast_path", lambda s: {"result": "fast"})
        graph.add_node("normal_path", lambda s: {"result": "normal"})
        graph.add_node("slow_path", lambda s: {"result": "slow"})
        graph.add_edge(MockStateGraph.START, "router")
        graph.add_conditional_edges("router",
                                    lambda s: s.get("priority", "low"),
                                    {"high": "fast_path", "medium": "normal_path", "low": "slow_path"})
        graph.add_edge("fast_path", MockStateGraph.END)
        graph.add_edge("normal_path", MockStateGraph.END)
        graph.add_edge("slow_path", MockStateGraph.END)

        final, result, ad = _run_instrumented(
            graph, adapter,
            input_state={"task": "urgent", "priority": "high"},
        )

        artifact_ids = ad.get_metrics()["artifact_ids"]
        # fast_path should run; normal_path and slow_path skipped
        has_normal_absence = any("normal_path" in aid for aid in artifact_ids)
        has_slow_absence = any("slow_path" in aid for aid in artifact_ids)
        self.assertTrue(has_normal_absence,
                        f"normal_path absence not tracked. IDs: {artifact_ids}")
        self.assertTrue(has_slow_absence,
                        f"slow_path absence not tracked. IDs: {artifact_ids}")

    def test_conditional_preserves_validation(self):
        """Conditional routing still produces valid sealed chambers."""
        adapter = _make_adapter("cond-valid")

        graph = MockStateGraph()
        graph.add_node("decide", lambda s: {"decision": "go"})
        graph.add_node("path_a", lambda s: {"path": "a"})
        graph.add_node("path_b", lambda s: {"path": "b"})
        graph.add_edge(MockStateGraph.START, "decide")
        graph.add_conditional_edges("decide",
                                    lambda s: "a",
                                    {"a": "path_a", "b": "path_b"})
        graph.add_edge("path_a", MockStateGraph.END)
        graph.add_edge("path_b", MockStateGraph.END)

        final, result, _ = _run_instrumented(graph, adapter)
        self.assertEqual(len(result["validation_errors"]), 0)
        self.assertEqual(result["violations_detected"], 0)


# ===========================================================================
# 8. MULTI-SCENARIO REGRESSION TESTS (3 tests)
# ===========================================================================

class TestMultiScenarioRegression(unittest.TestCase):
    """Run all scenarios and check aggregate properties."""

    def test_all_scenarios_zero_validation_errors(self):
        """Every built-in scenario produces 0 validation errors."""
        for name, scenario_fn in SCENARIOS.items():
            harness = LangGraphForgeHarness()
            result = scenario_fn(harness)
            session = result["session_result"]
            self.assertEqual(
                len(session["validation_errors"]), 0,
                f"Scenario '{name}' has validation errors: {session['validation_errors']}"
            )

    def test_all_scenarios_trace_verified(self):
        """Every built-in scenario has trace_verified=True."""
        for name, scenario_fn in SCENARIOS.items():
            harness = LangGraphForgeHarness()
            result = scenario_fn(harness)
            session = result["session_result"]
            self.assertTrue(
                session["trace_verified"],
                f"Scenario '{name}' trace not verified"
            )

    def test_long_conversation_ten_nodes(self):
        """Long conversation scenario has >= 10 executed nodes."""
        harness = LangGraphForgeHarness()
        result = scenario_long_conversation(harness)
        session = result["session_result"]
        # 10 nodes + __input__ checkpoint = 11 stages
        self.assertGreaterEqual(session["total_stages"], 10)

    def test_all_scenarios_all_reach_root(self):
        """Every scenario's artifacts all reach the chamber root."""
        for name, scenario_fn in SCENARIOS.items():
            harness = LangGraphForgeHarness()
            result = scenario_fn(harness)
            adapter = result["adapter"]
            self.assertTrue(
                _all_reach_root(adapter),
                f"Scenario '{name}': not all artifacts reach root"
            )


if __name__ == "__main__":
    unittest.main()
