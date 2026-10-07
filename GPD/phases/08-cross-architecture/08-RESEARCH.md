# Phase 8 Research: Cross-Architecture Generalization (RQ4)

**Phase:** 08-cross-architecture
**Research Question:** Do typed absence and provenance gains transfer beyond a single runtime into other agent architectures?
**Date:** 2026-03-27
**Gap Addressed:** XARCH-01 (multi-architecture validation required for PhD-level generality claim)
**Status:** COMPLETE -- ready for planning

---

## 1. Forge Tool Surface Summary

The forge instrumentation suite consists of six pure-Python modules (stdlib only) that enforce structural invariants on agent computation:

| Tool | Core Abstraction | Key API | What It Captures |
|------|-----------------|---------|-----------------|
| `forge_nulls.py` | 8-state typed absence | `absent()`, `validate_record()`, `validate_transition()` | Every empty/null field must declare WHY it is empty |
| `forge_reversible_summary.py` | Grounded summaries | `create_summary_view()`, `is_grounded()` | Every summary must have `source_refs` to original artifacts |
| `forge_stage_output.py` | Artifact envelopes | `create_v1_stage_artifact()`, `create_v1_stage_summary()` | Per-step output with provenance, hash, typed absence |
| `forge_chamber.py` | Multi-stage containers | `create_chamber()`, `register_stage()`, `seal_chamber()` | Full run lifecycle with ref validation at registration |
| `forge_trace_codec.py` | Structural compression | `encode_trace()`, `decode_trace()`, `verify_trace()` | Lossless compaction with exact round-trip verification |
| `forge_orchestrator.py` | Multi-seat orchestration | `run_chamber()` with `seat_specs` | Full orchestration with critique/revision/error handling |

**Existing adapter pattern:** `openclaw_adapter.py` demonstrates the proven approach:
- Post-hoc JSONL ledger parsing (Approach 2: non-invasive)
- Adapter class wraps framework lifecycle events into forge chamber artifacts
- Four interception points: per-turn, per-tool-call, compaction events, chamber lifecycle
- Metric computation delegated to bridge functions (reversibility, overhead, provenance depth)

---

## 2. Target Framework Architectures

### 2.1 LangGraph (LangChain)

**Version:** 1.0.x (stable as of March 2026)
**Repository:** `langchain-ai/langgraph`
**Core pattern:** Directed graph of stateful nodes communicating through a shared typed state

#### State Model

LangGraph uses `StateGraph` parameterized by a `TypedDict` state schema. State flows between nodes via **reducers** -- annotated functions that control how node outputs merge into the shared state.

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # reducer = add_messages
    plan: str

builder = StateGraph(AgentState)
builder.add_node("planner", planner_fn)
builder.add_node("executor", executor_fn)
builder.add_edge(START, "planner")
builder.add_conditional_edges("planner", route_fn, {"execute": "executor", "done": END})
graph = builder.compile(checkpointer=checkpointer)
```

Key classes and methods:
- `StateGraph(state_schema)` -- graph definition with typed state
- `.add_node(name, fn)` -- register a node function (receives state, returns partial state update)
- `.add_edge(src, dst)` -- fixed transition
- `.add_conditional_edges(src, condition_fn, mapping)` -- conditional routing
- `.compile(checkpointer=)` -- produces a `CompiledStateGraph` (implements `Runnable`)
- Compiled graph: `.invoke()`, `.stream()`, `.get_state()`, `.get_state_history()`

#### Checkpointing and Persistence

Checkpointers implement `BaseCheckpointSaver` with methods:
- `.put(config, checkpoint, metadata, new_versions)` -- store state snapshot
- `.put_writes(config, writes, task_id)` -- store pending writes
- `.get_tuple(config)` -- fetch checkpoint by thread_id + checkpoint_id
- `.list(config, filter, before, limit)` -- list checkpoint history
- `.delete_thread(thread_id)` -- cleanup
- `.get_next_version()` -- generate next version ID for a channel

Built-in implementations: `InMemorySaver`, `SqliteSaver`, `PostgresSaver`, `AsyncPostgresSaver`

**Where state loss happens:**
1. Reducer functions may silently drop or merge data (e.g., `add_messages` appends but custom reducers could overwrite)
2. No built-in checkpointer validates what changed between checkpoints
3. Conditional edges can route past nodes entirely -- those nodes produce nothing, but this is not tracked
4. Thread deletion via `delete_thread()` is unrecoverable
5. Long message lists accumulate without compaction -- users often truncate manually

#### Extensibility Points

1. **Custom checkpointer** -- subclass `BaseCheckpointSaver`, intercept every `.put()` call to wrap in forge artifacts
2. **LangChain middleware** -- `@hook_config` decorators for `before_model`, `after_model` hooks
3. **Node wrapper functions** -- wrap any node function with pre/post logic
4. **Callbacks** -- pass `CallbackHandler` via config to trace node execution
5. **State history replay** -- `get_state_history()` returns all checkpoints for a thread

#### Adapter Design

**Strategy: Custom ForgeCheckpointSaver wrapping an inner checkpointer**

The checkpointer interface is the primary interception point. Every state transition passes through `.put()`, making it the ideal place to register forge artifacts.

```python
class ForgeCheckpointSaver(BaseCheckpointSaver):
    """Forge-instrumented checkpointer that wraps any inner checkpointer."""

    def __init__(self, inner: BaseCheckpointSaver, adapter: ForgeLangGraphAdapter):
        self._inner = inner
        self._adapter = adapter

    def put(self, config, checkpoint, metadata, new_versions):
        # 1. Delegate to inner checkpointer
        result = self._inner.put(config, checkpoint, metadata, new_versions)
        # 2. Register state snapshot as forge artifact
        self._adapter.register_agent_output(
            agent_name=metadata.get("source", "unknown-node"),
            output=json.dumps(checkpoint, default=str),
            summary=f"Checkpoint at step {metadata.get('step', '?')}",
        )
        return result

    def get_tuple(self, config):
        return self._inner.get_tuple(config)

    def list(self, config, **kwargs):
        yield from self._inner.list(config, **kwargs)

    # ... remaining methods delegate to inner
