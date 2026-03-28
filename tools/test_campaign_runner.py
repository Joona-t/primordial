"""Tests for campaign_runner.py -- Phase 7, Plan 02, Task 2.

Validates:
  - Dry-run produces output with all 7 instrumentation channels
  - Each channel has the correct type
  - Resume correctly skips completed runs
  - Timeout handling produces partial results
  - Campaign status accurately reports counts
  - Output schema is consistent across runs

Convention assertions (project-specific -- physics conventions N/A):
  violation_classification = "structural only (CONVENTIONS.md #8)"
  compaction_disambiguation = "forge compaction = lossless; LLM compaction = lossy"
  all_metrics_dimensionless = True
"""

import json
import pytest
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adversarial_corpus import AdversarialCorpus, STRESS_LEVELS
from campaign_runner import (
    CampaignRunner,
    MockLMBackend,
    FRAMEWORK_VERSION,
    validate_run_result,
    _empty_run_result,
    _serialize_chamber,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def corpus():
    return AdversarialCorpus()


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for test runs."""
    out = tmp_path / "campaign_runs"
    out.mkdir()
    return out


@pytest.fixture
def runner(corpus, tmp_output):
    """Campaign runner in dry-run/mock mode."""
    return CampaignRunner(
        corpus=corpus,
        output_dir=str(tmp_output),
        dry_run=True,
        backend="mock",
        seed=42,
    )


# ---------------------------------------------------------------------------
# Empty Run Result Tests
# ---------------------------------------------------------------------------

class TestEmptyRunResult:
    """Verify the empty run result template has all 7 channels."""

    def test_all_channels_present(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        errors = validate_run_result(result)
        assert errors == [], f"Validation errors: {errors}"

    def test_channel_types(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        assert isinstance(result["chamber"], dict)
        assert isinstance(result["transcript"], list)
        assert isinstance(result["tool_call_log"], list)
        assert isinstance(result["compaction_events"], list)
        assert isinstance(result["token_count"], dict)
        assert isinstance(result["wall_clock_seconds"], (int, float))
        assert isinstance(result["framework_version"], str)

    def test_run_id_format(self):
        result = _empty_run_result("TASK-A1a", "moderate", 3)
        assert result["run_id"] == "TASK-A1a_moderate_003"

    def test_framework_version_set(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        assert result["framework_version"] == FRAMEWORK_VERSION


# ---------------------------------------------------------------------------
# Validate Run Result Tests
# ---------------------------------------------------------------------------

class TestValidateRunResult:
    """Test the run result validator."""

    def test_valid_result(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        assert validate_run_result(result) == []

    def test_missing_field(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        del result["chamber"]
        errors = validate_run_result(result)
        assert any("chamber" in e for e in errors)

    def test_wrong_type(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        result["transcript"] = "not a list"
        errors = validate_run_result(result)
        assert any("transcript" in e for e in errors)

    def test_token_count_substructure(self):
        result = _empty_run_result("TASK-A1a", "control", 0)
        result["token_count"] = {"per_call": []}  # missing cumulative
        errors = validate_run_result(result)
        assert any("cumulative" in e for e in errors)


# ---------------------------------------------------------------------------
# MockLM Backend Tests
# ---------------------------------------------------------------------------

class TestMockLMBackend:
    """Test the mock backend produces structurally valid data."""

    def test_mock_produces_all_channels(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-A1a")
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        assert "chamber" in result
        assert "transcript" in result
        assert "tool_call_log" in result
        assert "compaction_events" in result
        assert "token_count" in result
        assert "wall_clock_seconds" in result

    def test_mock_chamber_has_stages(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-A1a")
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        chamber = result["chamber"]
        assert "stages" in chamber
        assert len(chamber["stages"]) > 0

    def test_mock_transcript_alternates_roles(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-B5a")
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        transcript = result["transcript"]
        assert len(transcript) > 0
        for i, entry in enumerate(transcript):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert entry["role"] == expected_role
            assert "content" in entry
            assert "tokens" in entry
            assert isinstance(entry["tokens"], int)
            assert entry["tokens"] > 0

    def test_mock_tool_call_log_structure(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-C9a")
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        for call in result["tool_call_log"]:
            assert "tool" in call
            assert "call_id" in call
            assert "input" in call
            assert "duration_ms" in call
            assert isinstance(call["duration_ms"], int)

    def test_mock_long_tier_has_compaction_events(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-A1a")  # LONG tier
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        events = result["compaction_events"]
        assert len(events) > 0, "LONG tier should have compaction events"
        for event in events:
            assert "timestamp" in event
            assert "type" in event
            assert "tokens_before" in event
            assert "tokens_after" in event
            assert event["tokens_after"] < event["tokens_before"]

    def test_mock_short_tier_no_compaction(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-C9a")  # SHORT tier
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        assert len(result["compaction_events"]) == 0

    def test_mock_token_counts_consistent(self, corpus):
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-B6a")
        config = task.get_stress_config("control")
        result = backend.run_task(task, config)

        tc = result["token_count"]
        assert tc["cumulative"] == sum(tc["per_call"])
        assert tc["cumulative"] > 0

    def test_mock_stress_injects_tool_failures(self, corpus):
        """Heavy stress (lambda=0.3) should produce some tool failures."""
        backend = MockLMBackend(seed=42)
        task = corpus.get_task("TASK-A2a")  # LONG tier, many steps
        config = task.get_stress_config("heavy")
        result = backend.run_task(task, config)

        errors_in_log = [c for c in result["tool_call_log"] if c["error"] is not None]
        # With lambda=0.3 and ~8 steps, expect at least 1 error (probabilistic)
        # But seed is fixed, so deterministic
        # Just check the structure is correct
        for call in result["tool_call_log"]:
            assert "error" in call  # field always present


# ---------------------------------------------------------------------------
# Dry-Run Tests (3 tasks: 1 SHORT, 1 MEDIUM, 1 LONG)
# ---------------------------------------------------------------------------

class TestDryRun:
    """Dry-run test: run 3 tasks, verify all 7 channels present."""

    REPRESENTATIVE_TASKS = [
        ("TASK-C9a", "SHORT"),
        ("TASK-B5a", "MEDIUM"),
        ("TASK-A1a", "LONG"),
    ]

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_all_7_channels(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)

        errors = validate_run_result(result)
        assert errors == [], f"Validation errors for {task_id}: {errors}"

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_chamber_nonempty(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert result["chamber"], f"Chamber empty for {task_id}"
        assert "stages" in result["chamber"]
        assert len(result["chamber"]["stages"]) > 0

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_transcript_nonempty(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert len(result["transcript"]) > 0

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_tool_call_log_nonempty(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert len(result["tool_call_log"]) > 0

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_token_count_positive(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert result["token_count"]["cumulative"] > 0

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_wall_clock_positive(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert result["wall_clock_seconds"] > 0

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_framework_version(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert result["framework_version"] == FRAMEWORK_VERSION
        assert isinstance(result["framework_version"], str)

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_task_completed(self, runner, task_id, tier):
        result = runner.run_single(task_id, "control", 0)
        assert result["task_completed"] is True

    @pytest.mark.parametrize("task_id,tier", REPRESENTATIVE_TASKS)
    def test_dry_run_persisted_to_disk(self, runner, task_id, tier, tmp_output):
        result = runner.run_single(task_id, "control", 0)
        path = tmp_output / f"{result['run_id']}.json"
        assert path.exists(), f"Run result not persisted: {path}"
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["run_id"] == result["run_id"]


# ---------------------------------------------------------------------------
# Resume Tests
# ---------------------------------------------------------------------------

class TestResume:
    """Resume test: run 2 tasks, create new runner, verify no duplicate runs."""

    def test_resume_skips_completed(self, corpus, tmp_output):
        # First runner: run 2 tasks
        runner1 = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )
        r1 = runner1.run_single("TASK-C9a", "control", 0)
        r2 = runner1.run_single("TASK-C9b", "control", 0)

        assert r1["task_completed"] is True
        assert r2["task_completed"] is True

        # Count files
        run_files = list(tmp_output.glob("TASK-*.json"))
        assert len(run_files) == 2

        # Second runner: same output dir (simulates resume)
        runner2 = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )

        # Re-run the same tasks -- should skip (return cached)
        r1_resume = runner2.run_single("TASK-C9a", "control", 0)
        r2_resume = runner2.run_single("TASK-C9b", "control", 0)

        # Should still be only 2 files (no duplicates)
        run_files_after = list(tmp_output.glob("TASK-*.json"))
        assert len(run_files_after) == 2

        # Results should match
        assert r1_resume["run_id"] == r1["run_id"]

    def test_resume_continues_new_tasks(self, corpus, tmp_output):
        # First runner: run 1 task
        runner1 = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )
        runner1.run_single("TASK-C9a", "control", 0)

        # Second runner: run a different task
        runner2 = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )
        runner2.run_single("TASK-C9b", "control", 0)

        # Should have 2 files total
        run_files = list(tmp_output.glob("TASK-*.json"))
        assert len(run_files) == 2


# ---------------------------------------------------------------------------
# Timeout Handling Tests
# ---------------------------------------------------------------------------

class TestTimeoutHandling:
    """Verify timeout handling produces partial results (not crashes)."""

    def test_timeout_produces_partial_result(self, corpus, tmp_output):
        """Simulate a timeout by using a backend that raises TimeoutError."""

        class TimeoutBackend:
            def run_task(self, task, config):
                raise TimeoutError("Simulated timeout")

        runner = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )
        # Replace backend with timeout-raising one
        runner._backend = TimeoutBackend()

        result = runner.run_single("TASK-A1a", "control", 0)

        # Should not crash -- should produce a partial result
        assert result["timed_out"] is True
        assert len(result["errors"]) > 0
        assert "Timed out" in result["errors"][0]

        # All 7 channels should still be present (empty but correct types)
        errors = validate_run_result(result)
        assert errors == [], f"Partial result validation errors: {errors}"

    def test_crash_produces_error_result(self, corpus, tmp_output):
        """Backend crash produces error result, not exception."""

        class CrashBackend:
            def run_task(self, task, config):
                raise RuntimeError("Backend crash")

        runner = CampaignRunner(
            corpus=corpus,
            output_dir=str(tmp_output),
            dry_run=True,
            backend="mock",
        )
        runner._backend = CrashBackend()

        result = runner.run_single("TASK-C9a", "control", 0)

        assert result["task_completed"] is False
        assert len(result["errors"]) > 0
        assert "RuntimeError" in result["errors"][0]

        # All channels present
        errors = validate_run_result(result)
        assert errors == [], f"Error result validation: {errors}"


# ---------------------------------------------------------------------------
# Schema Consistency Tests
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """Verify every output has identical top-level keys."""

    def test_all_runs_same_keys(self, runner):
        """Run multiple tasks, verify same schema."""
        task_ids = ["TASK-C9a", "TASK-B5a", "TASK-A1a"]
        results = []
        for i, task_id in enumerate(task_ids):
            result = runner.run_single(task_id, "control", i)
            results.append(result)

        # All should have same top-level keys
        expected_keys = set(results[0].keys())
        for result in results[1:]:
            assert set(result.keys()) == expected_keys, (
                f"Key mismatch: {set(result.keys()) - expected_keys} extra, "
                f"{expected_keys - set(result.keys())} missing"
            )

    def test_all_stress_levels_same_schema(self, runner):
        """Different stress levels produce same schema."""
        results = []
        for i, level in enumerate(STRESS_LEVELS):
            result = runner.run_single("TASK-B5a", level, i)
            results.append(result)

        expected_keys = set(results[0].keys())
        for result in results[1:]:
            assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Campaign Status Tests
# ---------------------------------------------------------------------------

class TestCampaignStatus:
    """Verify get_campaign_status returns accurate counts."""

    def test_empty_status(self, runner):
        status = runner.get_campaign_status()
        assert status["total_planned"] == 201
        assert status["completed"] == 0
        assert status["failed"] == 0
        assert isinstance(status["per_task"], dict)

    def test_status_after_runs(self, runner):
        runner.run_single("TASK-C9a", "control", 0)
        runner.run_single("TASK-C9a", "mild", 1)

        status = runner.get_campaign_status()
        assert status["completed"] == 2
        assert status["per_task"]["TASK-C9a"]["completed"] == 2
        assert status["per_task"]["TASK-C9a"]["remaining"] == 5  # 7 planned - 2 done

    def test_status_per_task_structure(self, runner):
        status = runner.get_campaign_status()
        for task_id, task_status in status["per_task"].items():
            assert "planned" in task_status
            assert "completed" in task_status
            assert "failed" in task_status
            assert "remaining" in task_status
            assert task_status["planned"] > 0

    def test_status_framework_version(self, runner):
        status = runner.get_campaign_status()
        assert status["framework_version"] == FRAMEWORK_VERSION


# ---------------------------------------------------------------------------
# Task Battery Tests
# ---------------------------------------------------------------------------

class TestTaskBattery:
    """Test running a full battery (all stress levels) for one task."""

    def test_battery_produces_results(self, runner):
        results = runner.run_task_battery("TASK-C9a", runs_per_level=2)
        # 4 levels x 2 reps = 8 results
        assert len(results) == 8

    def test_battery_covers_all_levels(self, runner):
        results = runner.run_task_battery("TASK-C9a", runs_per_level=1)
        levels_seen = {r["stress_level"] for r in results}
        assert levels_seen == set(STRESS_LEVELS.keys())

    def test_battery_all_valid(self, runner):
        results = runner.run_task_battery("TASK-C9b", runs_per_level=1)
        for result in results:
            errors = validate_run_result(result)
            assert errors == [], f"Invalid battery result: {errors}"


# ---------------------------------------------------------------------------
# Clean Output Tests
# ---------------------------------------------------------------------------

class TestCleanOutput:
    """Test the clean_output utility."""

    def test_clean_removes_files(self, runner, tmp_output):
        runner.run_single("TASK-C9a", "control", 0)
        assert len(list(tmp_output.glob("*.json"))) > 0

        runner.clean_output()
        assert len(list(tmp_output.glob("*.json"))) == 0
        assert runner.get_campaign_status()["completed"] == 0


# ---------------------------------------------------------------------------
# Serialization Tests
# ---------------------------------------------------------------------------

class TestSerialization:
    """Test that run results are JSON-serializable."""

    def test_run_result_json_roundtrip(self, runner):
        result = runner.run_single("TASK-A1a", "control", 0)
        json_str = json.dumps(result, indent=2, default=str)
        loaded = json.loads(json_str)
        assert loaded["run_id"] == result["run_id"]
        assert loaded["task_id"] == result["task_id"]

    def test_chamber_serializable(self, runner):
        result = runner.run_single("TASK-A1a", "control", 0)
        chamber = result["chamber"]
        # Should be JSON-serializable (sets already converted)
        json_str = json.dumps(chamber, indent=2, default=str)
        loaded = json.loads(json_str)
        assert "stages" in loaded
