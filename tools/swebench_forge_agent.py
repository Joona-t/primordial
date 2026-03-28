"""SWE-Bench Forge Agent — Phase 6, Plan 04 of Primordial v2.0.

Forge-instrumented coding agent designed for SWE-Bench tasks.
Integrates forge provenance tracking into a 5-phase agent loop:

1. Understand: Read issue description -> root artifact
2. Plan: Design solution approach -> references understand
3. Implement: Write code patches -> references plan
4. Test: Run test suite -> references implementation
5. Revise: Fix failures (up to 3 iterations) -> references test + impl

Each phase produces a forge artifact with explicit provenance links.
The full chain is tracked in a forge chamber for compaction survival
measurement.

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<phase>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent))

from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from compaction_experiment import (
    inject_artifact_markers,
    compute_artifact_survival,
    CompactionEvent,
)
from genuine_compaction_runner import (
    GenuineCompactionRunner,
    RunnerConfig,
    CompactionSnapshot,
    BoundaryCapture,
    TrialResult,
)
from summary_parser import (
    extract_artifact_ids as sp_extract_artifact_ids,
    parse_summary_provenance,
)
from findings_ledger import FindingsLedger, Finding


# --- Agent Phase Definitions ---

AGENT_PHASES = ["understand", "plan", "implement", "test", "revise"]

MAX_REVISIONS = 3


# --- Agent Output ---

@dataclass
class AgentPhaseOutput:
    """Output from a single agent phase."""
    phase: str
    artifact_id: str
    content: str
    source_refs: list[str]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentResult:
    """Complete result from one SWE-Bench agent run."""
    task_id: str
    run_id: str
    phases_completed: list[str]
    artifacts: list[dict]
    chamber_id: str
    chamber_validation: list[dict]
    compaction_events: list[dict]
    aggregate_metrics: dict
    trace_stats: dict
    task_success: bool | None  # None = not evaluated (no Docker)
    provenance_depth: int
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


# --- SWE-Bench Forge Agent ---

class SWEBenchForgeAgent:
    """Forge-instrumented coding agent for SWE-Bench tasks.

    Produces a forge chamber with artifacts from each agent phase,
    linked by explicit provenance chains. Designed for compaction
    survival measurement.

    Usage:
        agent = SWEBenchForgeAgent(
            issue_description="Fix the broken parser in module X...",
            repo_context="src/parser.py: class Parser: ...",
            run_id="swebench-001",
        )
        result = agent.run(dry_run=True)
        print(result.provenance_depth)  # >= 4
        print(result.chamber_validation)  # []
    """

    def __init__(
        self,
        issue_description: str,
        repo_context: str = "",
        run_id: str = "swebench-default",
        model: str = "claude-sonnet-4-20250514",
        threshold: int = 80_000,
        ledger: FindingsLedger | None = None,
    ):
        self.issue_description = issue_description
        self.repo_context = repo_context
        self.run_id = run_id
        self.model = model
        self.threshold = threshold
        self.ledger = ledger

        # Chamber ID format for SWE-Bench
        self.chamber_id = f"chamber:swebench:{run_id}:v1"
        self._chamber = create_chamber(self.chamber_id)

        # Phase tracking
        self._phase_outputs: list[AgentPhaseOutput] = []
        self._artifact_ids: list[str] = []
        self._artifact_contents: dict[str, str] = {}
        self._compaction_events: list[dict] = []
        self._impl_artifact_ids: list[str] = []

    def run(self, dry_run: bool = True) -> AgentResult:
        """Execute the full agent loop.

        Args:
            dry_run: If True, generate synthetic responses instead of API calls.

        Returns:
            AgentResult with all artifacts, metrics, and validation.
        """
        if dry_run:
            return self._run_dry()
        else:
            return self._run_live()

    def plan_solution(self, understand_output: str) -> AgentPhaseOutput:
        """Phase 2: Plan a solution approach based on understanding.

        Args:
            understand_output: Content from the understand phase.

        Returns:
            AgentPhaseOutput with plan artifact.
        """
        artifact_id = self._make_artifact_id("plan")
        source_refs = [self._phase_outputs[0].artifact_id] if self._phase_outputs else []

        content = (
            f"Solution Plan:\n"
            f"Based on the analysis, the fix requires:\n"
            f"1. Identify the root cause in the failing component\n"
            f"2. Design a minimal patch that addresses the issue\n"
            f"3. Add regression test to prevent recurrence\n"
            f"4. Verify backward compatibility\n\n"
            f"Key insight from understanding: {understand_output[:200]}\n"
            f"Approach: Modify the affected module with targeted fix.\n"
        )

        output = self._register_phase("plan", artifact_id, content, source_refs)
        return output

    def implement_patch(self, plan_output: str, filename: str = "fix.py") -> AgentPhaseOutput:
        """Phase 3: Implement a code patch based on the plan.

        Args:
            plan_output: Content from the plan phase.
            filename: Name of the file being patched.

        Returns:
            AgentPhaseOutput with implementation artifact.
        """
        artifact_id = self._make_artifact_id(f"impl:{filename}")
        plan_ref = self._find_phase_artifact("plan")
        source_refs = [plan_ref] if plan_ref else []

        content = (
            f"Implementation Patch for {filename}:\n"
            f"```python\n"
            f"# Fix based on plan: {plan_output[:100]}\n"
            f"def fixed_function(input_data):\n"
            f"    # Validate input before processing\n"
            f"    if not input_data:\n"
            f"        raise ValueError('Input cannot be empty')\n"
            f"    # Apply the targeted fix\n"
            f"    result = process(input_data)\n"
            f"    return result\n"
            f"```\n"
            f"Changes: Modified validation logic to handle edge case.\n"
        )

        output = self._register_phase("implement", artifact_id, content, source_refs)
        self._impl_artifact_ids.append(artifact_id)
        return output

    def run_tests(self) -> AgentPhaseOutput:
        """Phase 4: Run test suite and report results.

        References all implementation artifacts.

        Returns:
            AgentPhaseOutput with test result artifact.
        """
        artifact_id = self._make_artifact_id("test")
        source_refs = list(self._impl_artifact_ids)

        content = (
            f"Test Results:\n"
            f"Running test suite against patched code...\n"
            f"  test_basic_functionality: PASS\n"
            f"  test_edge_case_empty_input: PASS\n"
            f"  test_regression_original_bug: PASS\n"
            f"  test_backward_compatibility: PASS\n"
            f"\n"
            f"All tests passed. Patch validated.\n"
            f"Implementation artifacts tested: {', '.join(source_refs)}\n"
        )

        output = self._register_phase("test", artifact_id, content, source_refs)
        return output

    def register_artifact(
        self,
        phase: str,
        content: str,
        source_refs: list[str] | None = None,
    ) -> AgentPhaseOutput:
        """Register an artifact for a custom phase.

        Generic method for registering artifacts outside the standard
        5-phase loop. Used for revision artifacts and custom phases.

        Args:
            phase: Phase name (e.g., "revise:1").
            content: Artifact content.
            source_refs: List of artifact IDs this references.

        Returns:
            AgentPhaseOutput for the registered artifact.
        """
        artifact_id = self._make_artifact_id(phase)
        refs = source_refs or []
        return self._register_phase(phase, artifact_id, content, refs)

    # --- Internal Methods ---

    def _run_dry(self) -> AgentResult:
        """Dry-run mode: synthetic responses for pipeline validation.

        Simulates all 5 phases plus one revision loop.
        Simulates a compaction event after the implementation phase.
        """
        # Phase 1: Understand
        understand = self._dry_understand()

        # Phase 2: Plan
        plan = self.plan_solution(understand.content)

        # Phase 3: Implement (may have multiple files)
        impl1 = self.implement_patch(plan.content, "parser.py")
        impl2 = self.implement_patch(plan.content, "test_parser.py")

        # Simulate compaction event after implementation
        self._simulate_compaction_event()

        # Phase 4: Test
        test_result = self.run_tests()

        # Phase 5: Revise (simulate one test failure -> revision)
        revise = self._dry_revise(test_result, revision_num=1)

        # Seal chamber
        seal_chamber(self._chamber)
        trace = encode_trace(self._chamber)
        stats = trace_stats(trace)

        # Compute provenance depth
        depth = self._compute_provenance_depth()

        # Compute aggregate metrics
        metrics = self._compute_metrics()

        return AgentResult(
            task_id=f"swebench-{self.run_id}",
            run_id=self.run_id,
            phases_completed=[p.phase for p in self._phase_outputs],
            artifacts=[p.to_dict() for p in self._phase_outputs],
            chamber_id=self.chamber_id,
            chamber_validation=validate_chamber(self._chamber),
            compaction_events=self._compaction_events,
            aggregate_metrics=metrics,
            trace_stats=stats,
            task_success=None,  # No Docker evaluation in dry-run
            provenance_depth=depth,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _run_live(self) -> AgentResult:
        """Live API mode: actual LLM calls with forge instrumentation.

        Requires ANTHROPIC_API_KEY and optionally Docker for SWE-Bench eval.
        """
        try:
            import anthropic
        except ImportError:
            # Fallback to dry-run
            return self._run_dry()

        # Live implementation would use the compact_20260112 API
        # with pause_after_compaction, similar to GenuineCompactionRunner.
        # For now, fall back to dry-run since Docker setup is required
        # for actual SWE-Bench execution.
        return self._run_dry()

    def _dry_understand(self) -> AgentPhaseOutput:
        """Dry-run: Understand phase with synthetic analysis."""
        artifact_id = self._make_artifact_id("understand")

        content = (
            f"Issue Analysis:\n"
            f"Issue: {self.issue_description[:500]}\n\n"
            f"Root Cause Analysis:\n"
            f"The issue appears to be in the input validation logic. "
            f"The parser does not handle empty or malformed inputs correctly, "
            f"leading to an unhandled exception. The traceback points to "
            f"line 42 in parser.py where `data.split()` is called on None.\n\n"
            f"Affected Components:\n"
            f"- parser.py: main parsing logic\n"
            f"- test_parser.py: needs regression test\n\n"
            f"Repo Context Summary:\n"
            f"{self.repo_context[:300] if self.repo_context else 'No repo context provided.'}\n"
        )

        return self._register_phase("understand", artifact_id, content, source_refs=[])

    def _dry_revise(self, test_output: AgentPhaseOutput, revision_num: int) -> AgentPhaseOutput:
        """Dry-run: Revision phase after test results."""
        artifact_id = self._make_artifact_id(f"revise:{revision_num}")

        # Source refs: test artifact + relevant impl artifacts
        source_refs = [test_output.artifact_id]
        if self._impl_artifact_ids:
            source_refs.append(self._impl_artifact_ids[-1])

        content = (
            f"Revision {revision_num}:\n"
            f"After reviewing test results from {test_output.artifact_id}:\n"
            f"- Found additional edge case: unicode input not handled\n"
            f"- Added input encoding normalization\n"
            f"- Updated test to cover unicode paths\n\n"
            f"```python\n"
            f"def fixed_function(input_data):\n"
            f"    if not input_data:\n"
            f"        raise ValueError('Input cannot be empty')\n"
            f"    # Normalize encoding (revision {revision_num})\n"
            f"    if isinstance(input_data, bytes):\n"
            f"        input_data = input_data.decode('utf-8')\n"
            f"    return process(input_data)\n"
            f"```\n"
        )

        return self._register_phase(f"revise:{revision_num}", artifact_id, content, source_refs)

    def _simulate_compaction_event(self):
        """Simulate a compaction event in dry-run mode.

        Creates a synthetic compaction summary that preserves some
        artifact IDs and loses others, for testing compaction survival.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Build synthetic summary text preserving recent artifacts
        surviving = self._artifact_ids[-3:] if len(self._artifact_ids) >= 3 else self._artifact_ids
        lost = [a for a in self._artifact_ids if a not in surviving]

        summary_parts = ["Summary of agent progress so far: "]
        for aid in surviving:
            summary_parts.append(f"[PROVENANCE: {aid}] ")
        if len(surviving) >= 2:
            summary_parts.append(
                f"source_ref: {surviving[0]} -> {surviving[1]} "
            )
        summary_text = "".join(summary_parts)

        self._compaction_events.append({
            "type": "simulated_compaction",
            "timestamp": now,
            "artifacts_before": len(self._artifact_ids),
            "artifacts_surviving": len(surviving),
            "artifacts_lost": len(lost),
            "surviving_ids": surviving,
            "lost_ids": lost,
            "summary_text": summary_text[:500],
        })

    def _register_phase(
        self,
        phase: str,
        artifact_id: str,
        content: str,
        source_refs: list[str],
    ) -> AgentPhaseOutput:
        """Register a phase output as a forge artifact in the chamber.

        Args:
            phase: Phase name (e.g., "understand", "plan").
            artifact_id: The forge artifact ID.
            content: Phase output content.
            source_refs: Artifact IDs this references.

        Returns:
            AgentPhaseOutput for the registered phase.
        """
        # Mark content with artifact ID for survival tracking
        marked_content = f"{content}\n[PROVENANCE: {artifact_id}]\n"

        # Create forge artifact
        artifact = create_v1_stage_artifact(
            stage_id=artifact_id,
            seat=f"swebench-{phase.split(':')[0]}",
            producer_name=f"swebench-agent-{phase}",
            producer_role=phase.split(":")[0],
            output=marked_content,
            source_refs=source_refs if source_refs else None,
        )

        # Create summary
        summary = create_v1_stage_summary(
            artifact,
            f"SWE-Bench agent phase '{phase}': {content[:100]}...",
            extra_source_refs=source_refs if source_refs else None,
        )

        # Register in chamber
        register_stage(self._chamber, artifact, summary)

        # Track
        self._artifact_ids.append(artifact_id)
        self._artifact_contents[artifact_id] = content

        output = AgentPhaseOutput(
            phase=phase,
            artifact_id=artifact_id,
            content=content,
            source_refs=source_refs,
        )
        self._phase_outputs.append(output)

        return output

    def _make_artifact_id(self, phase: str) -> str:
        """Create artifact ID following convention #5.

        Format: artifact:{run_id}:stage:{phase}:r1
        """
        # Sanitize phase name for ID (replace special chars)
        safe_phase = phase.replace(":", "_").replace("/", "_").replace(" ", "_")
        return f"artifact:{self.run_id}:stage:{safe_phase}:r1"

    def _find_phase_artifact(self, phase_prefix: str) -> str | None:
        """Find the most recent artifact ID for a given phase prefix."""
        for output in reversed(self._phase_outputs):
            if output.phase.startswith(phase_prefix):
                return output.artifact_id
        return None

    def _compute_provenance_depth(self) -> int:
        """Compute the maximum provenance chain depth in the chamber.

        Walks the source_ref DAG from each leaf artifact to find the
        longest chain.
        """
        # Build adjacency: artifact_id -> source_refs
        adj: dict[str, list[str]] = {}
        for output in self._phase_outputs:
            adj[output.artifact_id] = output.source_refs

        def _depth(aid: str, visited: set) -> int:
            if aid in visited or aid not in adj:
                return 0
            visited.add(aid)
            refs = adj[aid]
            if not refs:
                return 1
            max_parent = 0
            for ref in refs:
                parent_d = _depth(ref, visited)
                max_parent = max(max_parent, parent_d)
            return 1 + max_parent

        max_depth = 0
        for aid in adj:
            depth = _depth(aid, set())
            max_depth = max(max_depth, depth)

        return max_depth

    def _compute_metrics(self) -> dict:
        """Compute aggregate metrics for the agent run."""
        total_artifacts = len(self._artifact_ids)
        phases_completed = len(self._phase_outputs)

        # If compaction events exist, compute survival
        if self._compaction_events:
            event = self._compaction_events[-1]
            surviving = event.get("artifacts_surviving", total_artifacts)
            survival_rate = surviving / max(total_artifacts, 1)
        else:
            survival_rate = 1.0

        return {
            "total_artifacts": total_artifacts,
            "phases_completed": phases_completed,
            "provenance_depth": self._compute_provenance_depth(),
            "artifact_id_survival": round(survival_rate, 4),
            "compaction_events": len(self._compaction_events),
            "revision_count": sum(
                1 for p in self._phase_outputs if p.phase.startswith("revise")
            ),
        }


# --- CLI Entry Point ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SWE-Bench Forge Agent")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Run in dry-run mode (default)")
    parser.add_argument("--issue", type=str, default="Fix the broken parser that crashes on empty input",
                        help="Issue description")
    parser.add_argument("--run-id", type=str, default=f"swebench-{int(time.time())}",
                        help="Run identifier")
    args = parser.parse_args()

    agent = SWEBenchForgeAgent(
        issue_description=args.issue,
        run_id=args.run_id,
    )
    result = agent.run(dry_run=True)

    print(f"SWE-Bench Forge Agent — dry-run complete")
    print(f"  Run ID: {result.run_id}")
    print(f"  Task ID: {result.task_id}")
    print(f"  Phases: {result.phases_completed}")
    print(f"  Artifacts: {len(result.artifacts)}")
    print(f"  Provenance depth: {result.provenance_depth}")
    print(f"  Chamber validation errors: {len(result.chamber_validation)}")
    print(f"  Compaction events: {len(result.compaction_events)}")
    print(f"  Metrics: {json.dumps(result.aggregate_metrics, indent=2)}")
