"""Tests for adversarial_corpus.py -- Phase 7, Plan 02, Task 1.

Validates:
  - All 20 task templates instantiate and generate valid workspaces
  - D-type coverage: each D-type targeted by >= 2 task categories
  - Tier distribution matches RESEARCH Section 5.1
  - Stress config generation for all 4 levels
  - Control variants exist for all Tier A/B tasks
  - Corpus manifest is valid JSON with all required fields

Convention assertions (project-specific -- physics conventions N/A):
  violation_classification = "structural only (CONVENTIONS.md #8)"
  d_type_taxonomy = "D1-D9 per CONVENTIONS.md"
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adversarial_corpus import (
    STRESS_LEVELS,
    TASK_CLASSES,
    CONTROL_CLASSES,
    ALL_TASK_CLASSES,
    VALID_STRESS_LEVELS,
    VALID_TIERS,
    VALID_DTYPES,
    AdversarialCorpus,
    AdversarialTask,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def corpus():
    return AdversarialCorpus()


@pytest.fixture
def manifest(corpus):
    return corpus.generate_manifest()


# ---------------------------------------------------------------------------
# Task Instantiation Tests
# ---------------------------------------------------------------------------

class TestTaskInstantiation:
    """Each of 20 tasks can be instantiated and generates a valid workspace."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_instantiate_task(self, cls):
        task = cls()
        assert isinstance(task, AdversarialTask)
        assert task.task_id.startswith("TASK-")

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_workspace_structure(self, cls):
        task = cls()
        ws = task.generate_workspace()
        assert isinstance(ws, dict)
        assert "files" in ws
        assert "tools" in ws
        assert "constraints" in ws
        assert isinstance(ws["files"], dict)
        assert isinstance(ws["tools"], list)
        assert isinstance(ws["constraints"], dict)
        assert len(ws["files"]) > 0, f"{task.task_id}: workspace has no files"
        assert len(ws["tools"]) > 0, f"{task.task_id}: workspace has no tools"

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_workspace_files_are_strings(self, cls):
        task = cls()
        ws = task.generate_workspace()
        for fname, content in ws["files"].items():
            assert isinstance(fname, str), f"filename is not str: {type(fname)}"
            assert isinstance(content, str), f"content of {fname} is not str"
            assert len(content) > 0, f"content of {fname} is empty"