```

Additionally, wrap node functions to capture per-node output and absence:

```python
def forge_wrap_node(node_fn, adapter, node_name):
    """Wrap a LangGraph node function with forge instrumentation."""
    def wrapped(state):
        try:
            result = node_fn(state)
            if result is None:
                adapter.register_absence_event(node_name, "not_generated", "Node returned None")
            else:
                adapter.register_agent_output(node_name, str(result))
            return result
        except Exception as e:
            adapter.register_absence_event(node_name, "invalid", str(e))
            raise
    return wrapped
```

**What to intercept:**
- `.put()` -- every state checkpoint becomes a forge artifact with source_refs to prior checkpoint
- `.put_writes()` -- pending writes (tool calls, node outputs) become sub-artifacts
- Node execution -- wrap each node fn to capture output/absence/errors
- Conditional edge routing -- log which branch was taken and which nodes were skipped
- Thread deletion -- register as `deleted` absence state

**Expected difficulty: MEDIUM**
- Clean `BaseCheckpointSaver` interface makes wrapping straightforward
- State is a typed dict -- can be validated against forge null discipline
- Challenge: reducers are opaque functions; cannot inspect merge logic without wrapping each one
- Challenge: middleware API is v1-alpha and may change
- Challenge: async variants needed for production (doubles implementation surface)

---

### 2.2 CrewAI

**Version:** Latest (actively developed, 2026)
**Repository:** `crewAIInc/crewAI`
**Core pattern:** Dual-layer architecture: deterministic Flows + autonomous Crews

#### State Model

CrewAI separates state management into two layers:

**Flows** (deterministic orchestration):
- `Flow[StateType]` -- generic class parameterized by Pydantic BaseModel or unstructured dict
- `@start()` -- marks entry point method
- `@listen(method)` -- chains execution by listening to upstream method output
- `@router` -- returns a string key that routes to matching `@listen("key")` step
- State is accessed via `self.state` (a Pydantic model instance)
- Each state gets auto-generated UUID for tracking

```python
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

class ExampleState(BaseModel):
    counter: int = 0
    message: str = ""

class StateExampleFlow(Flow[ExampleState]):
    @start()
    def first_method(self):
        self.state.message = "Hello from first_method"
        self.state.counter += 1

    @listen(first_method)
    def second_method(self):
        self.state.message += " - updated by second_method"
        self.state.counter += 1
        return self.state.message
```

**Crews** (autonomous agent teams):
- `Crew(agents=[...], tasks=[...], process=Process.sequential|hierarchical)`
- `Agent(role, goal, backstory, llm, tools, step_callback)`
- `Task(description, expected_output, agent, context, callback)`
- Crew execution: `crew.kickoff(inputs={})` returns `CrewOutput`

#### Where State Lives

1. **Flow state** -- Pydantic model on the Flow instance (`self.state`)
2. **Crew output** -- `CrewOutput` object with `.raw`, `.pydantic`, `.json_dict` properties
3. **Task output** -- `TaskOutput` with `.raw`, `.pydantic`, `.json_dict`, `.agent`
4. **Agent memory** -- short-term (conversation), long-term (persistent), entity memory
5. **Inter-task context** -- `Task.context` list references other tasks whose output feeds in

#### Extensibility Points

1. **`task_callback`** -- function called after each task completes, receives `TaskOutput`
2. **`step_callback`** -- function called after each agent reasoning step, set on Agent
3. **Flow `@listen` chaining** -- intercept between flow steps by adding listener methods
4. **Crew `output_log_file`** -- path to log all crew output
5. **Flow state mutation** -- all state changes go through `self.state` (inspectable)

#### Adapter Design

**Strategy: Callback-based instrumentation wrapping Crew + Flow**

```python
class ForgeCrewAIAdapter(ForgeBaseAdapter):
    """Forge adapter for CrewAI Crews and Flows."""

    def __init__(self, session_id: str):
        super().__init__(session_id, "crewai")
        self._task_count = 0
        self._step_count = 0
        self._prev_task_refs: list[str] = []

    def task_callback(self, output: TaskOutput) -> None:
        """Register each completed task as a forge artifact."""
        self._task_count += 1
        art_id = self.register_agent_output(
            agent_name=output.agent or "unknown",
            output=output.raw,
            source_refs=self._prev_task_refs if self._prev_task_refs else None,
            role="task-executor",
            summary=f"Task completed by {output.agent}.",
        )
        self._prev_task_refs = [art_id]

    def step_callback(self, step_output) -> None:
        """Register each agent reasoning step as a sub-artifact."""
        self._step_count += 1
        self.register_tool_call(
            tool_name="agent-step",
            input_data=str(step_output),
            output_data=str(step_output),
            parent_artifact=self._prev_task_refs[-1] if self._prev_task_refs else None,
        )

    def wrap_crew(self, crew) -> None:
        """Inject forge callbacks into a CrewAI Crew."""
        crew.task_callback = self.task_callback
        for agent in crew.agents:
            agent.step_callback = self.step_callback
