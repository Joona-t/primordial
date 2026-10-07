"""Tests for compaction_experiment.py."""

import tempfile
import unittest

from compaction_experiment import (
    inject_artifact_markers,
    extract_artifact_ids,
    compute_artifact_survival,
    CompactionEvent,
    ExperimentConfig,
    CompactionExperiment,
)
from findings_ledger import FindingsLedger


class TestArtifactInjection(unittest.TestCase):

    def test_inject_adds_marker(self):
        text, aid = inject_artifact_markers("hello", "run1", 0)
        self.assertIn("artifact:run1:iter:0:r1", text)
        self.assertEqual(aid, "artifact:run1:iter:0:r1")

    def test_extract_finds_markers(self):
        text = "Some text artifact:run1:iter:0:r1 and artifact:run1:iter:1:r1 more"
        ids = extract_artifact_ids(text)
        self.assertEqual(len(ids), 2)
        self.assertIn("artifact:run1:iter:0:r1", ids)

    def test_extract_empty(self):
        self.assertEqual(extract_artifact_ids("no markers here"), [])


class TestArtifactSurvival(unittest.TestCase):

    def test_full_survival(self):
        ids = ["artifact:r1:iter:0:r1", "artifact:r1:iter:1:r1"]
        text = "Summary with artifact:r1:iter:0:r1 and artifact:r1:iter:1:r1"
        result = compute_artifact_survival(ids, text)
        self.assertEqual(result["survival_rate"], 1.0)
        self.assertEqual(result["ids_lost"], 0)

    def test_partial_survival(self):
        ids = ["artifact:r1:iter:0:r1", "artifact:r1:iter:1:r1"]
        text = "Only artifact:r1:iter:0:r1 survived"
        result = compute_artifact_survival(ids, text)
        self.assertEqual(result["survival_rate"], 0.5)
        self.assertEqual(result["ids_survived"], 1)
        self.assertEqual(len(result["lost"]), 1)

    def test_total_loss(self):
        ids = ["artifact:r1:iter:0:r1"]
        text = "Nothing survived"
        result = compute_artifact_survival(ids, text)
        self.assertEqual(result["survival_rate"], 0.0)

    def test_empty_ids(self):
        result = compute_artifact_survival([], "any text")
        self.assertEqual(result["survival_rate"], 0.0)
        self.assertEqual(result["ids_before"], 0)


class TestCompactionExperiment(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_simulated_run_completes(self):
        config = ExperimentConfig(run_id="test-sim-1", num_iterations=5)
        exp = CompactionExperiment(config, self.ledger)
        result = exp._run_simulated()
        self.assertEqual(result["run_id"], "test-sim-1")
        self.assertEqual(result["iterations"], 5)
        self.assertGreater(result["compaction_events"], 0)
        self.assertEqual(len(result["chamber_validation"]), 0)

    def test_simulated_records_to_ledger(self):
        config = ExperimentConfig(run_id="test-sim-2", num_iterations=5)
        exp = CompactionExperiment(config, self.ledger)
        exp._run_simulated()
        # Should have at least 1 compaction event finding
        findings = self.ledger.query(tag="genuine-compaction")
        self.assertGreater(len(findings), 0)

    def test_simulated_creates_forge_artifacts(self):
        config = ExperimentConfig(run_id="test-sim-3", num_iterations=5)
        exp = CompactionExperiment(config, self.ledger)
        result = exp._run_simulated()
        self.assertEqual(result["total_artifacts"], 5)

    def test_compaction_event_has_spf(self):
        config = ExperimentConfig(run_id="test-sim-4", num_iterations=8)
        exp = CompactionExperiment(config, self.ledger)
        result = exp._run_simulated()
        events = result["events"]
        self.assertGreater(len(events), 0)
        event = events[0]
        self.assertIn("spf_scores", event)
        self.assertIn("artifact_survival", event)

    def test_provenance_aware_config(self):
        config = ExperimentConfig(
            run_id="test-prov",
            num_iterations=5,
            provenance_aware_instructions=True,
        )
        exp = CompactionExperiment(config, self.ledger)
        prompt = exp._build_system_prompt()
        self.assertIn("artifact", prompt.lower())
        self.assertIn("provenance", prompt.lower())

    def test_different_task_categories(self):
        for cat in ["coding", "debugging", "specification"]:
            config = ExperimentConfig(run_id=f"test-{cat}", task_category=cat, num_iterations=3)
            exp = CompactionExperiment(config, self.ledger)
            result = exp._run_simulated()
            self.assertEqual(result["task_category"], cat)

    def test_api_falls_back_to_simulated(self):
        """Without ANTHROPIC_API_KEY, run_api should fall back to simulated."""
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            config = ExperimentConfig(run_id="test-fallback", num_iterations=3)
            exp = CompactionExperiment(config, self.ledger)
            result = exp.run_api()
            self.assertEqual(result["run_id"], "test-fallback")
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key


import os  # needed for test_api_falls_back

if __name__ == "__main__":
    unittest.main()