class TestTaskAttributes:
    """Each task has valid class-level attributes."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_target_dtypes_nonempty(self, cls):
        assert len(cls.target_dtypes) > 0, f"{cls.task_id}: no target D-types"

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_target_dtypes_valid(self, cls):
        for dtype in cls.target_dtypes:
            assert dtype in VALID_DTYPES, f"{cls.task_id}: invalid D-type {dtype}"

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_tier_valid(self, cls):
        assert cls.tier in VALID_TIERS, f"{cls.task_id}: invalid tier {cls.tier}"

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_category_format(self, cls):
        # Category must be like "A1-description" or "C9-description"
        parts = cls.category.split("-", 1)
        assert len(parts) == 2, f"{cls.task_id}: category format wrong: {cls.category}"
        code = parts[0]
        assert len(code) >= 2, f"{cls.task_id}: category code too short: {code}"

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_has_title(self, cls):
        assert isinstance(cls.title, str)
        assert len(cls.title) > 0

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_has_stress_mechanism(self, cls):
        assert isinstance(cls.stress_mechanism, str)
        assert len(cls.stress_mechanism) > 5


# ---------------------------------------------------------------------------
# D-Type Coverage Tests
# ---------------------------------------------------------------------------

class TestDTypeCoverage:
    """D-type coverage matrix: each D-type targeted by >= 2 categories."""

    def test_all_9_dtypes_covered(self, corpus):
        matrix = corpus.get_dtype_coverage_matrix()
        for i in range(1, 10):
            dtype = f"D{i}"
            assert len(matrix[dtype]) > 0, f"{dtype} has no targeting tasks"

    def test_each_dtype_by_at_least_2_categories(self, corpus):
        cat_coverage = corpus.get_dtype_category_coverage()
        for dtype, categories in cat_coverage.items():
            assert len(categories) >= 2, (
                f"{dtype} targeted by only {len(categories)} category(ies): "
                f"{categories}. Need >= 2."
            )

    def test_total_unique_dtype_task_pairs(self, corpus):
        """Total unique (task, D-type) pairs >= 30."""
        matrix = corpus.get_dtype_coverage_matrix()
        total_pairs = sum(len(tasks) for tasks in matrix.values())
        assert total_pairs >= 30, f"Only {total_pairs} unique (task, D-type) pairs, need >= 30"


# ---------------------------------------------------------------------------
# Tier Distribution Tests
# ---------------------------------------------------------------------------

class TestTierDistribution:
    """Tier distribution matches RESEARCH Section 5.1."""

    def test_short_count(self, corpus):
        dist = corpus.get_tier_distribution()
        assert dist["SHORT"] >= 3, f"Only {dist['SHORT']} SHORT tasks, need >= 3"

    def test_medium_count(self, corpus):
        dist = corpus.get_tier_distribution()
        assert dist["MEDIUM"] >= 4, f"Only {dist['MEDIUM']} MEDIUM tasks, need >= 4"

    def test_long_count(self, corpus):
        dist = corpus.get_tier_distribution()
        assert dist["LONG"] >= 5, f"Only {dist['LONG']} LONG tasks, need >= 5"

    def test_extreme_count(self, corpus):
        dist = corpus.get_tier_distribution()
        assert dist["EXTREME"] >= 1, f"Only {dist['EXTREME']} EXTREME tasks, need >= 1"


# ---------------------------------------------------------------------------
# Category Distribution Tests
# ---------------------------------------------------------------------------

class TestCategoryDistribution:
    """Category counts match RESEARCH Section 5.1."""

    EXPECTED_COUNTS = {
        "A1": 3, "A2": 3, "A3": 2, "A4": 2,
        "B5": 2, "B6": 2, "B7": 2, "B8": 1, "C9": 3,
    }

    def test_category_counts(self, corpus):
        coverage = corpus.get_category_coverage()
        for cat, expected in self.EXPECTED_COUNTS.items():
            actual = len(coverage.get(cat, []))
            assert actual == expected, (
                f"Category {cat}: expected {expected} tasks, got {actual}. "
                f"Tasks: {coverage.get(cat, [])}"
            )

    def test_total_task_count(self, corpus):
        assert len(corpus.tasks) == 20, f"Expected 20 tasks, got {len(corpus.tasks)}"


# ---------------------------------------------------------------------------
# Stress Configuration Tests
# ---------------------------------------------------------------------------

class TestStressConfig:
    """Stress config generation: all 4 levels produce valid configs for each task."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_all_stress_levels_valid(self, cls):
        task = cls()
        for level in VALID_STRESS_LEVELS:
            config = task.get_stress_config(level)
            assert isinstance(config, dict)
            assert "epsilon" in config
            assert "lambda_" in config
            assert "stress_level" in config
            assert "tier_config" in config
            assert "tool_failure_rate" in config
            assert "ambiguity_injection" in config
            assert 0.0 <= config["epsilon"] <= 1.0
            assert 0.0 <= config["lambda_"] <= 1.0
            assert config["stress_level"] == level

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_control_has_zero_stress(self, cls):
        task = cls()
        config = task.get_stress_config("control")
        assert config["epsilon"] == 0.0
        assert config["lambda_"] == 0.0

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_heavy_has_highest_lambda(self, cls):
        task = cls()
        heavy = task.get_stress_config("heavy")
        mild = task.get_stress_config("mild")
        assert heavy["lambda_"] > mild["lambda_"]

    def test_invalid_stress_level_raises(self):
        task = TASK_CLASSES[0]()
        with pytest.raises(AssertionError):
            task.get_stress_config("nonexistent")


# ---------------------------------------------------------------------------
# Prompt Generation Tests
# ---------------------------------------------------------------------------

