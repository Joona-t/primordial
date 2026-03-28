"""ForgeAdapter — universal adapter interface for cross-architecture instrumentation.

Every agent framework adapter implements this ABC. The adapter captures
state transitions, output lifecycle, provenance chains, and absence events,
mapping them into forge artifacts registered in a chamber.

Phase 8 of Primordial v2.0 (RQ4: cross-architecture generalization).

Supported frameworks (planned):
    P0: AG2 (AutoGen v2) — 9-hook system
    P1: LangGraph — callbacks + custom checkpointer
    P2: CrewAI — task hooks
    P3: OpenHands — event stream

The existing OpenClaw adapter (tools/openclaw_adapter.py) is the reference
implementation. This ABC formalizes the pattern it established.
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent))

from forge_nulls import AbsenceState, validate_record
from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from findings_ledger import FindingsLedger, Finding


# --- Interception Events ---

@dataclass
class InterceptionEvent:
    """A captured state transition from an agent framework."""
    event_type: str          # "turn", "tool_call", "compaction", "lifecycle", "error"
    timestamp: str
    seat: str                # agent/node/role name
    input_data: Any = None
    output_data: Any = None
    output_state: str | None = None  # AbsenceState if output is absent
    parent_ref: str | None = None    # artifact ID of parent/upstream
    metadata: dict = field(default_factory=dict)
    error: str | None = None


# --- ForgeAdapter ABC ---

class ForgeAdapter(ABC):
    """Abstract base for framework-specific forge adapters.

    Subclasses implement the 4 interception points:
    1. on_turn — agent produces a response/output
    2. on_tool_call — agent calls a tool/function
    3. on_compaction — context is compacted/summarized
    4. on_lifecycle — session start/end, agent spawn/exit

    The base class handles:
    - Chamber lifecycle (create, seal, validate)
    - Artifact registration (stage_id generation, ref chains)
    - Trace encoding and verification
    - Findings ledger integration
    """

    def __init__(
        self,
        framework_name: str,
        run_id: str | None = None,
        ledger: FindingsLedger | None = None,
    ):
        self.framework_name = framework_name
        self.run_id = run_id or f"run-{int(time.time())}"
        self.ledger = ledger
        self._chamber = None
        self._artifact_ids: list[str] = []
        self._stage_counter = 0
        self._events: list[InterceptionEvent] = []
        self._violations: list[dict] = []
        self._started = False

    # --- Chamber Lifecycle ---

    def start_session(self, metadata: dict | None = None):
        """Initialize a forge chamber for this session."""
        self._chamber = create_chamber(
            f"chamber:{self.framework_name}:{self.run_id}:v1"
        )
        self._started = True
        self._record_lifecycle("session_start", metadata or {})

    def end_session(self) -> dict:
        """Seal the chamber, validate, encode trace, return results."""
        if not self._started or not self._chamber:
            return {"error": "Session not started"}

        self._record_lifecycle("session_end", {})
        seal_chamber(self._chamber)

        validation_errors = validate_chamber(self._chamber)
        trace = encode_trace(self._chamber)
        verification = verify_trace(trace, self._chamber)
        stats = trace_stats(trace)

        result = {
            "run_id": self.run_id,
            "framework": self.framework_name,
            "total_stages": self._stage_counter,
            "total_events": len(self._events),
            "violations_detected": len(self._violations),
            "validation_errors": validation_errors,
            "trace_stats": stats,
            "trace_verified": verification.get("valid", False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log to findings ledger
        if self.ledger:
            self.ledger.record(Finding(
                phase=8, category="architecture", rq="RQ4",
                title=f"{self.framework_name} session: {self._stage_counter} stages, "
                      f"{len(self._violations)} violations",
                description=f"Run {self.run_id} on {self.framework_name}. "
                            f"{self._stage_counter} artifacts registered, "
                            f"{len(self._violations)} violations detected.",
                evidence=result,
                verdict="pending", confidence="medium",
                tags=["XARCH-01", f"framework:{self.framework_name}"],
            ))

        self._started = False
        return result

    # --- Artifact Registration ---

    def _next_stage_id(self, seat: str) -> str:
        """Generate the next artifact ID."""
        self._stage_counter += 1
        return f"artifact:{self.framework_name}:{self.run_id}:stage:{seat}:{self._stage_counter}:r1"

    def _register_artifact(
        self,
        seat: str,
        output: str | None,
        output_state: str | None = None,
        source_refs: list[str] | None = None,
        summary_text: str | None = None,
        producer_role: str = "agent",
        metadata: dict | None = None,
    ) -> str:
        """Register an artifact in the chamber. Returns artifact ID."""
        if not self._chamber:
            raise RuntimeError("Session not started. Call start_session() first.")

        stage_id = self._next_stage_id(seat)
        refs = source_refs or []

        # If no explicit refs and we have previous artifacts, ref the last one
        if not refs and self._artifact_ids:
            refs = [self._artifact_ids[-1]]

        # Handle absence
        if output is None and output_state is None:
            output_state = AbsenceState.NOT_GENERATED

        artifact = create_v1_stage_artifact(
            stage_id=stage_id,
            seat=seat,
            producer_name=f"{self.framework_name}-adapter",
            producer_role=producer_role,
            output=output,
            output_state=output_state,
            source_refs=refs,
        )

        # Summary
        if summary_text is None and output:
            summary_text = f"{seat} output ({len(output)} chars)"
        summary = None
        if summary_text:
            summary = create_v1_stage_summary(artifact, summary_text, extra_source_refs=refs)

        register_stage(self._chamber, artifact, summary)
        self._artifact_ids.append(stage_id)

        return stage_id

    # --- Violation Detection ---

    def _check_violation(self, event: InterceptionEvent):
        """Check an interception event for structural violations."""
        violations = []

        # D1: Empty output without typed absence
        if event.output_data is None and event.output_state is None:
            violations.append({
                "type": "D1", "description": "Empty output without typed absence state",
                "event_type": event.event_type, "seat": event.seat,
            })

        # D2: Check for ungrounded output (no context of what produced it)
        if event.output_data and not event.parent_ref and len(self._artifact_ids) > 0:
            violations.append({
                "type": "D2_warning", "description": "Output without explicit parent ref",
                "event_type": event.event_type, "seat": event.seat,
            })

        # D5: Bare None in structured output
        if isinstance(event.output_data, dict):
            for k, v in event.output_data.items():
                if v is None and f"{k}_state" not in event.output_data:
                    violations.append({
                        "type": "D5", "description": f"Bare None in field '{k}' without state",
                        "event_type": event.event_type, "seat": event.seat,
                    })

        if violations:
            self._violations.extend(violations)
            if self.ledger:
                for v in violations:
                    self.ledger.record(Finding(
                        phase=8, category="violation", rq="RQ2b",
                        title=f"Violation {v['type']} in {self.framework_name}: {v['description'][:60]}",
                        description=v["description"],
                        evidence=v,
                        verdict="positive" if not v["type"].endswith("_warning") else "neutral",
                        confidence="high",
                        tags=["VIOL-04", f"framework:{self.framework_name}", v["type"]],
                    ))

    # --- Lifecycle Events ---

    def _record_lifecycle(self, event_type: str, metadata: dict):
        self._events.append(InterceptionEvent(
            event_type="lifecycle",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat="system",
            metadata={**metadata, "lifecycle": event_type},
        ))

    # --- Abstract Interception Points (subclasses implement) ---

    @abstractmethod
    def on_turn(self, seat: str, input_data: Any, output_data: Any, **kwargs) -> str:
        """Called when an agent produces a response.

        Returns the registered artifact ID.
        """

    @abstractmethod
    def on_tool_call(self, seat: str, tool_name: str, tool_input: Any,
                     tool_output: Any, **kwargs) -> str:
        """Called when an agent invokes a tool.

        Returns the registered artifact ID.
        """

    @abstractmethod
    def on_compaction(self, original_content: str, compacted_content: str, **kwargs) -> str:
        """Called when context is compacted/summarized.

        Returns the registered artifact ID.
        """

    def on_error(self, seat: str, error: Exception, **kwargs) -> str:
        """Called when an error occurs. Default implementation provided."""
        event = InterceptionEvent(
            event_type="error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat=seat,
            output_data=None,
            output_state=AbsenceState.INVALID,
            error=str(error),
            metadata=kwargs,
        )
        self._events.append(event)
        self._check_violation(event)

        return self._register_artifact(
            seat=seat,
            output=None,
            output_state=AbsenceState.INVALID,
            summary_text=f"Error in {seat}: {type(error).__name__}: {str(error)[:100]}",
            producer_role="error-handler",
        )

    # --- Metrics ---

    def get_metrics(self) -> dict:
        """Current metrics for this session."""
        return {
            "framework": self.framework_name,
            "run_id": self.run_id,
            "stages": self._stage_counter,
            "events": len(self._events),
            "violations": len(self._violations),
            "violation_types": list(set(v["type"] for v in self._violations)),
            "artifact_ids": list(self._artifact_ids),
        }


# --- AG2 Adapter (P0) ---

class AG2ForgeAdapter(ForgeAdapter):
    """Forge adapter for AG2 (AutoGen v2).

    AG2 provides 9 hooks: before/after message send, before/after tool call,
    before/after LLM call, state change, error, and custom. This adapter
    maps the most relevant ones to forge interception points.

    Usage:
        adapter = AG2ForgeAdapter(run_id="exp-001", ledger=ledger)
        adapter.start_session()

        # In AG2 hook callbacks:
        adapter.on_turn("assistant", input_msg, output_msg)
        adapter.on_tool_call("assistant", "search", query, results)

        results = adapter.end_session()
    """

    def __init__(self, run_id: str | None = None, ledger: FindingsLedger | None = None):
        super().__init__(framework_name="ag2", run_id=run_id, ledger=ledger)

    def on_turn(self, seat: str, input_data: Any, output_data: Any, **kwargs) -> str:
        output_text = str(output_data) if output_data is not None else None
        # Empty string is present (agent responded), not absent.
        # Wrap to forge-safe sentinel so null discipline doesn't reject it.
        if output_text == "":
            output_text = "<empty_response>"
        output_state = None if output_text is not None else AbsenceState.NOT_GENERATED

        event = InterceptionEvent(
            event_type="turn",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat=seat,
            input_data=str(input_data)[:500] if input_data else None,
            output_data=output_text,
            output_state=output_state,
            parent_ref=self._artifact_ids[-1] if self._artifact_ids else None,
            metadata=kwargs,
        )
        self._events.append(event)
        self._check_violation(event)

        return self._register_artifact(
            seat=seat,
            output=output_text,
            output_state=output_state,
            producer_role="ag2-agent",
            summary_text=f"AG2 {seat} turn: {len(output_text or '')} chars",
        )

    def on_tool_call(self, seat: str, tool_name: str, tool_input: Any,
                     tool_output: Any, **kwargs) -> str:
        output_text = str(tool_output) if tool_output is not None else None
        # Empty string is present (tool returned), not absent
        if output_text == "":
            output_text = "<empty_tool_output>"
        output_state = None if output_text is not None else AbsenceState.NOT_GENERATED

        event = InterceptionEvent(
            event_type="tool_call",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat=seat,
            input_data={"tool": tool_name, "input": str(tool_input)[:300]},
            output_data=output_text,
            output_state=output_state,
            parent_ref=self._artifact_ids[-1] if self._artifact_ids else None,
            metadata={**kwargs, "tool_name": tool_name},
        )
        self._events.append(event)
        self._check_violation(event)

        return self._register_artifact(
            seat=f"{seat}-tool-{tool_name}",
            output=output_text,
            output_state=output_state,
            producer_role="ag2-tool",
            summary_text=f"AG2 tool call: {tool_name} → {len(output_text or '')} chars",
        )

    def on_compaction(self, original_content: str, compacted_content: str, **kwargs) -> str:
        # AG2 doesn't have built-in compaction, but this handles manual truncation
        from semantic_provenance_fidelity import SPFMetric
        spf = SPFMetric()
        scores = spf.measure(original_content, compacted_content)

        event = InterceptionEvent(
            event_type="compaction",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat="system",
            input_data=original_content[:500],
            output_data=compacted_content[:500],
            metadata={**kwargs, "spf_scores": scores},
        )
        self._events.append(event)

        # Register with source refs to all previous artifacts
        return self._register_artifact(
            seat="compactor",
            output=compacted_content,
            source_refs=list(self._artifact_ids),
            producer_role="ag2-compactor",
            summary_text=f"Compaction: {len(original_content)} → {len(compacted_content)} chars, "
                         f"SPF jaccard={scores['jaccard']:.3f}",
        )


# --- LangGraph Adapter (P1) ---

class LangGraphForgeAdapter(ForgeAdapter):
    """Forge adapter for LangGraph.

    LangGraph uses StateGraph with typed state dicts. Nodes are functions
    that transform state. Edges define transitions. Checkpointers persist state.

    This adapter hooks into:
    - Node execution (before/after) via callbacks
    - State transitions via checkpointer intercepts
    - Message history truncation as compaction events
    """

    def __init__(self, run_id: str | None = None, ledger: FindingsLedger | None = None):
        super().__init__(framework_name="langgraph", run_id=run_id, ledger=ledger)

    def on_turn(self, seat: str, input_data: Any, output_data: Any, **kwargs) -> str:
        output_text = json.dumps(output_data) if isinstance(output_data, dict) else str(output_data or "")
        # Empty string is present (node responded), not absent
        if output_text == "":
            output_text = "<empty_response>"
        output_state = None if output_text else AbsenceState.NOT_GENERATED

        event = InterceptionEvent(
            event_type="turn",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat=seat,
            input_data=str(input_data)[:500] if input_data else None,
            output_data=output_text[:1000],
            output_state=output_state,
            parent_ref=self._artifact_ids[-1] if self._artifact_ids else None,
            metadata=kwargs,
        )
        self._events.append(event)
        self._check_violation(event)

        return self._register_artifact(
            seat=seat,
            output=output_text,
            output_state=output_state,
            producer_role="langgraph-node",
            summary_text=f"LangGraph node '{seat}': {len(output_text)} chars",
        )

    def on_tool_call(self, seat: str, tool_name: str, tool_input: Any,
                     tool_output: Any, **kwargs) -> str:
        output_text = str(tool_output) if tool_output is not None else None
        # Empty string is present (tool returned), not absent
        if output_text == "":
            output_text = "<empty_tool_output>"
        output_state = None if output_text is not None else AbsenceState.NOT_GENERATED

        event = InterceptionEvent(
            event_type="tool_call",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat=seat,
            input_data={"tool": tool_name, "input": str(tool_input)[:300]},
            output_data=output_text,
            output_state=output_state,
            parent_ref=self._artifact_ids[-1] if self._artifact_ids else None,
            metadata={**kwargs, "tool_name": tool_name},
        )
        self._events.append(event)
        self._check_violation(event)

        return self._register_artifact(
            seat=f"{seat}-tool-{tool_name}",
            output=output_text,
            output_state=output_state,
            producer_role="langgraph-tool",
            summary_text=f"LangGraph tool: {tool_name}",
        )

    def on_compaction(self, original_content: str, compacted_content: str, **kwargs) -> str:
        from semantic_provenance_fidelity import SPFMetric
        spf = SPFMetric()
        scores = spf.measure(original_content, compacted_content)

        event = InterceptionEvent(
            event_type="compaction",
            timestamp=datetime.now(timezone.utc).isoformat(),
            seat="system",
            input_data=original_content[:500],
            output_data=compacted_content[:500],
            metadata={**kwargs, "spf_scores": scores},
        )
        self._events.append(event)

        return self._register_artifact(
            seat="compactor",
            output=compacted_content,
            source_refs=list(self._artifact_ids),
            producer_role="langgraph-compactor",
            summary_text=f"LangGraph compaction: SPF={scores['jaccard']:.3f}",
        )


if __name__ == "__main__":
    from findings_ledger import FindingsLedger

    ledger = FindingsLedger()

    print("=" * 60)
    print("ForgeAdapter Demo — AG2 Adapter")
    print("=" * 60)

    adapter = AG2ForgeAdapter(run_id="demo-ag2-001", ledger=ledger)
    adapter.start_session({"demo": True})

    # Simulate multi-turn conversation
    adapter.on_turn("architect", "Design the system", "Here is the architecture plan with 5 components...")
    adapter.on_turn("builder", "Implement component 1", "def component_1():\n    return 'built'")
    adapter.on_tool_call("builder", "run_tests", {"file": "test_comp1.py"}, "3 tests passed")
    adapter.on_turn("critic", "Review the implementation", None)  # Empty output → violation
    adapter.on_turn("builder", "Fix based on review", "Updated implementation with error handling")
    adapter.on_compaction(
        "Full conversation history with 5 turns of detailed output...",
        "Summary: architecture designed, component 1 built and tested",
    )
    adapter.on_turn("builder", "Continue with component 2", "def component_2():\n    pass")

    results = adapter.end_session()

    print(f"\nRun: {results['run_id']}")
    print(f"Framework: {results['framework']}")
    print(f"Stages: {results['total_stages']}")
    print(f"Events: {results['total_events']}")
    print(f"Violations: {results['violations_detected']}")
    print(f"Trace verified: {results['trace_verified']}")
    print(f"Validation errors: {len(results['validation_errors'])}")

    metrics = adapter.get_metrics()
    if metrics["violation_types"]:
        print(f"Violation types: {metrics['violation_types']}")

    print(f"\nFindings ledger: {ledger.summary()['total']} total findings")