```

**What to intercept:**
- `task_callback` on Crew -- each task completion becomes a forge artifact
- `step_callback` on Agent -- each reasoning step becomes a sub-artifact
- Flow state transitions -- `@listen` methods' inputs/outputs tracked
- Crew kickoff/completion -- chamber open/seal lifecycle
- Agent delegation events -- source_refs chain between delegating and receiving agents
- Memory operations -- when agent memory is consulted or updated

**Expected difficulty: LOW-MEDIUM**
- Callback system is simple and well-documented
- Pydantic state models are inspectable and validatable
- Challenge: `step_callback` signature is not well-documented; may vary between versions
- Challenge: agent-to-agent delegation within a crew is implicit; tracing requires instrumentation of the delegation mechanism
- Challenge: memory system is internal; may need monkey-patching to intercept reads/writes

---

### 2.3 OpenHands (formerly OpenDevin)

**Version:** V1 SDK (2026)
**Repository:** `OpenHands/software-agent-sdk`
**Core pattern:** Event-sourced state with Action-Execution-Observation triad

#### State Model

OpenHands V1 uses an event-sourcing architecture:

- **EventStream** -- central pub/sub hub; all communication flows as typed immutable events
- **ConversationState** -- single mutable source of truth (session metadata + EventLog)
- **EventLog** -- append-only log of all Action and Observation events
- **Actions** -- Pydantic-validated inputs (CmdRunAction, IPythonRunCellAction, BrowseAction, etc.)
- **Observations** -- structured outputs from action execution
- **AgentController** -- drives the agent loop: prompt -> LLM -> parse action -> execute -> observe -> update state

The core loop:
```
state (EventStream + metadata)
  -> generate prompt from history
  -> LLM completion
  -> parse Action from response
  -> execute Action in sandbox Runtime
  -> receive Observation
  -> append both to EventLog
  -> repeat
```

#### Where State Lives

1. **EventLog** -- append-only list of (Action, Observation) events
2. **ConversationState** -- mutable metadata (costs, delegation tracking, execution params)
3. **Persistence** -- `state.json` for metadata, individual JSON files per event
4. **Runtime sandbox** -- Docker container state (filesystem, processes)

#### Extensibility Points

1. **EventStream subscription** -- `event_stream.subscribe(EventStreamSubscriber.MAIN, on_event)` -- receive all events
2. **Agent server middleware** -- `@server.middleware` decorator for request/response interception
3. **Custom event types** -- extend the Action/Observation type hierarchy
4. **Pluggable hooks** -- user-definable hooks for skills and context components
5. **Deterministic replay** -- EventLog supports full replay from persisted events

#### Adapter Design

**Strategy: EventStream subscriber for live instrumentation**

```python
class ForgeOpenHandsAdapter(ForgeBaseAdapter):
    """Forge adapter for OpenHands V1 SDK."""

    def __init__(self, session_id: str):
        super().__init__(session_id, "openhands")
        self._action_count = 0
        self._last_action_id: str | None = None

    def on_event(self, event) -> None:
        """Subscribe to EventStream; register events as forge artifacts."""
        if hasattr(event, 'action'):
            self._register_action(event)
        elif hasattr(event, 'observation'):
            self._register_observation(event)

    def _register_action(self, event) -> None:
        self._action_count += 1
        source_refs = [self._last_action_id] if self._last_action_id else None
        art_id = self.register_agent_output(
            agent_name="openhands-agent",
            output=str(event),
            source_refs=source_refs,
            role="action-executor",
        )
        self._last_action_id = art_id

    def _register_observation(self, event) -> None:
        self.register_tool_call(
            tool_name=type(event).__name__,
            input_data="",
            output_data=str(event),
            parent_artifact=self._last_action_id,
        )

    def subscribe(self, conversation) -> None:
        """Attach to conversation's event stream."""
        conversation.event_stream.subscribe(
            EventStreamSubscriber.MAIN,
            self.on_event
        )