class TestPromptGeneration:
    """Prompt generation at different stress levels."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_generate_prompt_control(self, cls):
        task = cls()
        prompt = task.generate_prompt("control")
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_generate_prompt_all_levels(self, cls):
        task = cls()
        for level in VALID_STRESS_LEVELS:
            prompt = task.generate_prompt(level)
            assert isinstance(prompt, str)
            assert len(prompt) > 10

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_stressed_prompts_differ_from_control(self, cls):
        """Stressed prompts should have ambiguity additions."""
        task = cls()
        control = task.generate_prompt("control")
        moderate = task.generate_prompt("moderate")
        # Moderate adds ambiguity text, so should be longer
        assert len(moderate) >= len(control)


# ---------------------------------------------------------------------------
# Control Variant Tests
# ---------------------------------------------------------------------------

class TestControlVariants:
    """Control variants exist for all Tier A/B tasks."""

    def test_tier_a_tasks_have_controls(self, corpus):
        for task in corpus.tasks.values():
            cat_prefix = task.category.split("-")[0]
            if cat_prefix.startswith("A"):
                ctrl_id = task.get_control_variant_id()
                assert ctrl_id is not None, (
                    f"Tier A task {task.task_id} has no control variant"
                )
                assert ctrl_id in corpus.all_tasks, (
                    f"Control variant {ctrl_id} for {task.task_id} not found in corpus"
                )

    def test_tier_b_tasks_have_controls(self, corpus):
        for task in corpus.tasks.values():
            cat_prefix = task.category.split("-")[0]
            if cat_prefix.startswith("B"):
                ctrl_id = task.get_control_variant_id()
                assert ctrl_id is not None, (
                    f"Tier B task {task.task_id} has no control variant"
                )
                assert ctrl_id in corpus.all_tasks, (
                    f"Control variant {ctrl_id} for {task.task_id} not found in corpus"
                )

    def test_tier_c_tasks_are_controls(self, corpus):
        """C9 tasks are themselves controls -- no further control variant."""
        for task in corpus.tasks.values():
            if task.category.startswith("C9"):
                assert task.get_control_variant_id() is None, (
                    f"C9 task {task.task_id} should not have a control variant"
                )

    def test_control_variants_instantiate(self):
        """Each control variant class can be instantiated."""
        for cls in CONTROL_CLASSES:
            ctrl = cls()
            ws = ctrl.generate_workspace()
            assert isinstance(ws, dict)
            assert "files" in ws

    def test_control_variant_count(self):
        """17 control variants: 14 for Tier A + B tasks (minus C9)."""
        # A1: 3, A2: 3, A3: 2, A4: 2, B5: 2, B6: 2, B7: 2, B8: 1 = 17
        assert len(CONTROL_CLASSES) == 17, (
            f"Expected 17 control variants, got {len(CONTROL_CLASSES)}"
        )


# ---------------------------------------------------------------------------
# Corpus Manifest Tests
# ---------------------------------------------------------------------------

class TestCorpusManifest:
    """Corpus manifest is valid JSON with all required fields."""

    def test_manifest_has_required_fields(self, manifest):
        required = ["version", "total_tasks", "total_planned_runs",
                     "categories", "tasks", "dtype_coverage_matrix", "stress_levels"]
        for field in required:
            assert field in manifest, f"Manifest missing field: {field}"

    def test_manifest_version(self, manifest):
        assert manifest["version"] == "7.0"

    def test_manifest_total_tasks(self, manifest):
        assert manifest["total_tasks"] == 20

    def test_manifest_total_runs(self, manifest):
        assert manifest["total_planned_runs"] >= 200, (
            f"Only {manifest['total_planned_runs']} planned runs, need >= 200"
        )

    def test_manifest_exact_run_count(self, manifest):
        """Target: 201 runs per RESEARCH Section 5.1."""
        assert manifest["total_planned_runs"] == 201, (
            f"Expected 201 planned runs, got {manifest['total_planned_runs']}"
        )

    def test_manifest_tasks_list(self, manifest):
        assert len(manifest["tasks"]) == 20
        for task_meta in manifest["tasks"]:
            assert "task_id" in task_meta
            assert "category" in task_meta
            assert "tier" in task_meta
            assert "target_dtypes" in task_meta
            assert "runs_planned" in task_meta
            assert "stress_levels" in task_meta
            assert "control_variant" in task_meta

    def test_manifest_dtype_matrix_complete(self, manifest):
        matrix = manifest["dtype_coverage_matrix"]
        for i in range(1, 10):
            dtype = f"D{i}"
            assert dtype in matrix, f"{dtype} missing from coverage matrix"
            assert len(matrix[dtype]) > 0, f"{dtype} has no targeting tasks in matrix"

    def test_manifest_json_serializable(self, corpus):
        """Manifest must be JSON-serializable (for writing to file)."""
        manifest = corpus.generate_manifest()
        json_str = json.dumps(manifest, indent=2, default=list)
        loaded = json.loads(json_str)
        assert loaded["total_tasks"] == 20

    def test_write_manifest(self, corpus, tmp_path):
        """Test writing manifest to disk."""
        out_path = tmp_path / "manifest.json"
        manifest = corpus.write_manifest(out_path)
        assert out_path.exists()
        with open(out_path) as f:
            loaded = json.load(f)
        assert loaded["total_tasks"] == 20
        assert loaded["total_planned_runs"] == 201


# ---------------------------------------------------------------------------
# Metadata Tests
# ---------------------------------------------------------------------------

class TestMetadata:
    """Task metadata is complete and consistent."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_get_metadata(self, cls):
        task = cls()
        meta = task.get_metadata()
        assert meta["task_id"] == cls.task_id
        assert meta["category"] == cls.category
        assert meta["tier"] == cls.tier
        assert meta["title"] == cls.title
        assert meta["target_dtypes"] == list(cls.target_dtypes)

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_expected_tokens_format(self, cls):
        """expected_tokens should be like '50K-80K' or '5K-10K'."""
        assert "K" in cls.expected_tokens, f"{cls.task_id}: expected_tokens missing 'K'"


