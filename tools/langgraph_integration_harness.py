"""LangGraph integration harness — mock StateGraph + ForgeCheckpointSaver.

Simulates LangGraph's StateGraph architecture with:
- MockCheckpointSaver (BaseCheckpointSaver interface)
- ForgeCheckpointSaver (transparent wrapper that registers forge artifacts)
- MockStateGraph / MockCompiledGraph (graph definition + execution)
- LangGraphForgeHarness (orchestrates instrumentation + scenario runs)

No real LangGraph import needed — the mock fidelity is sufficient to test
that the adapter pattern intercepts state transitions, handles conditional
edges, and produces valid forge artifacts with typed absence and provenance.

Phase 8 of Primordial v2.0 (RQ4: cross-architecture generalization).
"""

import copy
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent))

from forge_adapter import LangGraphForgeAdapter, InterceptionEvent
from forge_nulls import AbsenceState
from forge_chamber import validate_chamber


# ---------------------------------------------------------------------------
# MockCheckpointSaver — simulates BaseCheckpointSaver interface
# ---------------------------------------------------------------------------

class MockCheckpointSaver:
    """In-memory checkpoint store mimicking LangGraph's BaseCheckpointSaver.

    Stores checkpoints keyed by (thread_id, checkpoint_id).
    Supports put, get_tuple, list, put_writes, get_next_version.
    """

    def __init__(self):
        self._store: dict[tuple[str, str], dict] = {}
        self._writes: dict[tuple[str, str], list] = {}
        self._version_counter: int = 0
        self.call_log: list[dict] = []

    def put(self, config: dict, checkpoint: dict, metadata: dict,
            new_versions: dict | None = None) -> dict:
        """Store a checkpoint. Returns the config for retrieval."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = checkpoint.get("id", f"ckpt-{self._version_counter}")

        key = (thread_id, checkpoint_id)
        entry = {
            "checkpoint": copy.deepcopy(checkpoint),
            "metadata": copy.deepcopy(metadata),
            "config": copy.deepcopy(config),
            "new_versions": copy.deepcopy(new_versions) if new_versions else {},
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store[key] = entry

        self.call_log.append({
            "method": "put",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "metadata": metadata,
        })

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(self, config: dict, writes: list, task_id: str) -> None:
        """Store pending writes for a task."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        key = (thread_id, task_id)
        self._writes[key] = copy.deepcopy(writes)

        self.call_log.append({
            "method": "put_writes",
            "thread_id": thread_id,
            "task_id": task_id,
            "write_count": len(writes),
        })

    def get_tuple(self, config: dict) -> dict | None:
        """Retrieve a checkpoint by thread_id + checkpoint_id."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        self.call_log.append({
            "method": "get_tuple",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
        })

        if checkpoint_id:
            key = (thread_id, checkpoint_id)
            return self._store.get(key)

        # Return latest checkpoint for thread
        thread_checkpoints = [
            (k, v) for k, v in self._store.items() if k[0] == thread_id
        ]
        if not thread_checkpoints:
            return None
        return max(thread_checkpoints, key=lambda x: x[1]["stored_at"])[1]

    def list(self, config: dict, *, filter: dict | None = None,
             before: dict | None = None, limit: int | None = None):
        """Yield checkpoint history for a thread."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")

        self.call_log.append({
            "method": "list",
            "thread_id": thread_id,
            "limit": limit,
        })

        entries = [
            v for k, v in sorted(self._store.items(), key=lambda x: x[1]["stored_at"])
            if k[0] == thread_id
        ]

        if limit is not None:
            entries = entries[:limit]

        return iter(entries)

    def get_next_version(self, current: str | None = None) -> str:
        """Generate next incremental version ID."""
        self._version_counter += 1
        return f"v{self._version_counter}"


# ---------------------------------------------------------------------------
# ForgeCheckpointSaver — transparent wrapper that intercepts for forge
# ---------------------------------------------------------------------------

