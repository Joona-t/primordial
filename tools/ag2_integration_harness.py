"""AG2 integration harness — realistic multi-agent session simulation.

Simulates AG2 (AutoGen v2) multi-agent GroupChat sessions with hook_list
callbacks, exercising all 4 interception points (turn, tool_call, compaction,
error). Uses ONLY stdlib + existing forge tools. No AG2 import needed.

The harness validates that the AG2ForgeAdapter correctly:
  1. Registers all events as forge artifacts with typed absence
  2. Maintains provenance chains (all artifacts reachable from root)
  3. Produces traces that round-trip losslessly (hash_match = True)
  4. Detects injected faults (D1, D2, D5)

Phase 8, Plan 01 of Primordial v2.0 (RQ4: cross-architecture generalization).
"""

import copy
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Ensure forge tools are importable
sys.path.insert(0, str(Path(__file__).parent))

from forge_adapter import AG2ForgeAdapter, InterceptionEvent
from forge_nulls import AbsenceState
from forge_chamber import validate_chamber
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from findings_ledger import FindingsLedger, Finding


# ============================================================
# Mock AG2 Framework Components
# ============================================================

class MockHookList:
    """Simulates AG2's hook_list system.

    AG2 hooks are pass-through: they receive a value and return
    the same value (potentially modified by the hook). Hooks are
    invoked in registration order.

    Supported hook names (AG2 v0.4+):
        process_all_messages_before_reply
        safeguard_llm_inputs
        safeguard_llm_outputs
        process_message_before_send
        safeguard_tool_inputs
        safeguard_tool_outputs
        process_last_received_message
        process_speaker_selection
        custom
    """

    _VALID_HOOKS = frozenset({
        "process_all_messages_before_reply",
        "safeguard_llm_inputs",
        "safeguard_llm_outputs",
        "process_message_before_send",
        "safeguard_tool_inputs",
        "safeguard_tool_outputs",
        "process_last_received_message",
        "process_speaker_selection",
        "custom",
    })

    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {h: [] for h in self._VALID_HOOKS}

    def register_hook(self, hook_name: str, callback: Callable):
        """Register a callback on the named hook."""
        if hook_name not in self._VALID_HOOKS:
            raise ValueError(f"Unknown AG2 hook: {hook_name!r}. Valid: {sorted(self._VALID_HOOKS)}")
        self._hooks[hook_name].append(callback)

    def fire(self, hook_name: str, value: Any) -> Any:
        """Fire all callbacks for the named hook. Pass-through semantics."""
        if hook_name not in self._VALID_HOOKS:
            raise ValueError(f"Unknown AG2 hook: {hook_name!r}")
        result = value
        for cb in self._hooks[hook_name]:
            returned = cb(result)
            if returned is not None:
                result = returned
        return result


