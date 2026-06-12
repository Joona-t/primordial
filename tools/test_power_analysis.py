"""Tests for power_analysis.py — statistical correctness verification."""

import unittest
from power_analysis import (
    clopper_pearson_upper,
    clopper_pearson_lower,
    sample_size_for_upper_bound,
    power_to_detect,
    sample_size_for_power,
    generate_power_table,
)


class TestClopperPearson(unittest.TestCase):
    """Verify Clopper-Pearson intervals match known values."""

    def test_v1_baseline_matches(self):
        """v1.0 reported 0/30 → CP upper bound 11.6%."""
        ub = clopper_pearson_upper(0, 30)
        self.assertAlmostEqual(ub, 0.1157, places=3)

    def test_zero_of_zero_is_one(self):
        """Edge case: k=n should give upper bound of 1.0."""
        self.assertEqual(clopper_pearson_upper(5, 5), 1.0)

    def test_lower_bound_zero_violations(self):
        """Lower bound with 0 violations is always 0."""
        self.assertEqual(clopper_pearson_lower(0, 100), 0.0)

    def test_upper_bound_decreases_with_n(self):
        """More runs with 0 violations tightens the bound."""
        ub_30 = clopper_pearson_upper(0, 30)
        ub_100 = clopper_pearson_upper(0, 100)
        ub_200 = clopper_pearson_upper(0, 200)
        self.assertGreater(ub_30, ub_100)
        self.assertGreater(ub_100, ub_200)

    def test_bounds_bracket_true_value(self):
        """For known proportion, CI should bracket it most of the time."""
        # 50/100 = 0.5 true rate
        lower = clopper_pearson_lower(50, 100)
        upper = clopper_pearson_upper(50, 100)
        self.assertLess(lower, 0.5)
        self.assertGreater(upper, 0.5)

    def test_v2_target_200_runs(self):
        """200 runs with 0 violations → ~1.8% upper bound."""
        ub = clopper_pearson_upper(0, 200)
        self.assertLess(ub, 0.02)  # below 2%
        self.assertGreater(ub, 0.01)  # above 1%


class TestSampleSize(unittest.TestCase):
    """Verify sample size computations."""

    def test_bound_10_pct(self):
        """Need ~36 runs for 10% CP upper bound."""
        n = sample_size_for_upper_bound(0.10)
        self.assertLessEqual(n, 40)
        self.assertGreaterEqual(n, 30)

    def test_bound_5_pct(self):
        """Need ~72 runs for 5% CP upper bound."""
        n = sample_size_for_upper_bound(0.05)
        self.assertLessEqual(n, 80)
        self.assertGreaterEqual(n, 60)

    def test_bound_2_pct(self):
        """Need ~183 runs for 2% CP upper bound."""
        n = sample_size_for_upper_bound(0.02)
        self.assertLessEqual(n, 200)
        self.assertGreaterEqual(n, 150)

    def test_achieved_bound_is_below_target(self):
        """The actual bound at computed N must be <= target."""
        for target in [0.10, 0.05, 0.03, 0.02, 0.01]:
            n = sample_size_for_upper_bound(target)
            actual = clopper_pearson_upper(0, n)
            self.assertLessEqual(actual, target,
                                 f"At n={n}, actual UB {actual:.4f} > target {target}")


class TestPower(unittest.TestCase):
    """Verify power computations."""

    def test_power_increases_with_n(self):
        """More runs = more power."""
        p1 = power_to_detect(0.05, 30)
        p2 = power_to_detect(0.05, 100)
        p3 = power_to_detect(0.05, 200)
        self.assertLess(p1, p2)
        self.assertLess(p2, p3)

    def test_power_increases_with_rate(self):
        """Higher true rate = easier to detect."""
        p1 = power_to_detect(0.01, 100)
        p2 = power_to_detect(0.05, 100)
        p3 = power_to_detect(0.10, 100)
        self.assertLess(p1, p2)
        self.assertLess(p2, p3)

    def test_v1_power_at_5pct(self):
        """v1.0 had ~78% power to detect 5% rate with 30 runs."""
        p = power_to_detect(0.05, 30)
        self.assertAlmostEqual(p, 0.785, places=2)

    def test_v2_power_at_2pct(self):
        """v2.0 target: 200 runs has ~98% power at 2% rate."""
        p = power_to_detect(0.02, 200)
        self.assertGreater(p, 0.95)

    def test_sample_size_for_95_power(self):
        """Need ~59 runs for 95% power at 5% rate."""
        n = sample_size_for_power(0.05, 0.95)
        self.assertLessEqual(n, 65)
        self.assertGreaterEqual(n, 50)

    def test_power_at_computed_n_meets_target(self):
        """Power at computed N must be >= target."""
        for rate in [0.01, 0.02, 0.05, 0.10]:
            for target_power in [0.80, 0.90, 0.95]:
                n = sample_size_for_power(rate, target_power)
                actual = power_to_detect(rate, n)
                self.assertGreaterEqual(actual, target_power,
                                        f"rate={rate}, n={n}: power {actual:.3f} < {target_power}")


class TestGenerateTable(unittest.TestCase):
    """Verify the full table generation."""

    def test_all_sections_present(self):
        results = generate_power_table()
        self.assertIn("upper_bound_if_zero", results)
        self.assertIn("sample_size_for_bound", results)
        self.assertIn("power_matrix", results)
        self.assertIn("sample_size_for_power", results)
        self.assertIn("v1_baseline", results)
        self.assertIn("v2_target", results)

    def test_v1_baseline_correct(self):
        results = generate_power_table()
        self.assertEqual(results["v1_baseline"]["n"], 30)
        self.assertEqual(results["v1_baseline"]["k"], 0)

    def test_v2_target_sensible(self):
        results = generate_power_table()
        v2 = results["v2_target"]
        self.assertEqual(v2["n"], 200)
        self.assertLess(v2["cp_upper_95_if_zero"], 0.02)
        self.assertGreater(v2["power_at_5pct_rate"], 0.99)


if __name__ == "__main__":
    unittest.main()