# ---------------------------------------------------------------------------
# Success Checker Tests
# ---------------------------------------------------------------------------

class TestSuccessChecker:
    """Success checker works for basic cases."""

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_success_with_completed_true(self, cls):
        task = cls()
        assert task.check_success({"completed": True}) is True

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_failure_with_completed_false(self, cls):
        task = cls()
        assert task.check_success({"completed": False}) is False

    @pytest.mark.parametrize("cls", TASK_CLASSES, ids=[c.task_id for c in TASK_CLASSES])
    def test_failure_with_empty_result(self, cls):
        task = cls()
        assert task.check_success({}) is False


# ---------------------------------------------------------------------------
# Cross-Validation Tests
# ---------------------------------------------------------------------------

class TestCrossValidation:
    """Cross-validation between task attributes and corpus."""

    def test_no_duplicate_task_ids(self):
        ids = [cls.task_id for cls in TASK_CLASSES]
        assert len(ids) == len(set(ids)), f"Duplicate task IDs: {ids}"

    def test_no_duplicate_control_ids(self):
        ids = [cls.task_id for cls in CONTROL_CLASSES]
        assert len(ids) == len(set(ids)), f"Duplicate control IDs: {ids}"

    def test_no_overlap_task_control_ids(self):
        task_ids = {cls.task_id for cls in TASK_CLASSES}
        ctrl_ids = {cls.task_id for cls in CONTROL_CLASSES}
        overlap = task_ids & ctrl_ids
        assert len(overlap) == 0, f"Task/control ID overlap: {overlap}"

    def test_all_classes_in_registry(self):
        for cls in TASK_CLASSES + CONTROL_CLASSES:
            assert cls.task_id in ALL_TASK_CLASSES

    def test_control_variant_ids_resolve(self):
        """Every control_variant_id in a primary task resolves to a control class."""
        for cls in TASK_CLASSES:
            ctrl_id = cls.control_variant_id
            if ctrl_id is not None:
                assert ctrl_id in ALL_TASK_CLASSES, (
                    f"{cls.task_id} references control {ctrl_id} which doesn't exist"
                )

    def test_runs_per_task_covers_all_tasks(self, corpus):
        """RUNS_PER_TASK has an entry for every primary task."""
        for task_id in corpus.tasks:
            assert task_id in corpus.RUNS_PER_TASK, (
                f"{task_id} missing from RUNS_PER_TASK"
            )
