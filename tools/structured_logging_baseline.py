"""
structured_logging_baseline.py -- Intermediate baseline with standard observability.

Provides span-based event recording, schema validation, timing instrumentation,
token counting, and error recording WITHOUT any forge-specific features.

This baseline isolates the differential value of forge's typed absence and
provenance from the general value of "any structured validation." If this
baseline catches the same errors as forge, then forge adds no differential
value. If forge catches errors this baseline misses, the difference is
attributable to typed absence and provenance.

MUST NOT INCLUDE (these are forge-specific features):
- Typed absence states (no AbsenceState enum, no normalize_absence_state())
- Provenance DAG (no source_refs, no parent_id linkage)
- Hash-verified trace compression (no encode_trace/decode_trace)
- Structural violation detection (no validate_transition, no null discipline)

Convention compliance:
- No imports from forge_nulls, forge_chamber, forge_trace_codec, or
  forge_reversible_summary (acceptance test: test-structured-logging-distinct)
- "Compaction" always qualified per Convention #6

Dependencies: Python stdlib only (logging, json, time, datetime).
OpenTelemetry is optional -- uses lightweight dict-based spans if unavailable.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

# --- Optional OpenTelemetry support ---

_OTEL_AVAILABLE = False
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

    _OTEL_AVAILABLE = True
except ImportError:
    pass


# --- Lightweight span implementation (used when OpenTelemetry unavailable) ---


class Span:
    """Lightweight span for structured event recording.

    Dict-based with start/end timestamps and arbitrary attributes.
    Used when OpenTelemetry is not available.
    """

    def __init__(
        self,
        name: str,
        *,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ):
        self.span_id = uuid.uuid4().hex[:16]
        self.name = name
        self.parent_span_id = parent_span_id
        self.attributes = dict(attributes) if attributes else {}
        self.start_time: float = time.monotonic()
        self.start_timestamp: str = _utc_iso_z()
        self.end_time: float | None = None
        self.end_timestamp: str | None = None
        self.status: str = "ok"
        self.error: str | None = None
        self.events: list[dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": _utc_iso_z(),
            "attributes": dict(attributes) if attributes else {},
        })

    def set_error(self, error: Exception) -> None:
        self.status = "error"
        self.error = f"{type(error).__name__}: {error}"

    def end(self) -> None:
        self.end_time = time.monotonic()
        self.end_timestamp = _utc_iso_z()

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.monotonic() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "span_id": self.span_id,
            "name": self.name,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "attributes": self.attributes,
        }
        if self.parent_span_id:
            d["parent_span_id"] = self.parent_span_id
        if self.error:
            d["error"] = self.error
        if self.events:
            d["events"] = self.events
        return d


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --- Schema validation ---


class SchemaValidator:
    """Basic JSON schema validation for LLM responses.

    Checks that responses have expected structure: required fields are present,
    types are correct, values are non-null where expected.

    This is a standard observability check -- it validates that the LLM
    returned well-formed output, NOT that the output is semantically correct
    or that state transitions are legal (those are forge-specific checks).
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        field_types: dict[str, type] | None = None,
    ):
        self.required_fields = required_fields or []
        self.field_types = field_types or {}
        self._violations: list[dict[str, Any]] = []

    def validate(self, data: Any, *, context: str = "") -> list[dict[str, Any]]:
        """Validate data against the schema.

        Args:
            data: The data to validate (expected: dict from JSON parse).
            context: Human-readable context for error messages.

        Returns:
            List of violation dicts: {field, expected, actual, context}.
        """
        violations: list[dict[str, Any]] = []

        if not isinstance(data, dict):
            violations.append({
                "field": "<root>",
                "expected": "dict",
                "actual": type(data).__name__,
                "context": context,
            })
            return violations

        for field in self.required_fields:
            if field not in data:
                violations.append({
                    "field": field,
                    "expected": "present",
                    "actual": "missing",
                    "context": context,
                })
            elif data[field] is None:
                violations.append({
                    "field": field,
                    "expected": "non-null",
                    "actual": "null",
                    "context": context,
                })

        for field, expected_type in self.field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    violations.append({
                        "field": field,
                        "expected": expected_type.__name__,
                        "actual": type(data[field]).__name__,
                        "context": context,
                    })

        self._violations.extend(violations)
        return violations

    @property
    def all_violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    def reset(self) -> None:
        self._violations.clear()


