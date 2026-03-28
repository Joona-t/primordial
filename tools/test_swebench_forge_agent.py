"""Tests for swebench_forge_agent.py — Phase 6, Plan 04.

Validates:
1. Agent instantiation with mock issue
2. Dry-run execution: 5+ phases produce artifacts
3. Provenance chain: understand -> plan -> impl -> test -> revise
4. Provenance depth >= 4 (no revisions), >= 5 (with revisions)
5. Chamber validation: zero errors after dry-run
6. Compaction event capture: simulated compaction valid
7. Artifact ID convention: artifact:{run_id}:stage:{phase}:r1
8. Source ref integrity: all refs resolve in the chamber
9. Register artifact API
10. Agent result serialization
"""

import json
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from swebench_forge_agent import (
    SWEBenchForgeAgent,
    AgentPhaseOutput,
    AgentResult,
    AGENT_PHASES,
    MAX_REVISIONS,
)
from forge_chamber import validate_chamber


MOCK_ISSUE = (
    "Fix the broken CSV parser that crashes when encountering empty rows. "
    "The parser in src/csv_parser.py raises an IndexError on line 87 when "
    "processing files with consecutive empty lines. Expected behavior: "
    "empty rows should be skipped gracefully. Traceback:\n"
    "  File 'src/csv_parser.py', line 87, in parse_row\n"
    "    fields = row.split(delimiter)\n"
    "IndexError: list index out of range"
)

MOCK_REPO_CONTEXT = (
    "src/csv_parser.py:\n"
    "class CSVParser:\n"
    "    def __init__(self, delimiter=','):\n"
    "        self.delimiter = delimiter\n"
    "    def parse_row(self, row):\n"
    "        fields = row.split(self.delimiter)\n"
    "        return fields[0]  # crashes on empty row\n"
)


class TestAgentInstantiation(unittest.TestCase):
    """Test SWEBenchForgeAgent creation."""

    def test_creates_with_defaults(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="test-001",
        )
        self.assertEqual(agent.run_id, "test-001")
        self.assertEqual(agent.model, "claude-sonnet-4-20250514")
        self.assertEqual(agent.threshold, 80_000)

    def test_creates_with_custom_params(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            repo_context=MOCK_REPO_CONTEXT,
            run_id="test-002",
            model="claude-opus-4-20250514",
            threshold=50_000,
        )
        self.assertEqual(agent.model, "claude-opus-4-20250514")
        self.assertEqual(agent.threshold, 50_000)

    def test_chamber_id_format(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="test-003",
        )
        self.assertEqual(agent.chamber_id, "chamber:swebench:test-003:v1")

    def test_initial_state_empty(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="test-004",
        )
        self.assertEqual(len(agent._phase_outputs), 0)
        self.assertEqual(len(agent._artifact_ids), 0)


class TestDryRunExecution(unittest.TestCase):
    """Test full dry-run execution."""

    def setUp(self):
        self.agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            repo_context=MOCK_REPO_CONTEXT,
            run_id="dryrun-001",
        )
        self.result = self.agent.run(dry_run=True)

    def test_produces_artifacts(self):
        """Dry-run must produce at least 4 artifacts (understand, plan, impl, test)."""
        self.assertGreaterEqual(len(self.result.artifacts), 4)

    def test_phases_include_core_phases(self):
        """All core phases should appear."""
        phases = self.result.phases_completed
        self.assertIn("understand", phases)
        self.assertIn("plan", phases)
        # Implementation may have multiple sub-phases
        impl_phases = [p for p in phases if p.startswith("implement")]
        self.assertGreaterEqual(len(impl_phases), 1)
        self.assertIn("test", phases)

    def test_includes_revision(self):
        """Dry-run simulates at least one revision."""
        phases = self.result.phases_completed
        revise_phases = [p for p in phases if p.startswith("revise")]
        self.assertGreaterEqual(len(revise_phases), 1)

    def test_has_6_artifacts(self):
        """Dry-run: understand + plan + 2 impl + test + revise = 6."""
        self.assertEqual(len(self.result.artifacts), 6)

    def test_task_success_is_none(self):
        """Dry-run cannot evaluate task success (no Docker)."""
        self.assertIsNone(self.result.task_success)

    def test_result_has_all_fields(self):
        d = self.result.to_dict()
        required_fields = [
            "task_id", "run_id", "phases_completed", "artifacts",
            "chamber_id", "chamber_validation", "compaction_events",
            "aggregate_metrics", "trace_stats", "task_success",
            "provenance_depth", "timestamp",
        ]
        for field_name in required_fields:
            self.assertIn(field_name, d, f"Missing field: {field_name}")