```

**What to intercept:**
- Every Action event -- becomes a forge artifact (output = action description/params)
- Every Observation event -- becomes a child artifact with source_ref to its Action
- Agent state resets -- register as absence events (state loss at agent restart)
- LLM context truncation -- if the agent loop truncates history, register as `pruned_recoverable`
- Sandbox state changes -- filesystem modifications tracked via Observation events
- Session persistence -- EventLog persistence events become compaction artifacts

**Expected difficulty: MEDIUM-HIGH**
- Event-sourced architecture aligns well with forge's append-only chamber model
- Pydantic validation on Actions matches forge's validation discipline
- Challenge: V1 SDK is new (2026); API may not be fully stable
- Challenge: EventStream subscription is the only clean hook; deeper instrumentation may require SDK modifications
- Challenge: Distinguishing "agent chose to do nothing" from "action failed silently" requires understanding Action subtypes
- Challenge: No built-in compaction mechanism -- state loss happens at the LLM context-window level, which is managed by the LLM client, not the SDK

---

### 2.4 AutoGen / AG2

**Version:** AG2 0.9.x (fork of Microsoft AutoGen 0.2)
**Repository:** `ag2ai/ag2` (AG2 fork) and `microsoft/autogen` (Microsoft v0.5+)
**Core pattern:** ConversableAgent with message passing and hook-based extensibility

**Note:** There are now TWO divergent codebases:
- **AG2** (formerly AutoGen 0.2): `ConversableAgent`, `GroupChatManager`, hook_lists. Community fork.
- **Microsoft AutoGen 0.5+**: `ChatAgent`, `on_messages()`, event-driven. Complete rewrite.

This analysis covers **AG2** (the 0.2 lineage) as it has the richer extensibility surface and larger deployment base.

#### State Model

AG2 agents communicate through **message passing** orchestrated by a `GroupChatManager`:

- `ConversableAgent` -- base class; maintains `_oai_messages` dict (conversation history per sender)
- `AssistantAgent` -- LLM-backed agent; generates replies via model
- `UserProxyAgent` -- human or code-execution proxy
- `GroupChat` -- multi-agent conversation container
- `GroupChatManager` -- orchestrates speaker selection and message broadcasting

Message flow in GroupChat:
```
Agent A sends message -> GroupChatManager receives
  -> GroupChatManager broadcasts to all agents
  -> GroupChatManager selects next speaker (round_robin|random|manual|auto)
  -> Selected agent generates reply
  -> repeat
```

#### Where State Lives

1. **`_oai_messages`** -- dict of message lists per conversation partner (on each agent)
2. **`context_variables`** -- shared `ContextVariables` dict across multi-agent chats
3. **`chat_messages`** -- GroupChat-level message history
4. **Agent memory** -- no built-in persistence; state lives in-process only
5. **Tool execution results** -- returned as messages in the conversation

#### Extensibility Points (AG2 hook system)

AG2 provides a comprehensive **hook_list** system on `ConversableAgent`:

| Hook | When Fired | Signature |
|------|-----------|-----------|
| `process_last_received_message` | Before reply generation | `(message: dict) -> dict` |
| `process_all_messages_before_reply` | Before reply generation | `(messages: list[dict]) -> list[dict]` |
| `process_message_before_send` | After reply generation | `(message: dict) -> dict` |
| `update_agent_state` | Before reply | `(agent, messages, sender, config) -> None` |
| `safeguard_tool_inputs` | Before tool execution | `(tool_input) -> tool_input` |
| `safeguard_tool_outputs` | After tool execution | `(tool_output) -> tool_output` |
| `safeguard_llm_inputs` | Before LLM call | `(messages) -> messages` |
| `safeguard_llm_outputs` | After LLM call | `(response) -> response` |
| `safeguard_human_inputs` | Before human input | `(input) -> input` |

Additionally:
- `register_reply(trigger, reply_func, position)` -- register custom reply generation functions
- `update_agent_state_before_reply` -- list of functions called before reply

#### Adapter Design

**Strategy: Hook-based instrumentation via hook_list registration**

```python
class ForgeAG2Adapter(ForgeBaseAdapter):
    """Forge adapter for AG2 (AutoGen 0.2 fork)."""

    def __init__(self, session_id: str):
        super().__init__(session_id, "ag2")
        self._message_count = 0
        self._installed_agents: set[str] = set()

    def install(self, agent) -> None:
        """Register forge hooks on an AG2 ConversableAgent."""
        agent_name = getattr(agent, 'name', 'unknown')
        if agent_name in self._installed_agents:
            return
        self._installed_agents.add(agent_name)

        agent.register_hook("process_message_before_send", self._on_message_send)
        agent.register_hook("safeguard_tool_outputs", self._on_tool_output)
        agent.register_hook("safeguard_llm_outputs", self._on_llm_output)

    def install_group(self, agents: list) -> None:
        """Install forge hooks on all agents in a group chat."""
        for agent in agents:
            self.install(agent)

    def _on_message_send(self, message: dict) -> dict:
        """Intercept every outgoing message and register as forge artifact."""
        self._message_count += 1
        content = message.get("content", "")
        if content is None or content == "":
            self.register_absence_event(
                agent_name=message.get("name", "unknown"),
                absence_state="not_generated",
                reason="Agent sent empty message",
            )
        else:
            self.register_agent_output(
                agent_name=message.get("name", "unknown"),
                output=str(content),
                role="conversable-agent",
            )
        return message  # pass-through: hooks must not alter semantics

    def _on_tool_output(self, output):
        """Register tool execution results as sub-artifacts."""
        self.register_tool_call(
            tool_name="ag2-tool",
            input_data="",
            output_data=str(output),
        )
        return output  # pass-through

    def _on_llm_output(self, response):
        """Track LLM responses for provenance."""
        # Register but do not modify
        return response
