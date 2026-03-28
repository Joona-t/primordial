"""Tests for genuine_compaction_runner.py — Phase 6, Plan 02.

Validates:
1. Dry-run mode end-to-end (no API calls)
2. Metric computation on known inputs
3. JSONL schema validation
4. Boundary capture logic
5. Retry logic (mock API errors)
6. Integration with summary_parser and embedding_similarity
7. RunnerConfig defaults and overrides
8. TrialResult serialization
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent))

from genuine_compaction_runner import (
    RunnerConfig,
    CompactionSnapshot,
    BoundaryCapture,
    TrialResult,
    GenuineCompactionRunner,
    DEFAULT_PROVENANCE_INSTRUCTIONS,
)
from compaction_experiment import inject_artifact_markers, compute_artifact_survival
from findings_ledger import FindingsLedger


# --- Minimal TaskTemplate mock for testing ---

class MockTaskTemplate:
    """Minimal task template for dry-run tests."""

    def __init__(self, category="coding", track="A", num_iterations=10):
        self.category = category
        self.track = track
        self._num_iterations = num_iterations

    def generate_iteration(self, iteration: int) -> str:
        return (
            f"Step {iteration + 1}: Implement component {iteration + 1} for the "
            f"authentication system. Include data models, API handlers, middleware, "
            f"and comprehensive tests. Use dependency injection for service wiring."
        )

    def expected_tokens_per_iteration(self) -> int:
        return 500


class TestRunnerConfig(unittest.TestCase):
    """Test RunnerConfig dataclass."""

    def test_default_values(self):
        config = RunnerConfig()
        self.assertEqual(config.model, "claude-sonnet-4-20250514")
        self.assertEqual(config.threshold, 80000)
        self.assertTrue(config.pause_after_compaction)
        self.assertEqual(config.max_retries, 3)
        self.assertFalse(config.dry_run)
        self.assertEqual(config.num_iterations, 20)

    def test_custom_values(self):
        config = RunnerConfig(
            model="claude-opus-4-20250514",
            threshold=50000,
            dry_run=True,
            max_retries=5,
            num_iterations=10,
        )
        self.assertEqual(config.model, "claude-opus-4-20250514")
        self.assertEqual(config.threshold, 50000)
        self.assertTrue(config.dry_run)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.num_iterations, 10)

    def test_provenance_aware_default_none(self):
        config = RunnerConfig()
        self.assertIsNone(config.provenance_aware_instructions)

    def test_provenance_aware_custom(self):
        config = RunnerConfig(
            provenance_aware_instructions=DEFAULT_PROVENANCE_INSTRUCTIONS
        )
        self.assertIn("artifact", config.provenance_aware_instructions)


class TestCompactionSnapshot(unittest.TestCase):
    """Test CompactionSnapshot serialization."""

    def test_to_dict(self):
        snapshot = CompactionSnapshot(
            artifact_ids=["artifact:r1:iter:0:r1"],
            ref_graph=[("artifact:r1:iter:0:r1", None)],
            chamber_hash="abc123",
            timestamp="2026-03-28T00:00:00Z",
        )
        d = snapshot.to_dict()
        self.assertEqual(d["artifact_ids"], ["artifact:r1:iter:0:r1"])
        self.assertEqual(d["chamber_hash"], "abc123")
        self.assertIsInstance(d["ref_graph"], list)


class TestTrialResult(unittest.TestCase):
    """Test TrialResult serialization."""

    def test_to_dict_roundtrip(self):
        result = TrialResult(
            trial_id="test-001",
            track="A",
            task_category="coding",
            model="claude-sonnet-4-20250514",
            mode="dry-run",
            provenance_aware=False,
            threshold=80000,
            num_iterations=10,
            compaction_events=[],
            aggregate_metrics={"structural_reachability": 0.5},
            trace_stats={},
            chamber_validation=[],
            timestamp="2026-03-28T00:00:00Z",
        )
        d = result.to_dict()
        self.assertEqual(d["trial_id"], "test-001")
        self.assertEqual(d["mode"], "dry-run")
        self.assertIn("structural_reachability", d["aggregate_metrics"])

    def test_json_serializable(self):
        result = TrialResult(
            trial_id="test-002",
            track="A",
            task_category="debugging",
            model="claude-sonnet-4-20250514",
            mode="dry-run",
            provenance_aware=True,
            threshold=50000,
            num_iterations=5,
            compaction_events=[],
            aggregate_metrics={},
            trace_stats={},
            chamber_validation=[],
            timestamp="2026-03-28T00:00:00Z",
        )
        # Must serialize to JSON without error
        serialized = json.dumps(result.to_dict(), default=str)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["trial_id"], "test-002")


class TestDryRunEndToEnd(unittest.TestCase):
    """End-to-end dry-run tests (no API calls)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)
        self.config = RunnerConfig(
            dry_run=True,
            num_iterations=10,
            output_dir=os.path.join(self.tmpdir, "output"),
        )
        self.runner = GenuineCompactionRunner(self.config, self.ledger)
        self.template = MockTaskTemplate(num_iterations=10)

    def test_dry_run_completes(self):
        result = self.runner.run_trial(self.template)
        self.assertIsInstance(result, TrialResult)
        self.assertEqual(result.mode, "dry-run")
        self.assertEqual(result.num_iterations, 10)

    def test_dry_run_produces_compaction_event(self):
        result = self.runner.run_trial(self.template)
        self.assertGreater(len(result.compaction_events), 0)

    def test_dry_run_metrics_in_valid_ranges(self):
        result = self.runner.run_trial(self.template)
        metrics = result.aggregate_metrics
        # structural_reachability in [0, 1]
        self.assertGreaterEqual(metrics["structural_reachability"], 0.0)
        self.assertLessEqual(metrics["structural_reachability"], 1.0)
        # artifact_id_survival in [0, 1]
        self.assertGreaterEqual(metrics["artifact_id_survival"], 0.0)
        self.assertLessEqual(metrics["artifact_id_survival"], 1.0)
        # compression_ratio > 0
        self.assertGreater(metrics["compression_ratio"], 0)
        # degraded_fraction in [0, 1]
        self.assertGreaterEqual(metrics["degraded_fraction"], 0.0)
        self.assertLessEqual(metrics["degraded_fraction"], 1.0)

    def test_dry_run_boundary_has_pre_post_snapshots(self):
        result = self.runner.run_trial(self.template)
        self.assertGreater(len(result.boundaries), 0)
        boundary = result.boundaries[0]
        self.assertIn("pre_snapshot", boundary)
        self.assertIn("post_snapshot", boundary)
        self.assertIn("surviving_ids", boundary)
        self.assertIn("lost_ids", boundary)
        self.assertIn("tier_classification", boundary)

    def test_dry_run_boundary_snapshots_have_correct_types(self):
        result = self.runner.run_trial(self.template)
        boundary = result.boundaries[0]
        pre = boundary["pre_snapshot"]
        post = boundary["post_snapshot"]
        self.assertIsInstance(pre["artifact_ids"], list)
        self.assertIsInstance(pre["ref_graph"], list)
        self.assertIsInstance(pre["chamber_hash"], str)
        self.assertIsInstance(post["artifact_ids"], list)

    def test_dry_run_logs_to_findings_ledger(self):
        self.runner.run_trial(self.template)
        findings = self.ledger.query(tag="boundary-capture")
        self.assertGreater(len(findings), 0)

    def test_dry_run_track_and_category(self):
        result = self.runner.run_trial(self.template)
        self.assertEqual(result.track, "A")
        self.assertEqual(result.task_category, "coding")