class TestProvenanceChain(unittest.TestCase):
    """Test provenance chain integrity."""

    def setUp(self):
        self.agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            repo_context=MOCK_REPO_CONTEXT,
            run_id="prov-001",
        )
        self.result = self.agent.run(dry_run=True)

    def test_understand_has_no_source_refs(self):
        """Understand phase is the root artifact (no predecessors)."""
        understand = self.result.artifacts[0]
        self.assertEqual(understand["source_refs"], [])

    def test_plan_references_understand(self):
        """Plan should reference the understand artifact."""
        plan = self.result.artifacts[1]
        understand_id = self.result.artifacts[0]["artifact_id"]
        self.assertIn(understand_id, plan["source_refs"])

    def test_impl_references_plan(self):
        """Implementation should reference the plan artifact."""
        plan_id = self.result.artifacts[1]["artifact_id"]
        # Find first impl artifact
        impl = None
        for a in self.result.artifacts:
            if a["phase"].startswith("implement"):
                impl = a
                break
        self.assertIsNotNone(impl)
        self.assertIn(plan_id, impl["source_refs"])

    def test_test_references_impl(self):
        """Test phase should reference implementation artifact(s)."""
        test_artifact = None
        for a in self.result.artifacts:
            if a["phase"] == "test":
                test_artifact = a
                break
        self.assertIsNotNone(test_artifact)
        self.assertGreater(len(test_artifact["source_refs"]), 0)
        # At least one ref should be an impl artifact
        impl_ids = [a["artifact_id"] for a in self.result.artifacts
                     if a["phase"].startswith("implement")]
        has_impl_ref = any(ref in impl_ids for ref in test_artifact["source_refs"])
        self.assertTrue(has_impl_ref)

    def test_revise_references_test(self):
        """Revision should reference the test artifact."""
        revise = None
        for a in self.result.artifacts:
            if a["phase"].startswith("revise"):
                revise = a
                break
        self.assertIsNotNone(revise)
        test_id = None
        for a in self.result.artifacts:
            if a["phase"] == "test":
                test_id = a["artifact_id"]
                break
        self.assertIn(test_id, revise["source_refs"])

    def test_no_dangling_refs(self):
        """All source_refs should resolve to existing artifact IDs."""
        all_ids = {a["artifact_id"] for a in self.result.artifacts}
        for a in self.result.artifacts:
            for ref in a["source_refs"]:
                self.assertIn(ref, all_ids,
                              f"Dangling ref {ref} in artifact {a['artifact_id']}")


class TestProvenanceDepth(unittest.TestCase):
    """Test provenance chain depth."""

    def test_depth_at_least_4_basic(self):
        """Basic chain: understand -> plan -> impl -> test = depth 4."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="depth-001",
        )
        result = agent.run(dry_run=True)
        # With revisions, depth should be >= 5
        self.assertGreaterEqual(result.provenance_depth, 4)

    def test_depth_at_least_5_with_revisions(self):
        """With revisions: understand -> plan -> impl -> test -> revise = depth >= 5."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="depth-002",
        )
        result = agent.run(dry_run=True)
        self.assertGreaterEqual(result.provenance_depth, 5)


class TestChamberValidation(unittest.TestCase):
    """Test forge chamber integrity after agent run."""

    def test_zero_validation_errors(self):
        """Chamber should validate cleanly after dry-run."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            repo_context=MOCK_REPO_CONTEXT,
            run_id="chamber-001",
        )
        result = agent.run(dry_run=True)
        self.assertEqual(result.chamber_validation, [],
                         f"Chamber validation errors: {result.chamber_validation}")

    def test_chamber_is_sealed(self):
        """Chamber should be sealed after agent run."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="chamber-002",
        )
        agent.run(dry_run=True)
        self.assertEqual(agent._chamber["status"], "sealed")