class ForgeCheckpointSaver:
    """Wraps any checkpointer, delegates ALL calls, and registers forge artifacts.

    Semantic neutrality: the inner checkpointer receives identical arguments
    and its return values are passed through unchanged. ForgeCheckpointSaver
    only ADDITIONALLY registers each put() as a forge artifact.
    """

    def __init__(self, inner: MockCheckpointSaver, adapter: LangGraphForgeAdapter):
        self._inner = inner
        self._adapter = adapter
        self._checkpoint_to_artifact: dict[str, str] = {}  # checkpoint_id -> artifact_id

    @property
    def inner(self) -> MockCheckpointSaver:
        return self._inner

    def put(self, config: dict, checkpoint: dict, metadata: dict,
            new_versions: dict | None = None) -> dict:
        """Delegate to inner, then register forge artifact."""
        # Delegate to inner — identical args, capture return
        result = self._inner.put(config, checkpoint, metadata, new_versions)

        # Extract node info from metadata (LangGraph convention)
        source_node = metadata.get("source", "unknown")
        step = metadata.get("step", 0)

        # Build state snapshot for forge
        state_snapshot = json.dumps(checkpoint.get("channel_values", {}))

        # Register as forge artifact via adapter's on_turn
        artifact_id = self._adapter.on_turn(
            seat=source_node,
            input_data={"step": step, "checkpoint_id": checkpoint.get("id")},
            output_data=checkpoint.get("channel_values", {}),
            checkpoint_metadata=metadata,
        )

        checkpoint_id = checkpoint.get("id", "")
        self._checkpoint_to_artifact[checkpoint_id] = artifact_id

        return result  # Return inner's result unchanged

    def put_writes(self, config: dict, writes: list, task_id: str) -> None:
        """Delegate to inner unchanged."""
        return self._inner.put_writes(config, writes, task_id)

    def get_tuple(self, config: dict) -> dict | None:
        """Delegate to inner unchanged."""
        return self._inner.get_tuple(config)

    def list(self, config: dict, *, filter: dict | None = None,
             before: dict | None = None, limit: int | None = None):
        """Delegate to inner unchanged."""
        return self._inner.list(config, filter=filter, before=before, limit=limit)

    def get_next_version(self, current: str | None = None) -> str:
        """Delegate to inner unchanged."""
        return self._inner.get_next_version(current)

    def get_artifact_for_checkpoint(self, checkpoint_id: str) -> str | None:
        """Look up which forge artifact corresponds to a checkpoint."""
        return self._checkpoint_to_artifact.get(checkpoint_id)


# ---------------------------------------------------------------------------
# MockStateGraph + MockCompiledGraph — simulates LangGraph graph execution
# ---------------------------------------------------------------------------

@dataclass
class EdgeDef:
    """An edge in the graph (fixed or conditional)."""
    src: str
    dst: str | None = None  # None for conditional
    condition_fn: Callable | None = None
    mapping: dict[str, str] | None = None  # condition result -> target node

    @property
    def is_conditional(self) -> bool:
        return self.condition_fn is not None


class MockStateGraph:
    """Simulates LangGraph's StateGraph definition.

    Nodes are functions: state_dict -> state_update_dict (or None).
    Edges define transitions. Conditional edges use a routing function.
    """

    START = "__start__"
    END = "__end__"

    def __init__(self, state_schema: dict | None = None):
        self.state_schema = state_schema or {}
        self._nodes: dict[str, Callable] = {}
        self._edges: list[EdgeDef] = []
        self._entry_node: str | None = None

    def add_node(self, name: str, fn: Callable) -> "MockStateGraph":
        """Register a node function."""
        self._nodes[name] = fn
        return self

    def add_edge(self, src: str, dst: str) -> "MockStateGraph":
        """Add a fixed transition edge."""
        self._edges.append(EdgeDef(src=src, dst=dst))
        if src == self.START:
            self._entry_node = dst
        return self

    def add_conditional_edges(self, src: str, condition_fn: Callable,
                              mapping: dict[str, str]) -> "MockStateGraph":
        """Add conditional routing from src based on condition_fn result."""
        self._edges.append(EdgeDef(
            src=src, condition_fn=condition_fn, mapping=mapping,
        ))
        return self

    def compile(self, checkpointer=None) -> "MockCompiledGraph":
        """Compile into an executable graph."""
        return MockCompiledGraph(
            nodes=dict(self._nodes),
            edges=list(self._edges),
            entry_node=self._entry_node,
            checkpointer=checkpointer,
        )