class TestJSONLLogging(unittest.TestCase):
    """Test JSONL log file creation and schema."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)
        self.config = RunnerConfig(
            dry_run=True,
            num_iterations=5,
            output_dir=os.path.join(self.tmpdir, "output"),
        )
        self.runner = GenuineCompactionRunner(self.config, self.ledger)
        self.template = MockTaskTemplate(num_iterations=5)

    def test_log_creates_file(self):
        result = self.runner.run_trial(self.template)
        log_path = self.runner.log_results(result)
        self.assertTrue(log_path.exists())

    def test_log_valid_jsonl(self):
        result = self.runner.run_trial(self.template)
        log_path = self.runner.log_results(result)
        with open(log_path) as f:
            for line in f:
                parsed = json.loads(line)
                self.assertIsInstance(parsed, dict)

    def test_log_schema_has_required_fields(self):
        result = self.runner.run_trial(self.template)
        log_path = self.runner.log_results(result)
        with open(log_path) as f:
            for line in f:
                parsed = json.loads(line)
                required = [
                    "trial_id", "track", "task_category", "model",
                    "mode", "provenance_aware", "threshold",
                    "compaction_events", "aggregate_metrics",
                    "trace_stats", "timestamp",
                ]
                for key in required:
                    self.assertIn(key, parsed, f"Missing required field: {key}")

    def test_log_aggregate_metrics_fields(self):
        result = self.runner.run_trial(self.template)
        log_path = self.runner.log_results(result)
        with open(log_path) as f:
            for line in f:
                parsed = json.loads(line)
                metrics = parsed["aggregate_metrics"]
                for metric_key in [
                    "structural_reachability",
                    "artifact_id_survival",
                    "compression_ratio",
                    "degraded_fraction",
                ]:
                    self.assertIn(metric_key, metrics,
                                  f"Missing metric: {metric_key}")


class TestMetricComputation(unittest.TestCase):
    """Test metric computation on known inputs."""

    def test_full_survival_gives_1_0(self):
        """When all artifact IDs survive, structural_reachability = 1.0."""
        tmpdir = tempfile.mkdtemp()
        config = RunnerConfig(dry_run=True, num_iterations=5,
                              output_dir=os.path.join(tmpdir, "out"))
        runner = GenuineCompactionRunner(config)

        # Manually set up state as if all artifacts survived
        runner._artifact_ids = ["artifact:r1:iter:0:r1", "artifact:r1:iter:1:r1"]
        runner._iteration_outputs = {
            "artifact:r1:iter:0:r1": "content A",
            "artifact:r1:iter:1:r1": "content B",
        }

        # Summary text containing all artifact IDs
        summary = (
            "Summary: artifact:r1:iter:0:r1 was about content A. "
            "artifact:r1:iter:1:r1 was about content B."
        )
        survival = compute_artifact_survival(runner._artifact_ids, summary)
        self.assertEqual(survival["survival_rate"], 1.0)

    def test_partial_survival_correct_ratio(self):
        """When 1 of 2 survives, rate = 0.5."""
        ids = ["artifact:r1:iter:0:r1", "artifact:r1:iter:1:r1"]
        summary = "Only artifact:r1:iter:0:r1 survived"
        survival = compute_artifact_survival(ids, summary)
        self.assertEqual(survival["survival_rate"], 0.5)

    def test_zero_survival(self):
        """When no IDs survive, rate = 0.0."""
        ids = ["artifact:r1:iter:0:r1"]
        summary = "Nothing survived"
        survival = compute_artifact_survival(ids, summary)
        self.assertEqual(survival["survival_rate"], 0.0)


class TestBoundaryCapture(unittest.TestCase):
    """Test boundary capture logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = RunnerConfig(
            dry_run=True, num_iterations=5,
            output_dir=os.path.join(self.tmpdir, "out"),
        )
        self.runner = GenuineCompactionRunner(self.config)

    def test_capture_produces_boundary(self):
        """capture_boundary returns a BoundaryCapture."""
        # Register some artifacts first
        from forge_chamber import create_chamber
        self.runner._chamber = create_chamber("chamber:test:boundary:v1")
        self.runner._artifact_ids = [
            "artifact:test:iter:0:r1",
            "artifact:test:iter:1:r1",
        ]
        self.runner._iteration_outputs = {
            "artifact:test:iter:0:r1": "Original content zero.",
            "artifact:test:iter:1:r1": "Original content one.",
        }

        # Note: only artifact:test:iter:1:r1 appears as a standalone ID
        # in the summary text. artifact:test:iter:0:r1 is NOT mentioned
        # outside the source_ref line -- but the parser finds it there too.
        # Use a summary that truly loses one ID.
        compaction_block = {
            "type": "compaction",
            "text": "Summary: artifact:test:iter:1:r1 was preserved. "
                    "The earlier work on data models was condensed.",
        }

        boundary = self.runner.capture_boundary(
            messages=[],
            compaction_block=compaction_block,
            chamber=self.runner._chamber,
        )

        self.assertIsInstance(boundary, BoundaryCapture)
        self.assertEqual(len(boundary.surviving_ids), 1)
        self.assertIn("artifact:test:iter:1:r1", boundary.surviving_ids)
        self.assertIn("artifact:test:iter:0:r1", boundary.lost_ids)

    def test_capture_tier_classification(self):
        """capture_boundary classifies each artifact into tiers."""
        from forge_chamber import create_chamber
        self.runner._chamber = create_chamber("chamber:test:tiers:v1")
        self.runner._artifact_ids = [
            "artifact:test:iter:0:r1",
            "artifact:test:iter:1:r1",
        ]
        self.runner._iteration_outputs = {
            "artifact:test:iter:0:r1": "Design the user authentication data model.",
            "artifact:test:iter:1:r1": "Write unit tests for auth middleware.",
        }

        # Only artifact:test:iter:1:r1 in summary
        compaction_block = {
            "type": "compaction",
            "text": "Summary: artifact:test:iter:1:r1 — unit tests for auth.",
        }

        boundary = self.runner.capture_boundary(
            messages=[],
            compaction_block=compaction_block,
            chamber=self.runner._chamber,
        )

        tiers = boundary.tier_classification
        self.assertEqual(tiers["artifact:test:iter:0:r1"], "broken")
        # iter:1 should be degraded or resolved (depends on similarity)
        self.assertIn(tiers["artifact:test:iter:1:r1"], ["resolved", "degraded"])

    def test_capture_provenance_metadata(self):
        """capture_boundary extracts provenance metadata via summary_parser."""
        from forge_chamber import create_chamber
        self.runner._chamber = create_chamber("chamber:test:prov:v1")
        self.runner._artifact_ids = ["artifact:test:iter:0:r1"]
        self.runner._iteration_outputs = {
            "artifact:test:iter:0:r1": "Some content.",
        }

        compaction_block = {
            "type": "compaction",
            "text": "[PROVENANCE: artifact:test:iter:0:r1] Summary text.",
        }

        boundary = self.runner.capture_boundary(
            messages=[],
            compaction_block=compaction_block,
            chamber=self.runner._chamber,
        )

        self.assertIn("provenance_density", boundary.provenance_metadata)
        self.assertIn("artifact_ids", boundary.provenance_metadata)
        self.assertIn("artifact:test:iter:0:r1",
                       boundary.provenance_metadata["artifact_ids"])