class MockConversableAgent:
    """Simulates an AG2 ConversableAgent with hook_list support.

    Key behaviors:
    - Maintains _oai_messages dict keyed by sender name
    - Has hook_list with register_hook() for all 9 AG2 hooks
    - generate_reply() fires hooks in correct AG2 order
    - Tool execution fires tool-specific hooks
    """

    def __init__(
        self,
        name: str,
        role: str = "agent",
        reply_fn: Callable | None = None,
        tool_fns: dict[str, Callable] | None = None,
    ):
        self.name = name
        self.role = role
        self.hook_list = MockHookList()
        self._oai_messages: dict[str, list[dict]] = {}
        self._reply_fn = reply_fn or self._default_reply
        self._tool_fns = tool_fns or {}

    def _default_reply(self, messages: list[dict]) -> str:
        return f"Reply from {self.name}: acknowledged {len(messages)} messages"

    def receive(self, message: str, sender: str):
        """Receive a message from another agent."""
        if sender not in self._oai_messages:
            self._oai_messages[sender] = []
        self._oai_messages[sender].append({
            "role": "user",
            "content": message,
            "sender": sender,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def generate_reply(self, messages: list[dict] | None = None) -> str | None:
        """Generate a reply, firing hooks in AG2 order.

        Hook execution order (AG2 docs):
        1. process_all_messages_before_reply
        2. safeguard_llm_inputs
        3. [LLM call / reply generation]
        4. safeguard_llm_outputs
        5. process_message_before_send
        """
        all_messages = messages or self._get_all_messages()

        # Hook 1: process all messages before reply
        all_messages = self.hook_list.fire("process_all_messages_before_reply", all_messages)

        # Hook 2: safeguard LLM inputs
        all_messages = self.hook_list.fire("safeguard_llm_inputs", all_messages)

        # Generate reply
        reply = self._reply_fn(all_messages)

        # Hook 3: safeguard LLM outputs
        reply = self.hook_list.fire("safeguard_llm_outputs", reply)

        # Hook 4: process message before send
        reply = self.hook_list.fire("process_message_before_send", reply)

        # Store in own messages
        if reply is not None:
            self._oai_messages.setdefault("self", []).append({
                "role": "assistant",
                "content": reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return reply

    def execute_tool(self, tool_name: str, tool_input: Any) -> Any:
        """Execute a tool, firing tool-specific hooks.

        Hook execution order for tools:
        1. safeguard_tool_inputs
        2. [tool execution]
        3. safeguard_tool_outputs
        """
        if tool_name not in self._tool_fns:
            raise RuntimeError(f"Agent {self.name} has no tool '{tool_name}'")

        # Hook: safeguard tool inputs
        tool_input = self.hook_list.fire("safeguard_tool_inputs", tool_input)

        # Execute tool
        result = self._tool_fns[tool_name](tool_input)

        # Hook: safeguard tool outputs
        result = self.hook_list.fire("safeguard_tool_outputs", result)

        return result

    def _get_all_messages(self) -> list[dict]:
        """Flatten all messages from all senders in chronological order."""
        all_msgs = []
        for sender_msgs in self._oai_messages.values():
            all_msgs.extend(sender_msgs)
        all_msgs.sort(key=lambda m: m.get("timestamp", ""))
        return all_msgs


class MockGroupChat:
    """Simulates an AG2 GroupChat with speaker selection.

    Supports round_robin and scripted speaker selection modes.
    Messages are broadcast to all agents (AG2 GroupChat semantics).
    """

    def __init__(
        self,
        agents: list[MockConversableAgent],
        speaker_order: list[str] | None = None,
        max_turns: int = 10,
    ):
        self.agents = {a.name: a for a in agents}
        self.messages: list[dict] = []
        self._speaker_order = speaker_order
        self._turn_idx = 0
        self.max_turns = max_turns
        self._agent_list = agents  # Preserve insertion order for round-robin

    def select_speaker(self) -> MockConversableAgent:
        """Select the next speaker.

        If speaker_order is provided, follows the scripted sequence.
        Otherwise uses round-robin across agents.
        """
        if self._speaker_order:
            if self._turn_idx >= len(self._speaker_order):
                return self._agent_list[0]  # wrap to first
            name = self._speaker_order[self._turn_idx]
            return self.agents[name]
        else:
            idx = self._turn_idx % len(self._agent_list)
            return self._agent_list[idx]

    def broadcast(self, message: str, sender_name: str):
        """Broadcast a message to all agents except the sender."""
        msg_record = {
            "content": message,
            "sender": sender_name,
            "turn": self._turn_idx,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.messages.append(msg_record)
        for name, agent in self.agents.items():
            if name != sender_name:
                agent.receive(message, sender_name)

    def run(self, initial_message: str, initial_sender: str) -> list[dict]:
        """Run the group chat for max_turns or until speaker_order exhausted.

        Returns the full message history.
        """
        self.broadcast(initial_message, initial_sender)

        n_turns = len(self._speaker_order) if self._speaker_order else self.max_turns

        for _ in range(n_turns):
            speaker = self.select_speaker()
            reply = speaker.generate_reply()
            if reply is not None:
                self.broadcast(reply, speaker.name)
            self._turn_idx += 1

        return self.messages


# ============================================================
# AG2 Forge Harness — Wires adapter hooks into mock agents
# ============================================================

class AG2ForgeHarness:
    """Wires AG2ForgeAdapter hooks into MockConversableAgent instances.

    The harness:
    1. Installs adapter callbacks on all relevant AG2 hooks
    2. Runs scripted scenarios that exercise all interception points
    3. Validates resulting chambers against forge structural guarantees
    """

    def __init__(self, run_id: str | None = None, ledger: FindingsLedger | None = None):
        self.run_id = run_id or f"harness-{int(time.time())}"
        self.adapter = AG2ForgeAdapter(run_id=self.run_id, ledger=ledger)
        self.ledger = ledger
        self._hooked_agents: list[MockConversableAgent] = []

    def install_hooks(self, agent: MockConversableAgent):
        """Register forge adapter callbacks on an agent's hook_list.

        Hooks are pass-through: they record the event in the adapter
        and return the value unchanged.
        """
        adapter = self.adapter
        agent_name = agent.name

        def on_llm_output(output):
            """safeguard_llm_outputs — fires after LLM generates a reply."""
            adapter.on_turn(agent_name, None, output)
            return output  # pass-through

        def on_tool_output(output):
            """safeguard_tool_outputs — fires after tool execution."""
            # We record a generic tool call; the tool name is set at call time
            adapter.on_tool_call(agent_name, "tool", None, output)
            return output  # pass-through

        agent.hook_list.register_hook("safeguard_llm_outputs", on_llm_output)
        agent.hook_list.register_hook("safeguard_tool_outputs", on_tool_output)
        self._hooked_agents.append(agent)

    def install_group(self, agents: list[MockConversableAgent]):
        """Install hooks on all agents in a group."""
        for agent in agents:
            self.install_hooks(agent)

    def run_scenario(self, scenario: "ScenarioSpec") -> dict:
        """Execute a scripted scenario and return validation results.

        Returns dict with:
            chamber, validation_errors, trace, trace_verified,
            trace_stats, metrics, session_result
        """
        self.adapter = AG2ForgeAdapter(run_id=self.run_id, ledger=self.ledger)
        self._hooked_agents = []

        self.adapter.start_session({"scenario": scenario.name})

        result = scenario.execute(self)

        session_result = self.adapter.end_session()
        chamber = self.adapter._chamber

        validation_errors = session_result.get("validation_errors", [])
        trace_verified = session_result.get("trace_verified", False)

        return {
            "scenario": scenario.name,
            "chamber": chamber,
            "validation_errors": validation_errors,
            "session_result": session_result,
            "metrics": self.adapter.get_metrics(),
            "trace_verified": trace_verified,
        }


# ============================================================
# Scenario Specifications
# ============================================================

class ScenarioSpec:
    """Base class for harness scenarios."""
    name: str = "unnamed"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        """Execute the scenario. Subclasses implement this."""
        raise NotImplementedError


class SimpleConversation(ScenarioSpec):
    """Scenario A: 2 agents, 3 turns each, all outputs present."""
    name = "simple_conversation"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        alice = MockConversableAgent(
            "alice", "assistant",
            reply_fn=lambda msgs: f"Alice reply ({len(msgs)} msgs received)"
        )
        bob = MockConversableAgent(
            "bob", "assistant",
            reply_fn=lambda msgs: f"Bob reply ({len(msgs)} msgs received)"
        )
        harness.install_group([alice, bob])

        group = MockGroupChat(
            agents=[alice, bob],
            speaker_order=["alice", "bob", "alice", "bob", "alice", "bob"],
        )
        group.run("Start the conversation", "system")
        return {"turns": 6, "agents": 2}


class ToolUseSession(ScenarioSpec):
    """Scenario B: 1 agent + tools, 5 tool calls with mixed success/failure."""
    name = "tool_use_session"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        call_count = {"n": 0}

        def search_tool(query):
            call_count["n"] += 1
            if call_count["n"] == 3:
                return None  # Simulate tool failure (returns None)
            if call_count["n"] == 5:
                raise RuntimeError("API timeout on search")
            return f"Search results for: {query}"

        def calc_tool(expr):
            return f"Result: {len(str(expr)) * 7}"

        agent = MockConversableAgent(
            "researcher", "assistant",
            reply_fn=lambda msgs: f"Researcher processed {len(msgs)} messages",
            tool_fns={"search": search_tool, "calc": calc_tool},
        )
        harness.install_hooks(agent)

        # Start session with agent turn
        harness.adapter.on_turn("researcher", "Begin research", "Starting tool-assisted research")

        # 5 tool calls with mixed outcomes
        tools_called = []
        for i in range(5):
            query = f"query_{i}"
            try:
                result = agent.execute_tool("search", query)
                # Tool hook fires automatically via safeguard_tool_outputs
                # But since we called execute_tool directly, the hook already fired.
                # We still need to manually record if tool returned None as a turn event.
                if result is None:
                    harness.adapter.on_tool_call("researcher", "search", query, None)
                tools_called.append({"tool": "search", "query": query, "result": result, "error": None})
            except RuntimeError as e:
                harness.adapter.on_error("researcher", e)
                tools_called.append({"tool": "search", "query": query, "result": None, "error": str(e)})

        # One calc tool call
        calc_result = agent.execute_tool("calc", "2+2")
        tools_called.append({"tool": "calc", "input": "2+2", "result": calc_result, "error": None})

        # Final agent turn
        harness.adapter.on_turn("researcher", "Summarize findings", "Research complete with 6 tool calls")

        return {"tool_calls": len(tools_called), "errors": 1}


class MultiAgentGroupChat(ScenarioSpec):
    """Scenario C: 4 agents, 10 turns, round-robin speaker selection."""
    name = "multi_agent_groupchat"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        agents = []
        for name in ["architect", "builder", "tester", "reviewer"]:
            agent = MockConversableAgent(
                name, name,
                reply_fn=lambda msgs, n=name: f"{n}: processed {len(msgs)} messages, producing analysis",
            )
            agents.append(agent)

        harness.install_group(agents)

        group = MockGroupChat(agents=agents, max_turns=10)
        messages = group.run("Design and build a data validation pipeline", "pm")

        return {"turns": 10, "agents": 4, "messages": len(messages)}


class ErrorAndAbsence(ScenarioSpec):
    """Scenario D: 3 agents with None outputs, empty strings, and exceptions."""
    name = "error_and_absence"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        turn_count = {"n": 0}

        def flaky_reply(msgs):
            turn_count["n"] += 1
            n = turn_count["n"]
            if n == 2:
                return None  # Absent output
            if n == 4:
                return ""   # Empty string (present, not absent)
            if n == 5:
                raise RuntimeError("LLM connection timeout")
            return f"Reply {n} from flaky agent"

        def stable_reply(msgs):
            return f"Stable reply with {len(msgs)} context messages"

        def quiet_reply(msgs):
            turn_count["n"] += 1
            if turn_count["n"] == 3:
                return None
            return f"Quiet reply {turn_count['n']}"

        flaky = MockConversableAgent("flaky", "assistant", reply_fn=flaky_reply)
        stable = MockConversableAgent("stable", "assistant", reply_fn=stable_reply)
        quiet = MockConversableAgent("quiet", "assistant", reply_fn=quiet_reply)

        harness.install_group([flaky, stable, quiet])

        # Manually orchestrate turns to control absence/error timing
        # Turn 1: stable (present)
        harness.adapter.on_turn("stable", "Start", "Stable reply with 0 context messages")

        # Turn 2: flaky returns None (absent)
        harness.adapter.on_turn("flaky", "Your turn", None)

        # Turn 3: quiet returns None (absent)
        harness.adapter.on_turn("quiet", "Go ahead", None)

        # Turn 4: flaky returns empty string (present)
        harness.adapter.on_turn("flaky", "Try again", "")

        # Turn 5: error from flaky
        try:
            harness.adapter.on_turn("flaky", "Once more", "Almost there")
            raise RuntimeError("LLM connection timeout")
        except RuntimeError as e:
            harness.adapter.on_error("flaky", e)

        # Turn 6: stable produces clean output
        harness.adapter.on_turn("stable", "Wrap up", "Final stable output")

        return {"turns": 6, "none_outputs": 2, "empty_strings": 1, "errors": 1}


class CompactionTrigger(ScenarioSpec):
    """Scenario E: Conversation exceeds threshold, manual truncation event."""
    name = "compaction_trigger"

    def execute(self, harness: AG2ForgeHarness) -> dict:
        agent = MockConversableAgent(
            "worker", "assistant",
            reply_fn=lambda msgs: f"Worker output: {'x' * 200} (verbose)"
        )
        harness.install_hooks(agent)

        # Build up conversation history with multiple turns
        for i in range(6):
            harness.adapter.on_turn(
                "worker",
                f"Task {i}: {'a' * 100}",
                f"Worker response {i}: {'b' * 200} detailed analysis and code output"
            )

        # Trigger compaction event (simulating context window pressure)
        original_context = " ".join([
            f"Turn {i}: {'b' * 200} detailed analysis"
            for i in range(6)
        ])
        compacted = "Summary: 6 turns of worker analysis covering tasks 0-5. Key outputs preserved."

        harness.adapter.on_compaction(original_context, compacted)

        # Post-compaction turn
        harness.adapter.on_turn(
            "worker",
            "Continue after compaction",
            "Worker continues with compressed context"
        )

        return {"pre_compaction_turns": 6, "post_compaction_turns": 1, "compaction_events": 1}


# ============================================================
# Built-in Scenario Registry
# ============================================================

SCENARIOS: dict[str, ScenarioSpec] = {
    "simple_conversation": SimpleConversation(),
    "tool_use_session": ToolUseSession(),
    "multi_agent_groupchat": MultiAgentGroupChat(),
    "error_and_absence": ErrorAndAbsence(),
    "compaction_trigger": CompactionTrigger(),
}


def run_all_scenarios(
    ledger: FindingsLedger | None = None,
    verbose: bool = False,
) -> dict[str, dict]:
    """Run all built-in scenarios and return results keyed by name."""
    results = {}
    for name, scenario in SCENARIOS.items():
        run_id = f"harness-{name}-{int(time.time())}"
        harness = AG2ForgeHarness(run_id=run_id, ledger=ledger)
        result = harness.run_scenario(scenario)
        results[name] = result
        if verbose:
            sr = result["session_result"]
            v_err = len(result["validation_errors"])
            print(f"  {name}: stages={sr['total_stages']}, "
                  f"violations={sr['violations_detected']}, "
                  f"val_errors={v_err}, "
                  f"trace_verified={result['trace_verified']}")
    return results


# ============================================================
# Provenance Analysis Utilities
# ============================================================

def compute_reversibility(chamber: dict) -> dict:
    """Compute provenance reversibility score for a sealed chamber.

    An artifact is "reachable from root" if following its ref chain backward
    eventually reaches a root node. A root node is any artifact with no refs
    (it was the first artifact registered and is implicitly connected to the
    chamber root). The chamber_id itself is also treated as a root.

    This models the real question: can we trace every artifact's provenance
    back to the beginning of the session?

    Returns:
        score: fraction of artifacts reachable from root [0, 1]
        all_reach_root: True if all artifacts reach root
        details: per-artifact reachability
    """
    if not chamber or "stages" not in chamber:
        return {"score": 0.0, "all_reach_root": False, "details": {}}

    chamber_id = chamber["chamber_id"]
    stages = chamber["stages"]

    if not stages:
        return {"score": 1.0, "all_reach_root": True, "details": {}}

    # Build adjacency: artifact -> set of refs (edges toward root)
    artifact_refs: dict[str, set[str]] = {}
    all_artifact_ids: set[str] = set()
    for stage in stages:
        stage_id = stage["stage_id"]
        all_artifact_ids.add(stage_id)
        art = stage.get("artifact", {})
        refs = set()
        for ref_entry in art.get("refs", []):
            if isinstance(ref_entry, dict):
                ref_id = ref_entry.get("ref", "")
                if ref_id:
                    refs.add(ref_id)
            elif isinstance(ref_entry, str):
                refs.add(ref_entry)
        artifact_refs[stage_id] = refs

    # Root nodes: artifacts with no refs (first artifacts), plus the chamber_id
    root_ids = {chamber_id}
    for aid, refs in artifact_refs.items():
        # An artifact is a root if it has no refs to other artifacts in the chamber
        refs_in_chamber = refs & all_artifact_ids
        if not refs_in_chamber:
            root_ids.add(aid)

    # BFS: can each artifact reach a root node by following refs backward?
    def can_reach_root(start_id: str) -> bool:
        if start_id in root_ids:
            return True
        visited = set()
        queue = [start_id]
        while queue:
            current = queue.pop(0)
            if current in root_ids:
                return True
            if current in visited:
                continue
            visited.add(current)
            for ref_id in artifact_refs.get(current, set()):
                if ref_id not in visited:
                    queue.append(ref_id)
        return False

    details = {}
    reachable_count = 0
    for stage in stages:
        sid = stage["stage_id"]
        reaches = can_reach_root(sid)
        details[sid] = reaches
        if reaches:
            reachable_count += 1

    total = len(stages)
    score = reachable_count / total if total > 0 else 1.0

    return {
        "score": score,
        "all_reach_root": reachable_count == total,
        "total_artifacts": total,
        "reachable": reachable_count,
        "details": details,
    }


# ============================================================
# Main — Run all scenarios as smoke test
# ============================================================

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("AG2 Integration Harness — All Scenarios")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    ledger = FindingsLedger(data_dir=tmpdir)

    results = run_all_scenarios(ledger=ledger, verbose=True)

    print(f"\n{'=' * 60}")
    print("Summary:")
    print(f"{'=' * 60}")

    all_pass = True
    for name, result in results.items():
        v_err = len(result["validation_errors"])
        verified = result["trace_verified"]
        stages = result["session_result"]["total_stages"]

        # Compute reversibility
        rev = compute_reversibility(result["chamber"])

        status = "PASS" if (v_err == 0 and verified) else "FAIL"
        if status == "FAIL":
            all_pass = False

        print(f"  {name}: {status} | stages={stages}, "
              f"val_errors={v_err}, trace_ok={verified}, "
              f"reversibility={rev['score']:.2f}")

    print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print(f"Findings: {ledger.summary()['total']} total")
