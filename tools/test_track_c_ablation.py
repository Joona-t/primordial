"""Tests for track_c_ablation.py — Phase 6, Plan 04.

Validates:
1. Condition generation: 9 conditions (3 instruction x 3 threshold)
2. Condition ID uniqueness and descriptiveness
3. Dry-run of single condition: metrics computed
4. Aggregation: mean/std/CI computed correctly on known inputs
5. Delta computation: provenance_aware - default computed correctly
6. Bonferroni correction: corrected p-values
7. Full dry-run ablation (N=1 per condition)
8. Export: JSONL and JSON valid
9. Bootstrap permutation test
10. Statistical utilities edge cases
"""

import json
import math
import os
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent))

from track_c_ablation import (
    INSTRUCTION_VARIANTS,
    THRESHOLD_LEVELS,
    MODEL_VARIANTS,
    AblationConfig,
    AblationRunner,
    ConditionSummary,
    AblationResults,
    _compute_ci,
    _bootstrap_permutation_test,
    _bonferroni_correct,
    _cycle_task_template,
)
from genuine_compaction_runner import TrialResult


class TestInstructionVariants(unittest.TestCase):
    """Test instruction variant definitions."""

    def test_three_instruction_variants(self):
        self.assertEqual(len(INSTRUCTION_VARIANTS), 3)

    def test_variant_names(self):
        self.assertIn("default", INSTRUCTION_VARIANTS)
        self.assertIn("provenance_aware", INSTRUCTION_VARIANTS)
        self.assertIn("minimal", INSTRUCTION_VARIANTS)

    def test_default_is_none(self):
        self.assertIsNone(INSTRUCTION_VARIANTS["default"])

    def test_provenance_aware_mentions_artifact_ids(self):
        text = INSTRUCTION_VARIANTS["provenance_aware"]
        self.assertIn("artifact ID", text)
        self.assertIn("source_ref", text)

    def test_minimal_is_short(self):
        text = INSTRUCTION_VARIANTS["minimal"]
        self.assertLess(len(text), 100)


class TestThresholdLevels(unittest.TestCase):
    """Test threshold level definitions."""

    def test_three_thresholds(self):
        self.assertEqual(len(THRESHOLD_LEVELS), 3)

    def test_threshold_values(self):
        self.assertEqual(THRESHOLD_LEVELS, [50_000, 80_000, 120_000])

    def test_thresholds_ascending(self):
        self.assertEqual(THRESHOLD_LEVELS, sorted(THRESHOLD_LEVELS))


class TestConditionGeneration(unittest.TestCase):
    """Test ablation condition matrix generation."""

    def setUp(self):
        self.runner = AblationRunner(dry_run=True)

    def test_generates_9_conditions(self):
        conditions = self.runner.generate_conditions()
        self.assertEqual(len(conditions), 9)

    def test_all_condition_ids_unique(self):
        conditions = self.runner.generate_conditions()
        ids = [c.condition_id for c in conditions]
        self.assertEqual(len(ids), len(set(ids)))

    def test_condition_ids_descriptive(self):
        conditions = self.runner.generate_conditions()
        for c in conditions:
            # Each ID should contain instruction variant, threshold, and model
            self.assertTrue(c.condition_id.startswith("C-"))
            self.assertIn("K", c.condition_id)  # threshold in K notation

    def test_all_instruction_variants_present(self):
        conditions = self.runner.generate_conditions()
        instr_in_conditions = set()
        for c in conditions:
            if c.instructions is None:
                instr_in_conditions.add("default")
            elif "provenance" in (c.instructions or "").lower():
                instr_in_conditions.add("provenance_aware")
            else:
                instr_in_conditions.add("minimal")
        self.assertEqual(instr_in_conditions, {"default", "provenance_aware", "minimal"})

    def test_all_thresholds_present(self):
        conditions = self.runner.generate_conditions()
        thresholds_in_conditions = {c.threshold for c in conditions}
        self.assertEqual(thresholds_in_conditions, set(THRESHOLD_LEVELS))

    def test_3_conditions_per_threshold(self):
        conditions = self.runner.generate_conditions()
        for threshold in THRESHOLD_LEVELS:
            count = sum(1 for c in conditions if c.threshold == threshold)
            self.assertEqual(count, 3, f"Expected 3 conditions for threshold {threshold}")

    def test_3_conditions_per_instruction(self):
        conditions = self.runner.generate_conditions()
        for instr_name, instr_text in INSTRUCTION_VARIANTS.items():
            count = sum(1 for c in conditions if c.instructions == instr_text)
            self.assertEqual(count, 3, f"Expected 3 conditions for instruction '{instr_name}'")

    def test_opus_conditions_separate(self):
        runner = AblationRunner(dry_run=True, include_opus=True)
        all_conditions = runner.generate_all_conditions()
        self.assertEqual(len(all_conditions), 18)  # 9 Sonnet + 9 Opus

    def test_condition_model_matches(self):
        conditions = self.runner.generate_conditions()
        for c in conditions:
            self.assertEqual(c.model, "claude-sonnet-4-20250514")