```

**What to intercept:**
- `process_message_before_send` -- every agent output becomes a forge artifact
- `safeguard_tool_inputs` / `safeguard_tool_outputs` -- tool calls become sub-artifacts with source_refs
- `safeguard_llm_inputs` / `safeguard_llm_outputs` -- LLM interactions tracked
- `update_agent_state` -- context_variables changes captured
- GroupChat speaker selection -- register which agent was chosen and which were skipped (absence events)
- Conversation truncation -- if `_oai_messages` is trimmed, register as `pruned_recoverable`

**Expected difficulty: LOW**
- Hook system is comprehensive and designed for exactly this kind of instrumentation
- All hooks are pass-through (receive value, must return it) -- forge can observe without modifying
- `register_reply` allows injecting custom reply logic at arbitrary positions
- Challenge: No built-in persistence; state loss = process termination (not recoverable)
- Challenge: GroupChat message broadcasting is implicit; tracing which agent received what requires hooking all agents
- Challenge: Microsoft AutoGen v0.5+ has a completely different API; adapter would need separate implementation

---

## 3. Architecture Comparison Table

| Dimension | LangGraph | CrewAI | OpenHands | AG2 (AutoGen 0.2) |
|-----------|-----------|--------|-----------|-------------------|
| **State model** | Shared TypedDict with reducers | Pydantic BaseModel on Flow; TaskOutput on Crew | Event-sourced EventLog + ConversationState | Message lists per agent (`_oai_messages`) + `context_variables` |
| **State mutation** | Node returns partial state; reducer merges | Direct `self.state.field = val` | Append-only events | Message append; direct attribute mutation |
| **Persistence** | Checkpointer (Postgres/SQLite/Memory) | None built-in (Flows are ephemeral) | state.json + per-event JSON files | None (in-process only) |
| **Multi-agent pattern** | Graph nodes (may be different agents) | Crew of agents with task delegation | Single agent with tool access (multi-agent via delegation) | GroupChat with speaker selection |
| **Compaction mechanism** | Manual message truncation; no built-in | None | LLM context-window management (external) | Manual message truncation |
| **Provenance support** | Checkpoint history with thread_id | Task `context` references; Flow `@listen` chains | EventLog with action->observation pairing | Message history (implicit ordering) |
| **Primary extensibility** | Custom checkpointer + middleware + callbacks | `task_callback` + `step_callback` + Flow decorators | EventStream subscription | hook_list system (9 hooks) + register_reply |
| **Interceptable state transitions** | Checkpoint put/get; node entry/exit | Task completion; agent step; flow step | Every event (Action/Observation) | Every message send/receive; every tool call; every LLM call |
| **Typed state validation** | TypedDict (static); reducers (runtime) | Pydantic (runtime validation) | Pydantic (Actions validated at creation) | None (dicts) |
| **Maturity** | Stable (v1.0+) | Active development; APIs shifting | V1 SDK new (2026); API stabilizing | Stable (AG2 fork); Microsoft version diverged |

---

## 4. OpenTelemetry GenAI Integration Design

### 4.1 Current OTel GenAI Semantic Conventions (v1.37+)

OpenTelemetry has defined semantic conventions for GenAI agent spans:

**Standard agent attributes:**
- `gen_ai.agent.id` -- unique identifier
- `gen_ai.agent.name` -- human-readable name
- `gen_ai.agent.description` -- free-form description
- `gen_ai.agent.version` -- version string
- `gen_ai.conversation.id` -- session/thread identifier
- `gen_ai.provider.name` -- provider discriminator
- `gen_ai.operation.name` -- operation type (`create_agent`, `invoke_agent`, `execute_tool`)
- `gen_ai.tool.name` -- tool being executed
- `gen_ai.tool.type` -- `Function` (client-side) or `Extension` (agent-side)

**Standard span types:**
- `create_agent` span -- agent creation
- `invoke_agent` span -- agent invocation (span kind: CLIENT or INTERNAL)
- `execute_tool` span -- tool execution within agent

**What is NOT in OTel today:**
- No typed absence attributes (no way to say "this agent produced nothing because X")
- No provenance chain attributes (no way to link outputs to inputs structurally)
- No compaction events (no way to mark state loss or recovery paths)
- No artifact lifecycle spans (created -> validated -> compacted -> deleted)

### 4.2 Forge-Specific OTel Extensions

We extend OTel with a `forge.*` attribute namespace for typed absence and provenance:

**Custom span attributes (on every agent/tool span):**

```
# Typed absence
forge.absence.state          = "not_generated" | "not_invoked" | "unknown" | ...
forge.absence.reason         = "LLM did not produce output"
forge.absence.transition     = "unknown -> pruned_recoverable"

# Provenance
forge.artifact.id            = "artifact:run500:stage:builder:r1"
forge.artifact.source_refs   = ["artifact:run500:stage:architect:r1"]
forge.artifact.type          = "stage_output" | "summary_view"
forge.artifact.hash          = "sha256:a1b2c3..."

# Chamber lifecycle
forge.chamber.id             = "chamber:run500:v1"
forge.chamber.status         = "open" | "sealed"
forge.chamber.stage_index    = 2