# --- Structured logging session ---


# Default schema for OpenClaw ledger events
LEDGER_EVENT_SCHEMA = SchemaValidator(
    required_fields=["ts", "kind", "task_id"],
    field_types={"ts": str, "kind": str, "task_id": str, "ok": bool, "detail": str},
)


class StructuredLoggingSession:
    """Structured logging session for agent task execution.

    Records spans for each agent turn and tool call, validates LLM responses
    against a schema, tracks timing and token counts, and captures errors.

    This is the intermediate baseline: it provides standard observability
    without forge-specific features (typed absence, provenance DAG,
    hash-verified compression).

    Usage:
        session = StructuredLoggingSession("my-session-001")

        with session.turn("turn-1") as turn:
            turn.set_attribute("prompt_tokens", 1500)
            turn.set_attribute("completion_tokens", 500)

            violations = session.validate_response(response_data)
            if violations:
                turn.add_event("schema_violation", {"count": len(violations)})

            with session.tool_call("file_read", parent=turn) as tool:
                tool.set_attribute("file", "queue_worker.py")
                # ... execute tool call ...

        report = session.get_report()
    """

    def __init__(
        self,
        session_id: str,
        *,
        schema: SchemaValidator | None = None,
        logger: logging.Logger | None = None,
    ):
        self.session_id = session_id
        self.schema = schema or SchemaValidator()
        self.logger = logger or logging.getLogger(f"structlog.{session_id}")

        self._spans: list[Span] = []
        self._errors: list[dict[str, Any]] = []
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._turn_count: int = 0
        self._tool_call_count: int = 0
        self._start_time: float = time.monotonic()
        self._start_timestamp: str = _utc_iso_z()

    # --- Turn recording ---

    class _SpanContext:
        """Context manager for span lifecycle."""

        def __init__(self, span: Span, session: StructuredLoggingSession):
            self._span = span
            self._session = session

        def __enter__(self) -> Span:
            return self._span

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            if exc_val is not None:
                self._span.set_error(exc_val)
                self._session._record_error(exc_val, context=self._span.name)
            self._span.end()

            # Extract token counts from span attributes
            prompt_tokens = self._span.attributes.get("prompt_tokens", 0)
            completion_tokens = self._span.attributes.get("completion_tokens", 0)
            if isinstance(prompt_tokens, (int, float)):
                self._session._total_prompt_tokens += int(prompt_tokens)
            if isinstance(completion_tokens, (int, float)):
                self._session._total_completion_tokens += int(completion_tokens)

            return False  # Do not suppress exceptions

    def turn(self, name: str, **attributes: Any) -> _SpanContext:
        """Create a span for an agent turn (LLM call + response processing).

        Args:
            name: Human-readable turn name.
            **attributes: Additional span attributes.

        Returns:
            Context manager yielding the Span.
        """
        self._turn_count += 1
        span = Span(
            f"turn:{name}",
            attributes={
                "session_id": self.session_id,
                "turn_number": self._turn_count,
                **attributes,
            },
        )
        self._spans.append(span)
        self.logger.info(
            "Turn started",
            extra={"turn": name, "number": self._turn_count},
        )
        return self._SpanContext(span, self)

    def tool_call(
        self, name: str, *, parent: Span | None = None, **attributes: Any
    ) -> _SpanContext:
        """Create a span for a tool call within a turn.

        Args:
            name: Tool call name (e.g., "file_read", "bash", "patch_apply").
            parent: Parent turn span (for nesting).
            **attributes: Additional span attributes.

        Returns:
            Context manager yielding the Span.
        """
        self._tool_call_count += 1
        span = Span(
            f"tool:{name}",
            parent_span_id=parent.span_id if parent else None,
            attributes={
                "session_id": self.session_id,
                "tool_call_number": self._tool_call_count,
                **attributes,
            },
        )
        self._spans.append(span)
        self.logger.debug(
            "Tool call started",
            extra={"tool": name, "number": self._tool_call_count},
        )
        return self._SpanContext(span, self)

    # --- Schema validation ---

    def validate_response(
        self, data: Any, *, context: str = ""
    ) -> list[dict[str, Any]]:
        """Validate an LLM response against the session schema.

        Args:
            data: Parsed JSON response from the LLM.
            context: Human-readable context for error messages.

        Returns:
            List of schema violations (empty = valid).
        """
        violations = self.schema.validate(data, context=context)
        if violations:
            self.logger.warning(
                "Schema violations detected",
                extra={"count": len(violations), "context": context},
            )
        return violations

    # --- Error recording ---

    def _record_error(self, error: Exception, *, context: str = "") -> None:
        error_record = {
            "timestamp": _utc_iso_z(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        }
        self._errors.append(error_record)
        # Use safe keys for logging extra (avoid reserved LogRecord keys)
        self.logger.error(
            f"Error in {context}: {type(error).__name__}: {error}",
            extra={
                "error_type": error_record["error_type"],
                "error_context": error_record["context"],
            },
        )

    def record_error(self, error: Exception, *, context: str = "") -> None:
        """Explicitly record an error (for errors not caught by span context)."""
        self._record_error(error, context=context)

    # --- Reporting ---

    def get_report(self) -> dict[str, Any]:
        """Generate a structured report of the session.

        Returns:
            Dict with session metadata, spans, schema violations, errors,
            token counts, and timing information.
        """
        end_timestamp = _utc_iso_z()
        elapsed_ms = (time.monotonic() - self._start_time) * 1000

        return {
            "session_id": self.session_id,
            "start_timestamp": self._start_timestamp,
            "end_timestamp": end_timestamp,
            "duration_ms": round(elapsed_ms, 3),
            "turn_count": self._turn_count,
            "tool_call_count": self._tool_call_count,
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "spans": [s.to_dict() for s in self._spans],
            "schema_violations": self.schema.all_violations,
            "errors": list(self._errors),
        }

    def get_spans(self) -> list[dict[str, Any]]:
        """Return all spans as dicts."""
        return [s.to_dict() for s in self._spans]

    @property
    def total_tokens(self) -> int:
        return self._total_prompt_tokens + self._total_completion_tokens

    @property
    def error_count(self) -> int:
        return len(self._errors)

    @property
    def violation_count(self) -> int:
        return len(self.schema.all_violations)


# --- Standalone functions for use by baseline_measurement.py ---


def create_session(
    session_id: str,
    *,
    required_fields: list[str] | None = None,
    field_types: dict[str, type] | None = None,
) -> StructuredLoggingSession:
    """Create a configured structured logging session.

    Args:
        session_id: Unique session identifier.
        required_fields: Fields required in LLM responses.
        field_types: Expected types for response fields.

    Returns:
        Configured StructuredLoggingSession.
    """
    schema = SchemaValidator(
        required_fields=required_fields,
        field_types=field_types,
    )
    return StructuredLoggingSession(session_id, schema=schema)


def process_ledger_with_logging(
    ledger_path: str,
    session_id: str,
) -> dict[str, Any]:
    """Process an OpenClaw ledger file using structured logging only.

    This is the structured logging analog of openclaw_adapter.process_ledger().
    It reads the ledger, validates each event against the schema, records
    spans for each event, and produces a report.

    Unlike the forge adapter, this function does NOT:
    - Assign typed absence states
    - Build provenance DAGs (no source_refs)
    - Compute hash-verified trace compression
    - Detect structural violations (illegal state transitions)

    Args:
        ledger_path: Path to queue_ledger.jsonl file.
        session_id: Unique session identifier.

    Returns:
        Structured logging report dict.
    """
    session = create_session(
        session_id,
        required_fields=["ts", "kind", "task_id"],
        field_types={"ts": str, "kind": str, "task_id": str, "ok": bool, "detail": str},
    )

    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        turn_name = f"ledger-line-{line_num}"

        with session.turn(turn_name) as turn:
            # Parse the line
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError as e:
                turn.set_error(e)
                continue

            # Validate against schema
            violations = session.validate_response(
                event, context=f"line {line_num}"
            )
            if violations:
                turn.set_attribute("schema_violations", len(violations))

            # Record event details as span attributes
            turn.set_attribute("kind", event.get("kind", ""))
            turn.set_attribute("task_id", event.get("task_id", ""))
            if "ok" in event:
                turn.set_attribute("ok", event["ok"])
            if "detail" in event:
                turn.set_attribute("detail", event["detail"])

            # Estimate token count (chars/4 heuristic)
            char_count = len(stripped)
            estimated_tokens = char_count // 4
            turn.set_attribute("prompt_tokens", estimated_tokens)
            turn.set_attribute("completion_tokens", 0)

    return session.get_report()