class TestSingleConditionDryRun(unittest.TestCase):
    """Test dry-run execution of a single condition."""

    def test_single_condition_produces_results(self):
        runner = AblationRunner(dry_run=True)
        conditions = runner.generate_conditions()
        config = conditions[0]
        results = runner.run_condition(config, n_trials=1)
        self.assertEqual(len(results), 1)

    def test_trial_result_has_metrics(self):
        runner = AblationRunner(dry_run=True)
        conditions = runner.generate_conditions()
        config = conditions[0]
        results = runner.run_condition(config, n_trials=1)
        result = results[0]
        self.assertIn("structural_reachability", result.aggregate_metrics)
        self.assertIn("artifact_id_survival", result.aggregate_metrics)
        self.assertIn("semantic_fidelity", result.aggregate_metrics)
        self.assertIn("compression_ratio", result.aggregate_metrics)
        self.assertIn("degraded_fraction", result.aggregate_metrics)

    def test_metrics_in_valid_ranges(self):
        runner = AblationRunner(dry_run=True)
        conditions = runner.generate_conditions()
        config = conditions[0]
        results = runner.run_condition(config, n_trials=1)
        metrics = results[0].aggregate_metrics
        self.assertGreaterEqual(metrics["structural_reachability"], 0.0)
        self.assertLessEqual(metrics["structural_reachability"], 1.0)
        self.assertGreaterEqual(metrics["artifact_id_survival"], 0.0)
        self.assertLessEqual(metrics["artifact_id_survival"], 1.0)
        self.assertGreater(metrics["compression_ratio"], 0.0)