# Compaction
forge.compaction.type        = "cursor_advancement" | "llm_context_truncation" | "trace_compression"
forge.compaction.ratio       = 2.34
forge.compaction.recoverable = true
forge.compaction.refs_behind = ["artifact:run500:stage:architect:r1"]
```

**Custom span types:**

| Span Name | Operation | When |
|-----------|-----------|------|
| `forge.stage_register` | Stage artifact registered in chamber | On every node/task/action completion |
| `forge.absence_event` | Agent produced nothing or something invalid | On typed absence detection |
| `forge.compaction` | State was compacted/truncated/pruned | On any state loss event |
| `forge.chamber_seal` | Chamber sealed (run complete) | On run completion |
| `forge.ref_validation` | Source reference validated against chamber index | On every ref check |

**Integration pattern:**

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("forge.instrumentation", "1.0.0")

def register_stage_with_otel(chamber, artifact, summary):
    with tracer.start_as_current_span(
        f"forge.stage_register {artifact['id']}",
        kind=SpanKind.INTERNAL,
        attributes={
            "forge.artifact.id": artifact["id"],
            "forge.artifact.type": artifact.get("type", "stage_output"),
            "forge.artifact.hash": artifact.get("hash", {}).get("value", ""),
            "forge.chamber.id": chamber["chamber_id"],
            "forge.chamber.stage_index": len(chamber["stages"]),
            "gen_ai.agent.name": artifact.get("producer", {}).get("name", ""),
        }
    ) as span:
        entry = register_stage(chamber, artifact, summary)
        refs = artifact.get("refs", [])
        ref_ids = [r["ref"] for r in refs if isinstance(r, dict)]
        if ref_ids:
            span.set_attribute("forge.artifact.source_refs", ref_ids)
        if artifact.get("output") is None:
            span.set_attribute("forge.absence.state",
                               artifact.get("output_state", "unknown"))
        return entry
```

### 4.3 Compatibility with Existing Observability Tools

The `forge.*` namespace is a custom extension that coexists with standard OTel GenAI conventions:
- **Langfuse/LangSmith/Braintrust** will display forge spans as custom spans in their UIs
- **Datadog/New Relic/Grafana** will index forge attributes for querying
- **Standard OTel exporters** (OTLP, Jaeger, Zipkin) will carry forge attributes without modification
- No changes needed to OTel collector or SDKs; custom attributes are first-class in the OTel data model

---

## 5. Universal Adapter Architecture

### 5.1 Adapter Interface Contract

Every framework adapter must implement the same interface so that downstream analysis (metrics, reporting, OTel export) works identically regardless of source framework:

```python
from abc import ABC, abstractmethod

class ForgeAdapter(ABC):
    """Universal adapter interface for forge instrumentation."""

    @abstractmethod
    def __init__(self, session_id: str, framework: str): ...

    @abstractmethod
    def register_agent_output(
        self, agent_name: str, output: str | None,
        source_refs: list[str] | None = None, **kwargs,
    ) -> str:
        """Register an agent's output as a forge artifact. Returns artifact ID."""

    @abstractmethod
    def register_tool_call(
        self, tool_name: str, input_data: str, output_data: str | None,
        parent_artifact: str | None = None, **kwargs,
    ) -> str:
        """Register a tool call as a sub-artifact. Returns artifact ID."""

    @abstractmethod
    def register_compaction_event(
        self, compaction_type: str, refs_compacted: list[str], **kwargs,
    ) -> str:
        """Register a state loss/compaction event. Returns artifact ID."""

    @abstractmethod
    def register_absence_event(
        self, agent_name: str, absence_state: str,
        reason: str | None = None, **kwargs,
    ) -> str:
        """Register a typed absence event. Returns artifact ID."""

    @abstractmethod
    def finalize(self) -> dict:
        """Seal the chamber and return it."""

    @abstractmethod
    def get_analysis(self) -> dict:
        """Run full forge analysis (validation, trace, metrics)."""
```

### 5.2 Base Adapter Implementation

A `ForgeBaseAdapter` provides the common forge plumbing so framework-specific subclasses only implement the interception logic:

```python
class ForgeBaseAdapter(ForgeAdapter):
    """Common forge plumbing for all framework adapters."""

    def __init__(self, session_id: str, framework: str):
        self._session_id = session_id
        self._framework = framework
        self._chamber = create_chamber(f"chamber:{framework}:{session_id}:v1")
        self._artifact_counter = 0
        self._sealed = False

    def _next_artifact_id(self, kind: str, name: str) -> str:
        self._artifact_counter += 1
        return (f"artifact:{self._framework}:{self._session_id}"
                f":{kind}:{name}:{self._artifact_counter}:r1")

    def register_agent_output(self, agent_name, output, source_refs=None, **kwargs):
        stage_id = self._next_artifact_id("agent", agent_name)
        output_state = AbsenceState.NOT_GENERATED if output is None else None
        artifact = create_v1_stage_artifact(
            stage_id=stage_id,
            seat=f"{self._framework}-{agent_name}",
            producer_name=agent_name,
            producer_role=kwargs.get("role", "agent"),
            output=output,
            output_state=output_state,
            source_refs=source_refs,
        )
        summary_text = kwargs.get("summary", f"Output from {agent_name}.")
        if output is not None:
            summary = create_v1_stage_summary(
                artifact, summary_text, extra_source_refs=source_refs)
            register_stage(self._chamber, artifact, summary)
        else:
            register_stage(self._chamber, artifact,
                           summary_state="not_generated")
        return stage_id

    def finalize(self) -> dict:
        if not self._sealed:
            seal_chamber(self._chamber)
            self._sealed = True
        return self._chamber

    def get_analysis(self) -> dict:
        chamber = self.finalize()
        validation_errors = validate_chamber(chamber)
        trace = encode_trace(chamber)
        verification = verify_trace(trace, chamber)
        return {
            "validation_errors": len(validation_errors),
            "trace_verified": verification["valid"],
            "stage_count": len(chamber.get("stages", [])),
        }
```

### 5.3 Per-Framework Subclasses

Each framework adapter subclasses `ForgeBaseAdapter` and implements framework-specific interception:

- `ForgeLangGraphAdapter(ForgeBaseAdapter)` -- custom checkpointer + node wrappers
- `ForgeCrewAIAdapter(ForgeBaseAdapter)` -- task_callback + step_callback injection
- `ForgeOpenHandsAdapter(ForgeBaseAdapter)` -- EventStream subscription
- `ForgeAG2Adapter(ForgeBaseAdapter)` -- hook_list registration

---

## 6. Instrumentation Strategy Comparison

### 6.1 Live vs. Post-Hoc

| Approach | Pros | Cons | Applicable To |
|----------|------|------|--------------|
| **Live instrumentation** (callbacks/hooks) | Real-time; can reject invalid state; lower storage | Requires framework hooks; version-coupled | LangGraph, CrewAI, AG2 |
| **Post-hoc log analysis** (JSONL/event replay) | Non-invasive; works across frameworks; version-decoupled | Cannot prevent violations; higher latency; depends on log completeness | OpenHands, any framework with structured logs |
| **Hybrid** (live hooks + post-hoc verification) | Best of both; detect live + verify after | Most complex; two code paths | Recommended for all |

### 6.2 Recommended Approach Per Framework

| Framework | Primary Strategy | Secondary Strategy |
|-----------|-----------------|-------------------|
| **AG2** | Live hooks (hook_list) | Post-hoc message log replay |
| **LangGraph** | Live checkpointer wrapper | Post-hoc checkpoint history analysis |
| **CrewAI** | Live callbacks (task_callback, step_callback) | Post-hoc output_log_file parsing |
| **OpenHands** | Live EventStream subscription | Post-hoc EventLog replay from persisted JSON |

---

## 7. Priority Order and Feasibility Assessment

### Recommended implementation order:

| Priority | Framework | Rationale | Difficulty | Est. LOC | Time Est. |
|----------|-----------|-----------|------------|----------|-----------|
| **P0** | AG2 (AutoGen 0.2) | Richest hook system; lowest friction; large user base; direct comparison to OpenClaw adapter | LOW | ~400 | 1-2 days |
| **P1** | LangGraph | Most popular framework; clean checkpointer interface; state model maps well to forge chambers | MEDIUM | ~600 | 2-3 days |
| **P2** | CrewAI | Good callback system; Pydantic state aligns with forge validation; growing adoption | LOW-MEDIUM | ~450 | 1-2 days |
| **P3** | OpenHands | Event-sourced architecture is the best theoretical fit; but V1 SDK is newest and least stable | MEDIUM-HIGH | ~550 | 2-4 days |

**Rationale for P0 = AG2:**
1. Hook system covers all interception points needed (messages, tools, LLM, state)
2. Pass-through hook semantics mean forge never alters framework behavior
3. GroupChat pattern directly parallels forge's multi-seat orchestration
4. No external dependencies (no checkpointer service, no event stream)
5. Fastest path to proving the adapter pattern works across frameworks

**Rationale for P1 = LangGraph (not P0):**
1. Custom checkpointer requires implementing 6+ methods (put, get_tuple, list, put_writes, delete_thread, get_next_version)
2. Async variants needed for production use (doubles the implementation surface)
3. Reducer opacity means some state mutations are invisible
4. But: largest user base and most standard architecture; highest impact for paper

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **Framework API instability** | Adapters break on version upgrades | HIGH (CrewAI, OpenHands) | Pin versions; version-gate adapter code; abstract framework calls behind thin wrappers |
| **Reducer opacity in LangGraph** | Cannot inspect how state was merged | MEDIUM | Wrap individual reducers; compare pre/post state snapshots |
| **Hook signature changes in AG2** | Adapter hooks may not match new signatures | LOW (AG2 stable) | Use defensive kwargs; register hooks dynamically |
| **EventStream API changes in OpenHands** | Subscription pattern may change in V1 | MEDIUM-HIGH | Isolate all OpenHands imports behind adapter boundary; test against pinned SDK version |
| **Overhead too high for production** | Forge instrumentation slows agent execution | LOW | Post-hoc mode fallback; lazy validation; configurable verbosity |
| **Incomplete interception** | Some state transitions invisible to adapter | MEDIUM | Characterize coverage per framework; document known gaps; combine live + post-hoc |

### 8.2 What Might Not Work Without Framework Modifications

| Framework | Limitation | What Would Need to Change |
|-----------|-----------|--------------------------|
| **LangGraph** | Reducer merge logic is invisible; conditional edge "skipped nodes" not reported | Would need reducer wrapper protocol or post-merge diff hook |
| **CrewAI** | Agent-to-agent delegation is implicit; memory reads are internal | Would need delegation event hook; memory access callback |
| **OpenHands** | LLM context truncation happens in LLM client, not SDK | Would need LLM client wrapper or truncation event in EventStream |
| **AG2** | No built-in persistence; process death = total state loss | Would need external state persistence (not a framework problem) |

### 8.3 What Requires Zero Framework Modifications

All four adapters can capture without any framework patches:
- Agent outputs (present or absent, with typed absence states)
- Tool call inputs/outputs (with provenance refs)
- Provenance chains (which output depends on which input)
- Run lifecycle (start, completion, error, seal)
- Structural trace compression (lossless round-trip)
- Full forge validation and metric computation

This is the same coverage the OpenClaw adapter achieves today.

---

## 9. Validation Plan

For each adapter, demonstrate the same metrics validated in v1.0:

| Metric | Definition | Target | Measurement |
|--------|-----------|--------|-------------|
| **Reversibility score** | Fraction of artifacts with valid provenance chain to root | >= 0.95 | `compute_reversibility_score(chamber)` |
| **Provenance depth** | Max chain depth; all chains reach chamber root | all_reach_root = True | `compute_provenance_depth(chamber)` |
| **Trace integrity** | Compressed trace round-trips exactly | hash_match = True | `verify_trace(trace, chamber)` |
| **Null discipline** | Zero ambiguous empties in any artifact | 0 violations | `validate_chamber(chamber)` |
| **Overhead ratio** | Forge trace size / vanilla log size | < 3x | `compute_overhead(trace, vanilla_size)` |
| **Fault detection** | Injected faults detected by forge validation | >= 90% | Fault injection campaign per framework |

**Cross-architecture comparison matrix:**

For each of the 4 frameworks, run 50+ agent sessions through the forge adapter and compare:
1. Do the same forge guarantees hold? (reversibility, provenance, null discipline)
2. What is the overhead per framework?
3. What state transitions are invisible to the adapter? (coverage gap analysis)
4. Does the adapter introduce any behavioral changes? (semantic neutrality test)

---

## 10. Key Findings and Decisions

### Findings

1. **All four frameworks have sufficient extensibility for forge instrumentation.** None requires core framework patches for basic adapter functionality.

2. **AG2's hook system is the closest architectural match** to forge's interception model. The 9-hook system covers messages, tools, LLM calls, and state updates -- exactly the four categories forge needs to track.

3. **LangGraph's checkpointer interface is the cleanest integration point** for state persistence tracking, but the most implementation-heavy (6+ methods, sync + async).

4. **CrewAI's callback system is the simplest** but has the largest gap: agent-to-agent delegation within a Crew is not directly observable without framework changes.

5. **OpenHands V1 SDK's event-sourced architecture is the strongest theoretical match** for forge's append-only chamber model, but the SDK is the newest and least stable.

6. **OpenTelemetry GenAI conventions lack typed absence, provenance, and compaction semantics.** The `forge.*` namespace extension fills this gap without conflicting with standard attributes.

7. **The OpenClaw adapter pattern generalizes cleanly.** The four interception points (per-turn, per-tool-call, compaction, lifecycle) map to concrete extensibility points in all four frameworks.

### Decisions

- **XARCH-D01:** Implement AG2 adapter first (P0) to validate the universal adapter pattern with minimal friction
- **XARCH-D02:** Use hybrid strategy (live hooks + post-hoc verification) for all adapters
- **XARCH-D03:** Define `ForgeAdapter` ABC and `ForgeBaseAdapter` base class before any framework-specific code
- **XARCH-D04:** OTel integration via `forge.*` custom attribute namespace, compatible with all standard exporters
- **XARCH-D05:** Target 50+ sessions per framework for cross-architecture comparison matrix
- **XARCH-D06:** Pin framework versions for reproducibility; document exact versions in adapter code

---

## Sources

- [LangGraph Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph StateGraph API (DeepWiki)](https://deepwiki.com/langchain-ai/langgraph/3.1-stategraph-api)
- [LangGraph Checkpointing Architecture (DeepWiki)](https://deepwiki.com/langchain-ai/langgraph/4.1-checkpointing-architecture)
- [LangGraph Persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Custom Checkpointer (LangChain Forum)](https://forum.langchain.com/t/how-to-implement-custom-basecheckpointsaver/1606)
- [LangChain Middlewares (Medium)](https://medium.com/@ale.garavaglia/langchain-middlewares-lightweight-hooks-for-more-structured-agents-f0abba828934)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [CrewAI Flows documentation](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Tasks documentation](https://docs.crewai.com/en/concepts/tasks)
- [CrewAI State Management (DeepWiki)](https://deepwiki.com/crewAIInc/crewAI/3.3-state-management)
- [CrewAI Unique Features (Vadim's blog)](https://vadim.blog/crewai-unique-features)
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk)
- [OpenHands SDK paper (arXiv:2511.03690)](https://arxiv.org/html/2511.03690v1)
- [OpenHands SDK GitHub](https://github.com/OpenHands/software-agent-sdk/)
- [OpenHands SDK ConversationState source](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/state.py)
- [AG2 ConversableAgent API](https://docs.ag2.ai/latest/docs/api-reference/autogen/ConversableAgent/)
- [AG2 Hooks documentation](https://docs.ag2.ai/latest/docs/contributor-guide/how-ag2-works/hooks/)
- [AG2 Generate Reply documentation](https://docs.ag2.ai/latest/docs/contributor-guide/how-ag2-works/generate-reply/)
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [AutoGen 0.2 ConversableAgent reference](https://microsoft.github.io/autogen/0.2/docs/reference/agentchat/conversable_agent/)
- [OTel GenAI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [OTel GenAI Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
- [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OTel GenAI Attribute Registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)
- [OTel semantic-conventions v1.37.0 gen-ai docs](https://github.com/open-telemetry/semantic-conventions/tree/v1.37.0/docs/gen-ai)
- [Langfuse LangGraph integration](https://langfuse.com/guides/cookbook/integration_langgraph)
- [Braintrust framework comparison (2026)](https://www.braintrust.dev/articles/langsmith-alternatives-2026)
- [AI Agent Frameworks comparison (2026)](https://designrevision.com/blog/ai-agent-frameworks)