class TestRetryLogic(unittest.TestCase):
    """Test API retry logic with mock errors."""

    def test_retry_exhaustion_returns_none(self):
        """After max_retries, _api_call_with_retry returns None."""
        tmpdir = tempfile.mkdtemp()
        config = RunnerConfig(
            dry_run=False, max_retries=2,
            retry_base_delay=0.01,  # fast for testing
            output_dir=os.path.join(tmpdir, "out"),
        )
        ledger = FindingsLedger(data_dir=tmpdir)
        runner = GenuineCompactionRunner(config, ledger)

        # Mock client that always raises
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")

        result = runner._api_call_with_retry(
            mock_client, "system", [{"role": "user", "content": "test"}],
            "trial-1", 0
        )
        self.assertIsNone(result)
        # Should have been called max_retries times
        self.assertEqual(mock_client.messages.create.call_count, 2)

    def test_retry_success_on_second_attempt(self):
        """If first call fails and second succeeds, return the response."""
        tmpdir = tempfile.mkdtemp()
        config = RunnerConfig(
            dry_run=False, max_retries=3,
            retry_base_delay=0.01,
            output_dir=os.path.join(tmpdir, "out"),
        )
        runner = GenuineCompactionRunner(config)

        mock_response = MagicMock()
        mock_response.content = []
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            RuntimeError("transient error"),
            mock_response,
        ]

        result = runner._api_call_with_retry(
            mock_client, "system", [{"role": "user", "content": "test"}],
            "trial-2", 0
        )
        self.assertIsNotNone(result)
        self.assertEqual(mock_client.messages.create.call_count, 2)

    def test_retry_logs_to_ledger(self):
        """Retry attempts are logged to the findings ledger."""
        tmpdir = tempfile.mkdtemp()
        ledger = FindingsLedger(data_dir=tmpdir)
        config = RunnerConfig(
            dry_run=False, max_retries=2,
            retry_base_delay=0.01,
            output_dir=os.path.join(tmpdir, "out"),
        )
        runner = GenuineCompactionRunner(config, ledger)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")

        runner._api_call_with_retry(
            mock_client, "system", [{"role": "user", "content": "test"}],
            "trial-3", 0
        )

        retry_findings = ledger.query(tag="api-retry")
        failure_findings = ledger.query(tag="api-failure")
        # Should have retry findings + final failure finding
        self.assertGreater(len(retry_findings), 0)
        self.assertGreater(len(failure_findings), 0)