class TestAggregation(unittest.TestCase):
    """Test metric aggregation with known inputs."""

    def _make_trial_result(self, survival: float, reachability: float) -> TrialResult:
        """Create a mock TrialResult with known metrics."""
        return TrialResult(
            trial_id="test-trial",
            track="C",
            task_category="coding",
            model="claude-sonnet-4-20250514",
            mode="dry-run",
            provenance_aware=False,
            threshold=80000,
            num_iterations=20,
            compaction_events=[],
            aggregate_metrics={
                "structural_reachability": reachability,
                "artifact_id_survival": survival,
                "semantic_fidelity": 0.5,
                "compression_ratio": 100.0,
                "degraded_fraction": 0.2,
            },
            trace_stats={},
            chamber_validation=[],
            timestamp="2026-01-01T00:00:00Z",
        )

    def test_aggregation_mean(self):
        results = [
            self._make_trial_result(0.4, 0.4),
            self._make_trial_result(0.6, 0.6),
            self._make_trial_result(0.5, 0.5),
        ]
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition(results)
        self.assertAlmostEqual(
            summary.metrics["artifact_id_survival"]["mean"], 0.5, places=4
        )

    def test_aggregation_std(self):
        results = [
            self._make_trial_result(0.4, 0.4),
            self._make_trial_result(0.6, 0.6),
            self._make_trial_result(0.5, 0.5),
        ]
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition(results)
        expected_std = statistics.stdev([0.4, 0.6, 0.5])
        self.assertAlmostEqual(
            summary.metrics["artifact_id_survival"]["std"], expected_std, places=4
        )

    def test_aggregation_ci(self):
        results = [
            self._make_trial_result(0.4, 0.4),
            self._make_trial_result(0.6, 0.6),
            self._make_trial_result(0.5, 0.5),
        ]
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition(results)
        metrics = summary.metrics["artifact_id_survival"]
        self.assertLess(metrics["ci_lower"], metrics["mean"])
        self.assertGreater(metrics["ci_upper"], metrics["mean"])

    def test_aggregation_empty_results(self):
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition([])
        self.assertEqual(summary.n_trials, 0)
        self.assertEqual(summary.metrics, {})

    def test_aggregation_single_result(self):
        results = [self._make_trial_result(0.5, 0.5)]
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition(results)
        self.assertEqual(summary.n_trials, 1)
        self.assertAlmostEqual(
            summary.metrics["artifact_id_survival"]["mean"], 0.5, places=4
        )
        # Std should be 0 for single result
        self.assertAlmostEqual(
            summary.metrics["artifact_id_survival"]["std"], 0.0, places=4
        )

    def test_raw_values_stored(self):
        results = [
            self._make_trial_result(0.3, 0.3),
            self._make_trial_result(0.7, 0.7),
        ]
        runner = AblationRunner(dry_run=True)
        summary = runner.aggregate_condition(results)
        self.assertEqual(summary.raw_values["artifact_id_survival"], [0.3, 0.7])


class TestDeltaComputation(unittest.TestCase):
    """Test provenance_aware_delta and threshold effect computation."""

    def _make_summary(self, cid: str, survival_vals: list[float]) -> ConditionSummary:
        """Create a ConditionSummary with known survival values."""
        mean_val = statistics.mean(survival_vals)
        std_val = statistics.stdev(survival_vals) if len(survival_vals) > 1 else 0.0
        ci_l, ci_u = _compute_ci(survival_vals)
        return ConditionSummary(
            condition_id=cid,
            n_trials=len(survival_vals),
            metrics={
                "artifact_id_survival": {
                    "mean": mean_val,
                    "std": std_val,
                    "ci_lower": ci_l,
                    "ci_upper": ci_u,
                },
                "structural_reachability": {
                    "mean": mean_val,
                    "std": std_val,
                    "ci_lower": ci_l,
                    "ci_upper": ci_u,
                },
            },
            raw_values={
                "artifact_id_survival": survival_vals,
                "structural_reachability": survival_vals,
            },
        )

    def test_provenance_aware_delta_positive(self):
        """provenance_aware should survive better than default."""
        summaries = {
            "C-default-80K-sonnet": self._make_summary(
                "C-default-80K-sonnet", [0.3, 0.4, 0.35, 0.45, 0.4]
            ),
            "C-provenance_aware-80K-sonnet": self._make_summary(
                "C-provenance_aware-80K-sonnet", [0.7, 0.8, 0.75, 0.85, 0.8]
            ),
            "C-minimal-80K-sonnet": self._make_summary(
                "C-minimal-80K-sonnet", [0.2, 0.3, 0.25, 0.35, 0.3]
            ),
        }
        runner = AblationRunner(dry_run=True)
        deltas = runner.compute_deltas(summaries)
        prov_delta = deltas["instruction_effect"]["provenance_aware_delta"]["80K"]
        self.assertGreater(prov_delta["delta"], 0.0)

    def test_delta_sign_correct(self):
        """delta = provenance_aware - default, should be positive when prov > default."""
        summaries = {
            "C-default-80K-sonnet": self._make_summary(
                "C-default-80K-sonnet", [0.3, 0.3, 0.3, 0.3, 0.3]
            ),
            "C-provenance_aware-80K-sonnet": self._make_summary(
                "C-provenance_aware-80K-sonnet", [0.8, 0.8, 0.8, 0.8, 0.8]
            ),
            "C-minimal-80K-sonnet": self._make_summary(
                "C-minimal-80K-sonnet", [0.2, 0.2, 0.2, 0.2, 0.2]
            ),
        }
        runner = AblationRunner(dry_run=True)
        deltas = runner.compute_deltas(summaries)
        prov_delta = deltas["instruction_effect"]["provenance_aware_delta"]["80K"]
        self.assertAlmostEqual(prov_delta["delta"], 0.5, places=3)

    def test_threshold_effect_computed(self):
        """Threshold effect should be computed for each instruction variant."""
        summaries = {}
        for instr_name in INSTRUCTION_VARIANTS:
            for threshold in THRESHOLD_LEVELS:
                t_short = f"{threshold // 1000}K"
                cid = f"C-{instr_name}-{t_short}-sonnet"
                # Higher threshold -> slightly better survival (simulated)
                base = 0.5 + (threshold - 80000) / 400000
                summaries[cid] = self._make_summary(
                    cid, [base, base + 0.05, base - 0.05]
                )
        runner = AblationRunner(dry_run=True)
        deltas = runner.compute_deltas(summaries)
        self.assertIn("threshold_effect", deltas)
        for instr_name in INSTRUCTION_VARIANTS:
            self.assertIn(instr_name, deltas["threshold_effect"])

    def test_pairwise_comparisons_present(self):
        """Pairwise comparisons should be present in instruction_effect."""
        summaries = {
            "C-default-80K-sonnet": self._make_summary(
                "C-default-80K-sonnet", [0.3, 0.4, 0.35]
            ),
            "C-provenance_aware-80K-sonnet": self._make_summary(
                "C-provenance_aware-80K-sonnet", [0.7, 0.8, 0.75]
            ),
            "C-minimal-80K-sonnet": self._make_summary(
                "C-minimal-80K-sonnet", [0.2, 0.3, 0.25]
            ),
        }
        runner = AblationRunner(dry_run=True)
        deltas = runner.compute_deltas(summaries)
        pairwise = deltas["instruction_effect"]["pairwise"]["80K"]
        self.assertEqual(len(pairwise), 3)  # 3 pairs