class NodeExecutionError(Exception):
    """Raised when a node function fails."""
    def __init__(self, node_name: str, original_error: Exception):
        self.node_name = node_name
        self.original_error = original_error
        super().__init__(f"Node '{node_name}' failed: {original_error}")


class MockCompiledGraph:
    """Simulates LangGraph's CompiledStateGraph execution."""

    START = MockStateGraph.START
    END = MockStateGraph.END

    def __init__(self, nodes: dict[str, Callable], edges: list[EdgeDef],
                 entry_node: str | None, checkpointer=None):
        self._nodes = nodes
        self._edges = edges
        self._entry_node = entry_node
        self._checkpointer = checkpointer

        # Build adjacency: src -> list of EdgeDef
        self._adjacency: dict[str, list[EdgeDef]] = {}
        for edge in edges:
            self._adjacency.setdefault(edge.src, []).append(edge)

    @property
    def checkpointer(self):
        return self._checkpointer

    @checkpointer.setter
    def checkpointer(self, value):
        self._checkpointer = value

    def _get_next_nodes(self, current: str, state: dict) -> list[str]:
        """Determine next node(s) from current node given state."""
        edges = self._adjacency.get(current, [])
        targets = []

        for edge in edges:
            if edge.is_conditional:
                route_key = edge.condition_fn(state)
                target = edge.mapping.get(route_key, self.END)
                targets.append(target)
            else:
                targets.append(edge.dst)

        return targets

    def _get_all_possible_targets(self, current: str) -> set[str]:
        """Get all nodes that COULD be reached from current (for absence tracking)."""
        edges = self._adjacency.get(current, [])
        targets = set()
        for edge in edges:
            if edge.is_conditional and edge.mapping:
                targets.update(edge.mapping.values())
            elif edge.dst:
                targets.add(edge.dst)
        return targets - {self.END}

    def _checkpoint(self, state: dict, node_name: str, step: int,
                    config: dict) -> str | None:
        """Checkpoint current state if checkpointer is available."""
        if not self._checkpointer:
            return None

        checkpoint_id = f"ckpt-{config.get('configurable', {}).get('thread_id', 'default')}-step{step}"
        checkpoint = {
            "id": checkpoint_id,
            "channel_values": copy.deepcopy(state),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        metadata = {
            "source": node_name,
            "step": step,
            "writes": {},
        }

        self._checkpointer.put(config, checkpoint, metadata)
        return checkpoint_id

    def invoke(self, input_state: dict, config: dict | None = None,
               error_handler: str | None = None) -> dict:
        """Execute the graph from START to END.

        Args:
            input_state: Initial state dict.
            config: LangGraph-style config with thread_id etc.
            error_handler: Name of error-handling node (called on node failure).

        Returns:
            Final state dict.
        """
        if config is None:
            config = {"configurable": {"thread_id": f"thread-{int(time.time())}"}}

        state = copy.deepcopy(input_state)
        current_node = self._entry_node
        step = 0
        executed_nodes: list[str] = []
        skipped_nodes: list[str] = []
        error_nodes: list[str] = []

        # Initial checkpoint
        self._checkpoint(state, "__input__", step, config)

        while current_node and current_node != self.END:
            step += 1
            node_fn = self._nodes.get(current_node)

            if node_fn is None:
                raise ValueError(f"Node '{current_node}' not found in graph")

            # Execute the node
            try:
                result = node_fn(state)
            except Exception as e:
                error_nodes.append(current_node)

                # Register error via adapter if checkpointer is ForgeCheckpointSaver
                if isinstance(self._checkpointer, ForgeCheckpointSaver):
                    self._checkpointer._adapter.on_error(current_node, e)

                if error_handler and error_handler in self._nodes:
                    # Route to error handler node
                    state["_error"] = str(e)
                    state["_error_node"] = current_node
                    current_node = error_handler
                    continue
                else:
                    # Checkpoint the error state
                    self._checkpoint(state, current_node, step, config)
                    raise NodeExecutionError(current_node, e)

            # Apply state update
            if result is not None and isinstance(result, dict):
                state.update(result)
                executed_nodes.append(current_node)
            elif result is None:
                # Node returned None — register absence if forge-instrumented
                if isinstance(self._checkpointer, ForgeCheckpointSaver):
                    self._checkpointer._adapter.on_turn(
                        seat=current_node,
                        input_data=state,
                        output_data=None,
                        node_returned_none=True,
                    )
                executed_nodes.append(current_node)
            else:
                # Non-dict, non-None result: treat as output string
                state[f"{current_node}_output"] = result
                executed_nodes.append(current_node)

            # Checkpoint after node execution
            self._checkpoint(state, current_node, step, config)

            # Determine next node(s) — handle conditional routing
            all_possible = self._get_all_possible_targets(current_node)
            next_nodes = self._get_next_nodes(current_node, state)

            # Track skipped nodes (conditional edge routing past them)
            if all_possible and next_nodes:
                actual_targets = set(next_nodes) - {self.END}
                skipped = (all_possible - actual_targets) & set(self._nodes.keys())
                for skip_node in skipped:
                    skipped_nodes.append(skip_node)
                    # Register absence for skipped node
                    if isinstance(self._checkpointer, ForgeCheckpointSaver):
                        self._checkpointer._adapter._register_artifact(
                            seat=skip_node,
                            output=None,
                            output_state=AbsenceState.NOT_INVOKED,
                            summary_text=f"Node '{skip_node}' skipped by conditional edge from '{current_node}'",
                            producer_role="langgraph-conditional-skip",
                        )

            # Move to next node (take first target for sequential execution)
            current_node = next_nodes[0] if next_nodes else self.END

        # Store execution metadata in state
        state["_execution_metadata"] = {
            "executed_nodes": executed_nodes,
            "skipped_nodes": skipped_nodes,
            "error_nodes": error_nodes,
            "total_steps": step,
        }

        return state


# ---------------------------------------------------------------------------
# LangGraphForgeHarness — orchestrates instrumentation + scenario execution
# ---------------------------------------------------------------------------

class LangGraphForgeHarness:
    """Instruments a MockStateGraph with forge tracking and runs scenarios."""

    def __init__(self, adapter: LangGraphForgeAdapter | None = None):
        self._adapter = adapter
        self._results: list[dict] = []

    @property
    def adapter(self) -> LangGraphForgeAdapter:
        return self._adapter

    def instrument(self, graph: MockStateGraph,
                   adapter: LangGraphForgeAdapter | None = None) -> MockCompiledGraph:
        """Compile graph with ForgeCheckpointSaver wrapping."""
        if adapter:
            self._adapter = adapter

        if not self._adapter:
            raise ValueError("No adapter provided — pass to __init__ or instrument()")

        inner_checkpointer = MockCheckpointSaver()
        forge_checkpointer = ForgeCheckpointSaver(inner_checkpointer, self._adapter)

        compiled = graph.compile(checkpointer=forge_checkpointer)
        return compiled

    def run_scenario(self, scenario_fn: Callable, run_id: str | None = None) -> dict:
        """Execute a scenario function that returns metrics dict."""
        result = scenario_fn(self)
        self._results.append(result)
        return result

    def get_all_results(self) -> list[dict]:
        return list(self._results)


# ---------------------------------------------------------------------------
# Built-in Scenarios
# ---------------------------------------------------------------------------

def scenario_linear_pipeline(harness: LangGraphForgeHarness) -> dict:
    """Scenario A: 3 nodes in sequence (planner -> executor -> reviewer).

    All nodes produce output. Tests basic checkpoint-based provenance chain.
    """
    adapter = LangGraphForgeAdapter(run_id="scenario-linear")
    adapter.start_session({"scenario": "linear_pipeline"})

    def planner(state):
        return {"plan": "Build a REST API with auth", "plan_ready": True}

    def executor(state):
        return {"code": "def api(): pass", "tests_written": True}

    def reviewer(state):
        return {"review": "Code looks good, needs error handling", "approved": True}

    graph = MockStateGraph()
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("reviewer", reviewer)
    graph.add_edge(MockStateGraph.START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reviewer")
    graph.add_edge("reviewer", MockStateGraph.END)

    compiled = harness.instrument(graph, adapter)
    config = {"configurable": {"thread_id": "linear-001"}}

    final_state = compiled.invoke({"task": "Build API"}, config)
    result = adapter.end_session()

    return {
        "scenario": "linear_pipeline",
        "final_state": final_state,
        "session_result": result,
        "adapter": adapter,
    }


def scenario_conditional_routing(harness: LangGraphForgeHarness) -> dict:
    """Scenario B: Conditional edge — planner routes to executor OR fallback.

    Tests absence tracking for the skipped branch node.
    """
    adapter = LangGraphForgeAdapter(run_id="scenario-conditional")
    adapter.start_session({"scenario": "conditional_routing"})

    def planner(state):
        complexity = state.get("complexity", "low")
        return {"plan": f"Plan for {complexity} task", "complexity": complexity}

    def executor(state):
        return {"result": "Executed main path", "success": True}

    def fallback(state):
        return {"result": "Fallback path taken", "success": True}

    def route_fn(state):
        return "complex" if state.get("complexity") == "high" else "simple"

    graph = MockStateGraph()
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("fallback", fallback)
    graph.add_edge(MockStateGraph.START, "planner")
    graph.add_conditional_edges("planner", route_fn, {
        "simple": "executor",
        "complex": "fallback",
    })
    graph.add_edge("executor", MockStateGraph.END)
    graph.add_edge("fallback", MockStateGraph.END)

    compiled = harness.instrument(graph, adapter)
    config = {"configurable": {"thread_id": "conditional-001"}}

    # Run with low complexity — executor runs, fallback skipped
    final_state = compiled.invoke({"task": "Simple task", "complexity": "low"}, config)
    result = adapter.end_session()

    return {
        "scenario": "conditional_routing",
        "final_state": final_state,
        "session_result": result,
        "adapter": adapter,
    }


def scenario_tool_use_graph(harness: LangGraphForgeHarness) -> dict:
    """Scenario C: Agent node calls tools via tool nodes, mixed success.

    Tests tool_call interception and mixed output states.
    """
    adapter = LangGraphForgeAdapter(run_id="scenario-tools")
    adapter.start_session({"scenario": "tool_use_graph"})

    def agent(state):
        return {"action": "search", "query": "latest news"}

    def search_tool(state):
        query = state.get("query", "")
        if query:
            # Also register via adapter's tool_call
            adapter.on_tool_call("search_tool", "web_search", query, f"Results for: {query}")
            return {"search_results": f"Results for: {query}"}
        return None  # No results — should be tracked as absence

    def summarizer(state):
        results = state.get("search_results", "")
        if results:
            return {"summary": f"Summary of: {results}"}
        return {"summary": None, "summary_state": "not_generated"}

    graph = MockStateGraph()
    graph.add_node("agent", agent)
    graph.add_node("search_tool", search_tool)
    graph.add_node("summarizer", summarizer)
    graph.add_edge(MockStateGraph.START, "agent")
    graph.add_edge("agent", "search_tool")
    graph.add_edge("search_tool", "summarizer")
    graph.add_edge("summarizer", MockStateGraph.END)

    compiled = harness.instrument(graph, adapter)
    config = {"configurable": {"thread_id": "tools-001"}}

    final_state = compiled.invoke({"task": "Find news"}, config)
    result = adapter.end_session()

    return {
        "scenario": "tool_use_graph",
        "final_state": final_state,
        "session_result": result,
        "adapter": adapter,
    }


def scenario_error_recovery(harness: LangGraphForgeHarness) -> dict:
    """Scenario D: Node raises exception, graph routes to error handler.

    Tests typed absence (invalid) for the failed node.
    """
    adapter = LangGraphForgeAdapter(run_id="scenario-error")
    adapter.start_session({"scenario": "error_recovery"})

    call_count = {"parser": 0}

    def planner(state):
        return {"plan": "Parse the data", "plan_ready": True}

    def parser(state):
        call_count["parser"] += 1
        if call_count["parser"] == 1:
            raise ValueError("Malformed input data at line 42")
        return {"parsed_data": {"records": 100}, "parse_success": True}

    def error_handler(state):
        error = state.get("_error", "unknown")
        return {
            "recovery_action": f"Handled error: {error}",
            "recovered": True,
        }

    def validator(state):
        if state.get("recovered"):
            return {"validation": "Recovery accepted", "valid": True}
        return {"validation": "Data validated", "valid": True}

    graph = MockStateGraph()
    graph.add_node("planner", planner)
    graph.add_node("parser", parser)
    graph.add_node("error_handler", error_handler)
    graph.add_node("validator", validator)
    graph.add_edge(MockStateGraph.START, "planner")
    graph.add_edge("planner", "parser")
    graph.add_edge("parser", "validator")
    graph.add_edge("error_handler", "validator")
    graph.add_edge("validator", MockStateGraph.END)

    compiled = harness.instrument(graph, adapter)
    config = {"configurable": {"thread_id": "error-001"}}

    final_state = compiled.invoke(
        {"task": "Parse dataset", "data": "raw data here"},
        config,
        error_handler="error_handler",
    )
    result = adapter.end_session()

    return {
        "scenario": "error_recovery",
        "final_state": final_state,
        "session_result": result,
        "adapter": adapter,
    }


def scenario_long_conversation(harness: LangGraphForgeHarness) -> dict:
    """Scenario E: 10-node graph simulating multi-step task with checkpoints.

    Tests checkpoint provenance chain integrity at scale.
    """
    adapter = LangGraphForgeAdapter(run_id="scenario-long")
    adapter.start_session({"scenario": "long_conversation"})

    def make_step_fn(name: str, step_num: int):
        def step_fn(state):
            progress = state.get("progress", [])
            progress.append(f"Step {step_num}: {name}")
            return {"progress": progress, f"{name}_done": True}
        return step_fn

    node_names = [
        "init", "plan", "research", "design", "implement",
        "test", "review", "fix", "document", "deploy"
    ]

    graph = MockStateGraph()
    for i, name in enumerate(node_names):
        graph.add_node(name, make_step_fn(name, i + 1))

    # Linear chain: START -> init -> plan -> ... -> deploy -> END
    graph.add_edge(MockStateGraph.START, node_names[0])
    for i in range(len(node_names) - 1):
        graph.add_edge(node_names[i], node_names[i + 1])
    graph.add_edge(node_names[-1], MockStateGraph.END)

    compiled = harness.instrument(graph, adapter)
    config = {"configurable": {"thread_id": "long-001"}}

    final_state = compiled.invoke({"task": "Full development cycle"}, config)
    result = adapter.end_session()

    return {
        "scenario": "long_conversation",
        "final_state": final_state,
        "session_result": result,
        "adapter": adapter,
    }


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

SCENARIOS = {
    "linear_pipeline": scenario_linear_pipeline,
    "conditional_routing": scenario_conditional_routing,
    "tool_use_graph": scenario_tool_use_graph,
    "error_recovery": scenario_error_recovery,
    "long_conversation": scenario_long_conversation,
}


def run_all_scenarios() -> dict:
    """Run all built-in scenarios and return aggregated results."""
    all_results = {}
    harness = LangGraphForgeHarness()

    for name, scenario_fn in SCENARIOS.items():
        result = scenario_fn(harness)
        all_results[name] = result

    return all_results


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("LangGraph Integration Harness — All 5 Scenarios")
    print("=" * 70)

    results = run_all_scenarios()

    for name, result in results.items():
        session = result["session_result"]
        print(f"\n--- {name} ---")
        print(f"  Stages: {session['total_stages']}")
        print(f"  Events: {session['total_events']}")
        print(f"  Violations: {session['violations_detected']}")
        print(f"  Validation errors: {len(session['validation_errors'])}")
        print(f"  Trace verified: {session['trace_verified']}")

    print("\n" + "=" * 70)
    print("All 5 scenarios completed.")