class TestIntegrationWithSummaryParser(unittest.TestCase):
    """Test integration with summary_parser module."""

    def test_parse_summary_provenance_called(self):
        """Boundary capture uses parse_summary_provenance from summary_parser."""
        tmpdir = tempfile.mkdtemp()
        config = RunnerConfig(
            dry_run=True, num_iterations=5,
            output_dir=os.path.join(tmpdir, "out"),
        )
        runner = GenuineCompactionRunner(config)
        result = runner.run_trial(MockTaskTemplate(num_iterations=5))

        # Verify provenance metadata is present in boundaries
        self.assertGreater(len(result.boundaries), 0)
        boundary = result.boundaries[0]
        self.assertIn("provenance_metadata", boundary)
        prov = boundary["provenance_metadata"]
        self.assertIn("artifact_ids", prov)
        self.assertIn("provenance_density", prov)


class TestIntegrationWithEmbeddingSimilarity(unittest.TestCase):
    """Test integration with embedding_similarity module."""

    def test_tier_classification_uses_similarity(self):
        """Boundary capture uses embedding_similarity for tier classification."""
        tmpdir = tempfile.mkdtemp()
        config = RunnerConfig(
            dry_run=True, num_iterations=5,
            output_dir=os.path.join(tmpdir, "out"),
        )
        runner = GenuineCompactionRunner(config)
        result = runner.run_trial(MockTaskTemplate(num_iterations=5))

        # Verify tier classification exists
        self.assertGreater(len(result.boundaries), 0)
        boundary = result.boundaries[0]
        tiers = boundary["tier_classification"]
        self.assertIsInstance(tiers, dict)
        for tier in tiers.values():
            self.assertIn(tier, ["resolved", "degraded", "broken"])


class TestMockLMAnchor(unittest.TestCase):
    """Verify dry-run metrics match MockLM anchor expectations.

    MockLM anchor: structural_reachability = 1.0 for uncompacted data.
    In dry-run, surviving artifacts (those in the summary) should have
    structural_reachability = 1.0 if all are present.
    """

    def test_full_survival_matches_mockml_ceiling(self):
        """When all artifact IDs are in the summary,
        structural_reachability = 1.0 (matches MockLM ceiling)."""
        ids = ["artifact:r1:iter:0:r1", "artifact:r1:iter:1:r1",
               "artifact:r1:iter:2:r1"]
        summary = " ".join(f"[PROVENANCE: {aid}]" for aid in ids)
        survival = compute_artifact_survival(ids, summary)
        self.assertEqual(survival["survival_rate"], 1.0,
                         "Full survival should match MockLM ceiling of 1.0")


if __name__ == "__main__":
    unittest.main()