class TestBonferroniCorrection(unittest.TestCase):
    """Test Bonferroni multiple comparison correction."""

    def test_bonferroni_multiplies_by_n(self):
        corrected = _bonferroni_correct([0.01, 0.02, 0.03], n_comparisons=3)
        self.assertAlmostEqual(corrected[0], 0.03)
        self.assertAlmostEqual(corrected[1], 0.06)
        self.assertAlmostEqual(corrected[2], 0.09)

    def test_bonferroni_caps_at_1(self):
        corrected = _bonferroni_correct([0.5, 0.8, 0.9], n_comparisons=3)
        self.assertLessEqual(corrected[0], 1.0)
        self.assertLessEqual(corrected[1], 1.0)
        self.assertEqual(corrected[2], 1.0)

    def test_bonferroni_alpha_threshold(self):
        """With 3 comparisons, corrected alpha = 0.05/3 = 0.0167."""
        corrected_alpha = 0.05 / 3
        self.assertAlmostEqual(corrected_alpha, 0.0167, places=3)

    def test_bonferroni_empty(self):
        corrected = _bonferroni_correct([], n_comparisons=3)
        self.assertEqual(corrected, [])

    def test_significant_after_correction(self):
        """p=0.01 should remain significant after Bonferroni with 3 comparisons."""
        corrected = _bonferroni_correct([0.01], n_comparisons=3)
        self.assertLess(corrected[0], 0.05)  # 0.03 < 0.05

    def test_not_significant_after_correction(self):
        """p=0.03 should NOT remain significant after Bonferroni with 3 comparisons."""
        corrected = _bonferroni_correct([0.03], n_comparisons=3)
        self.assertGreater(corrected[0], 0.05)  # 0.09 > 0.05