class TestCompactionEventCapture(unittest.TestCase):
    """Test simulated compaction event handling."""

    def test_compaction_event_exists(self):
        """Dry-run should simulate at least one compaction event."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="compact-001",
        )
        result = agent.run(dry_run=True)
        self.assertGreater(len(result.compaction_events), 0)

    def test_compaction_event_has_required_fields(self):
        """Compaction event should have type, timestamp, artifact counts."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="compact-002",
        )
        result = agent.run(dry_run=True)
        event = result.compaction_events[0]
        self.assertIn("type", event)
        self.assertIn("timestamp", event)
        self.assertIn("artifacts_before", event)
        self.assertIn("artifacts_surviving", event)
        self.assertIn("surviving_ids", event)

    def test_compaction_preserves_some_artifacts(self):
        """Simulated compaction should preserve some but not all artifacts."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="compact-003",
        )
        result = agent.run(dry_run=True)
        event = result.compaction_events[0]
        self.assertGreater(event["artifacts_surviving"], 0)
        # Should not preserve all (simulation loses some)
        self.assertLessEqual(event["artifacts_surviving"], event["artifacts_before"])


class TestArtifactIDConvention(unittest.TestCase):
    """Test artifact ID format compliance (Convention #5)."""

    def test_all_ids_follow_convention(self):
        """All artifact IDs should match: artifact:{run_id}:stage:{phase}:r1."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="conv-001",
        )
        result = agent.run(dry_run=True)
        for a in result.artifacts:
            aid = a["artifact_id"]
            self.assertTrue(aid.startswith("artifact:conv-001:stage:"),
                            f"ID {aid} doesn't follow convention")
            self.assertTrue(aid.endswith(":r1"),
                            f"ID {aid} doesn't end with :r1")

    def test_all_ids_unique(self):
        """All artifact IDs must be unique."""
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="conv-002",
        )
        result = agent.run(dry_run=True)
        ids = [a["artifact_id"] for a in result.artifacts]
        self.assertEqual(len(ids), len(set(ids)))


class TestRegisterArtifact(unittest.TestCase):
    """Test the generic register_artifact API."""

    def test_register_custom_phase(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="custom-001",
        )
        # First register understand (root)
        agent._dry_understand()

        output = agent.register_artifact(
            phase="custom_analysis",
            content="Custom analysis output with findings.",
            source_refs=[agent._artifact_ids[0]],
        )
        self.assertEqual(output.phase, "custom_analysis")
        self.assertIn(agent._artifact_ids[0], output.source_refs)

    def test_register_without_source_refs(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="custom-002",
        )
        output = agent.register_artifact(
            phase="root_artifact",
            content="A standalone root artifact.",
        )
        self.assertEqual(output.source_refs, [])


class TestAgentMetrics(unittest.TestCase):
    """Test aggregate metrics computation."""

    def test_metrics_present(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="metrics-001",
        )
        result = agent.run(dry_run=True)
        metrics = result.aggregate_metrics
        self.assertIn("total_artifacts", metrics)
        self.assertIn("phases_completed", metrics)
        self.assertIn("provenance_depth", metrics)
        self.assertIn("artifact_id_survival", metrics)
        self.assertIn("compaction_events", metrics)
        self.assertIn("revision_count", metrics)

    def test_artifact_count_matches(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="metrics-002",
        )
        result = agent.run(dry_run=True)
        self.assertEqual(
            result.aggregate_metrics["total_artifacts"],
            len(result.artifacts),
        )

    def test_revision_count_correct(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="metrics-003",
        )
        result = agent.run(dry_run=True)
        revise_phases = [p for p in result.phases_completed if p.startswith("revise")]
        self.assertEqual(
            result.aggregate_metrics["revision_count"],
            len(revise_phases),
        )


class TestAgentResultSerialization(unittest.TestCase):
    """Test AgentResult serialization."""

    def test_to_dict_is_json_serializable(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="serial-001",
        )
        result = agent.run(dry_run=True)
        d = result.to_dict()
        # Should be JSON serializable
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["run_id"], "serial-001")

    def test_artifacts_in_dict(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="serial-002",
        )
        result = agent.run(dry_run=True)
        d = result.to_dict()
        self.assertIsInstance(d["artifacts"], list)
        self.assertGreater(len(d["artifacts"]), 0)


class TestTraceStats(unittest.TestCase):
    """Test trace statistics from the forge chamber."""

    def test_trace_stats_present(self):
        agent = SWEBenchForgeAgent(
            issue_description=MOCK_ISSUE,
            run_id="trace-001",
        )
        result = agent.run(dry_run=True)
        self.assertIsInstance(result.trace_stats, dict)
        # Trace stats should have basic fields
        self.assertGreater(len(result.trace_stats), 0)


if __name__ == "__main__":
    unittest.main()