class TestBootstrapPermutationTest(unittest.TestCase):
    """Test bootstrap permutation test for between-group comparisons."""

    def test_identical_groups_high_p(self):
        """Identical groups should produce high p-value."""
        a = [0.5, 0.5, 0.5, 0.5, 0.5]
        b = [0.5, 0.5, 0.5, 0.5, 0.5]
        p = _bootstrap_permutation_test(a, b, n_permutations=1000)
        self.assertGreater(p, 0.5)

    def test_very_different_groups_low_p(self):
        """Very different groups should produce low p-value."""
        a = [0.1, 0.1, 0.1, 0.1, 0.1]
        b = [0.9, 0.9, 0.9, 0.9, 0.9]
        p = _bootstrap_permutation_test(a, b, n_permutations=1000)
        self.assertLess(p, 0.01)

    def test_empty_groups_return_1(self):
        p = _bootstrap_permutation_test([], [1.0, 2.0], n_permutations=100)
        self.assertEqual(p, 1.0)

    def test_deterministic_with_seed(self):
        a = [0.3, 0.4, 0.5]
        b = [0.6, 0.7, 0.8]
        p1 = _bootstrap_permutation_test(a, b, seed=42)
        p2 = _bootstrap_permutation_test(a, b, seed=42)
        self.assertEqual(p1, p2)


class TestComputeCI(unittest.TestCase):
    """Test confidence interval computation."""

    def test_single_value(self):
        ci_lower, ci_upper = _compute_ci([0.5])
        self.assertEqual(ci_lower, 0.5)
        self.assertEqual(ci_upper, 0.5)

    def test_ci_contains_mean(self):
        values = [0.3, 0.4, 0.5, 0.6, 0.7]
        ci_lower, ci_upper = _compute_ci(values)
        mean_val = statistics.mean(values)
        self.assertLess(ci_lower, mean_val)
        self.assertGreater(ci_upper, mean_val)

    def test_ci_symmetric_around_mean(self):
        values = [0.4, 0.5, 0.6]
        ci_lower, ci_upper = _compute_ci(values)
        mean_val = statistics.mean(values)
        lower_dist = mean_val - ci_lower
        upper_dist = ci_upper - mean_val
        self.assertAlmostEqual(lower_dist, upper_dist, places=4)

    def test_narrower_ci_with_more_data(self):
        few = [0.4, 0.5, 0.6]
        many = [0.4, 0.45, 0.5, 0.55, 0.6, 0.45, 0.5, 0.55, 0.5, 0.5]
        ci_few = _compute_ci(few)
        ci_many = _compute_ci(many)
        width_few = ci_few[1] - ci_few[0]
        width_many = ci_many[1] - ci_many[0]
        self.assertLess(width_many, width_few)


class TestCycleTaskTemplate(unittest.TestCase):
    """Test task template cycling."""

    def test_cycles_through_three_templates(self):
        from task_templates import (
            CodingTaskTemplate,
            DebuggingTaskTemplate,
            SpecificationTaskTemplate,
        )
        categories = set()
        for i in range(3):
            template = _cycle_task_template(i, f"test-{i}")
            categories.add(template.category)
        self.assertEqual(len(categories), 3)

    def test_deterministic_cycling(self):
        t0 = _cycle_task_template(0, "run-0")
        t1 = _cycle_task_template(3, "run-3")
        self.assertEqual(type(t0), type(t1))  # Same position in cycle


class TestFullDryRunAblation(unittest.TestCase):
    """Test full dry-run ablation with N=1 per condition."""

    def test_full_ablation_completes(self):
        runner = AblationRunner(dry_run=True)
        results = runner.run_full_ablation(n_per_condition=1)
        self.assertEqual(len(results.conditions), 9)

    def test_all_conditions_have_metrics(self):
        runner = AblationRunner(dry_run=True)
        results = runner.run_full_ablation(n_per_condition=1)
        for cid, summary in results.conditions.items():
            self.assertIn("artifact_id_survival", summary.metrics)
            self.assertIn("structural_reachability", summary.metrics)
            self.assertGreater(summary.n_trials, 0)

    def test_deltas_computed(self):
        runner = AblationRunner(dry_run=True)
        results = runner.run_full_ablation(n_per_condition=1)
        self.assertIn("instruction_effect", results.deltas)
        self.assertIn("threshold_effect", results.deltas)

    def test_provenance_aware_delta_present(self):
        runner = AblationRunner(dry_run=True)
        results = runner.run_full_ablation(n_per_condition=1)
        instr_effect = results.deltas.get("instruction_effect", {})
        # provenance_aware_delta should exist at each threshold
        prov_delta = instr_effect.get("provenance_aware_delta", {})
        # At least one threshold should have data
        self.assertGreater(len(prov_delta), 0)


class TestExportResults(unittest.TestCase):
    """Test JSON and JSONL export."""

    def test_export_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = AblationRunner(dry_run=True, output_dir=tmpdir)
            results = runner.run_full_ablation(n_per_condition=1)
            runner.export_results(results, path=tmpdir)

            # Check summary JSON exists
            json_files = list(Path(tmpdir).glob("*-summary.json"))
            self.assertEqual(len(json_files), 1)

            # Check conditions JSONL exists
            jsonl_files = list(Path(tmpdir).glob("*-conditions.jsonl"))
            self.assertEqual(len(jsonl_files), 1)

    def test_json_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = AblationRunner(dry_run=True, output_dir=tmpdir)
            results = runner.run_full_ablation(n_per_condition=1)
            runner.export_results(results, path=tmpdir)

            json_file = list(Path(tmpdir).glob("*-summary.json"))[0]
            with open(json_file) as f:
                data = json.load(f)
            self.assertIn("ablation_id", data)
            self.assertIn("conditions", data)
            self.assertEqual(len(data["conditions"]), 9)

    def test_jsonl_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = AblationRunner(dry_run=True, output_dir=tmpdir)
            results = runner.run_full_ablation(n_per_condition=1)
            runner.export_results(results, path=tmpdir)

            jsonl_file = list(Path(tmpdir).glob("*-conditions.jsonl"))[0]
            lines = []
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(json.loads(line))
            self.assertEqual(len(lines), 9)
            for line_data in lines:
                self.assertIn("condition_id", line_data)
                self.assertIn("metrics", line_data)


class TestAblationConfig(unittest.TestCase):
    """Test AblationConfig dataclass."""

    def test_default_trials_per_condition(self):
        config = AblationConfig(
            condition_id="test",
            instructions=None,
            threshold=80000,
            model="claude-sonnet-4-20250514",
        )
        self.assertEqual(config.trials_per_condition, 10)

    def test_to_dict(self):
        config = AblationConfig(
            condition_id="C-default-80K-sonnet",
            instructions=None,
            threshold=80000,
            model="claude-sonnet-4-20250514",
        )
        d = config.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["condition_id"], "C-default-80K-sonnet")
        self.assertIsNone(d["instructions"])


class TestConditionSummaryToDict(unittest.TestCase):
    """Test ConditionSummary serialization."""

    def test_to_dict_includes_metrics(self):
        summary = ConditionSummary(
            condition_id="test",
            n_trials=5,
            metrics={"survival": {"mean": 0.5, "std": 0.1, "ci_lower": 0.4, "ci_upper": 0.6}},
            raw_values={"survival": [0.4, 0.5, 0.5, 0.5, 0.6]},
        )
        d = summary.to_dict()
        self.assertIn("metrics", d)
        self.assertNotIn("raw_values", d)  # raw_values excluded from export


class TestAblationResultsToDict(unittest.TestCase):
    """Test AblationResults serialization."""

    def test_to_dict_structure(self):
        results = AblationResults(
            ablation_id="test-123",
            conditions={},
            deltas={"instruction_effect": {}},
            timestamp="2026-01-01T00:00:00Z",
            config_summary={"n_conditions": 9},
        )
        d = results.to_dict()
        self.assertEqual(d["ablation_id"], "test-123")
        self.assertIn("deltas", d)
        self.assertIn("config_summary", d)


if __name__ == "__main__":
    unittest.main()
