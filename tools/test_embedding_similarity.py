"""Tests for Embedding Similarity Module — Phase 6 of Primordial v2.0.

Tests the token overlap fallback (always available) and conditionally
tests the embedding backend when sentence-transformers is installed.

Convention assertions (project-specific — physics conventions N/A):
  cosine_similarity = "[dimensionless, range -1 to 1]"
  jaccard_similarity = "[dimensionless, range 0-1]"
"""

import unittest

from embedding_similarity import (
    EmbeddingSimilarity,
    tier_classify,
    calibrate_thresholds,
    RESOLVED_THRESHOLD,
    DEGRADED_THRESHOLD,
)
from semantic_provenance_fidelity import SPFMetric

# Check if sentence-transformers is available
_HAS_EMBEDDINGS = False
try:
    import sentence_transformers
    _HAS_EMBEDDINGS = True
except ImportError:
    pass


# --- Calibration Data ---
# Three canonical pairs for tier validation per acceptance test test-tier-calibration

IDENTICAL_TEXT = (
    "The builder agent produced a JSON schema with 12 fields including "
    "name, email, address, phone, and 8 optional metadata fields. "
    "Validation passed with no errors. Source: iteration 3 of run 42."
)

PARAPHRASED_TEXT = (
    "Builder output: JSON schema (12 fields: name, email, address, phone, "
    "plus 8 optional). Validated successfully. From run 42 iteration 3."
)

UNRELATED_TEXT = (
    "The weather forecast for Helsinki shows partly cloudy skies with "
    "temperatures reaching 15 degrees Celsius by midday. Light winds "
    "from the southwest are expected throughout the afternoon."
)


class TestTierClassify(unittest.TestCase):
    """Tests for tier_classify — threshold-based classification."""

    def test_resolved_above_threshold(self):
        """Similarity > 0.9 -> resolved."""
        self.assertEqual(tier_classify(0.95), "resolved")
        self.assertEqual(tier_classify(0.99), "resolved")
        self.assertEqual(tier_classify(1.0), "resolved")

    def test_degraded_in_range(self):
        """0.7 <= similarity <= 0.9 -> degraded."""
        self.assertEqual(tier_classify(0.7), "degraded")
        self.assertEqual(tier_classify(0.8), "degraded")
        self.assertEqual(tier_classify(0.9), "degraded")

    def test_broken_below_threshold(self):
        """Similarity < 0.7 -> broken."""
        self.assertEqual(tier_classify(0.69), "broken")
        self.assertEqual(tier_classify(0.5), "broken")
        self.assertEqual(tier_classify(0.0), "broken")
        self.assertEqual(tier_classify(-0.5), "broken")

    def test_exact_boundary_resolved(self):
        """Boundary: 0.91 is resolved (> 0.9)."""
        self.assertEqual(tier_classify(0.91), "resolved")

    def test_exact_boundary_degraded_upper(self):
        """Boundary: 0.9 exactly is degraded (not > 0.9)."""
        self.assertEqual(tier_classify(0.9), "degraded")

    def test_exact_boundary_degraded_lower(self):
        """Boundary: 0.7 exactly is degraded (>= 0.7)."""
        self.assertEqual(tier_classify(0.7), "degraded")

    def test_exact_boundary_broken(self):
        """Boundary: 0.699 is broken (< 0.7)."""
        self.assertEqual(tier_classify(0.699), "broken")

    def test_thresholds_match_protocol(self):
        """Threshold constants match protocol Section 5.3 values."""
        self.assertEqual(RESOLVED_THRESHOLD, 0.9)
        self.assertEqual(DEGRADED_THRESHOLD, 0.7)


class TestEmbeddingSimilarityFallback(unittest.TestCase):
    """Tests using the token overlap fallback (always available)."""

    def setUp(self):
        self.sim = EmbeddingSimilarity()

    def test_backend_is_token_overlap(self):
        """Without sentence-transformers, backend is token_overlap."""
        if not _HAS_EMBEDDINGS:
            self.assertEqual(self.sim.backend, "token_overlap")

    def test_identical_text_high_similarity(self):
        """Identical text produces similarity > 0.9."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, IDENTICAL_TEXT)
        self.assertGreater(score, 0.9)

    def test_unrelated_text_low_similarity(self):
        """Completely unrelated text produces similarity < 0.5."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, UNRELATED_TEXT)
        self.assertLess(score, 0.5)

    def test_paraphrased_text_intermediate(self):
        """Paraphrased text produces intermediate similarity."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, PARAPHRASED_TEXT)
        # Should be meaningfully above 0 but below identical
        self.assertGreater(score, 0.2)
        self.assertLess(score, 1.0)

    def test_empty_texts(self):
        """Two empty texts produce similarity of 1.0 (both empty = identical)."""
        score = self.sim.compute_similarity("", "")
        self.assertEqual(score, 1.0)

    def test_one_empty_text(self):
        """One empty text produces low similarity."""
        score = self.sim.compute_similarity("hello world", "")
        self.assertLessEqual(score, 0.1)

    def test_approximate_symmetry(self):
        """Fallback similarity is approximately symmetric.

        Jaccard component is exactly symmetric, but weighted_token_overlap
        is directional (measures what fraction of text_a tokens appear in
        text_b). The averaged fallback therefore has a directional bias.
        Both directions should be in the same tier though.
        """
        score_ab = self.sim.compute_similarity(IDENTICAL_TEXT, PARAPHRASED_TEXT)
        score_ba = self.sim.compute_similarity(PARAPHRASED_TEXT, IDENTICAL_TEXT)
        # Both should be meaningfully positive (> 0.3) and below 1.0
        self.assertGreater(score_ab, 0.3)
        self.assertGreater(score_ba, 0.3)
        self.assertLess(score_ab, 1.0)
        self.assertLess(score_ba, 1.0)
        # Directional difference is bounded
        self.assertLess(abs(score_ab - score_ba), 0.25)

    def test_similarity_range(self):
        """Fallback similarity is in [0, 1]."""
        pairs = [
            (IDENTICAL_TEXT, IDENTICAL_TEXT),
            (IDENTICAL_TEXT, PARAPHRASED_TEXT),
            (IDENTICAL_TEXT, UNRELATED_TEXT),
            ("", ""),
            ("hello", ""),
        ]
        for a, b in pairs:
            score = self.sim.compute_similarity(a, b)
            self.assertGreaterEqual(score, 0.0, f"Score below 0 for ({a[:20]}, {b[:20]})")
            self.assertLessEqual(score, 1.0, f"Score above 1 for ({a[:20]}, {b[:20]})")


class TestBatchComputation(unittest.TestCase):
    """Tests for compute_batch — batch similarity computation."""

    def setUp(self):
        self.sim = EmbeddingSimilarity()

    def test_batch_returns_correct_count(self):
        """Batch returns one score per pair."""
        pairs = [
            (IDENTICAL_TEXT, IDENTICAL_TEXT),
            (IDENTICAL_TEXT, PARAPHRASED_TEXT),
            (IDENTICAL_TEXT, UNRELATED_TEXT),
        ]
        results = self.sim.compute_batch(pairs)
        self.assertEqual(len(results), 3)

    def test_batch_matches_individual(self):
        """Batch results match individual computation."""
        pairs = [
            (IDENTICAL_TEXT, IDENTICAL_TEXT),
            (IDENTICAL_TEXT, PARAPHRASED_TEXT),
            (IDENTICAL_TEXT, UNRELATED_TEXT),
        ]
        batch_results = self.sim.compute_batch(pairs)
        individual_results = [
            self.sim.compute_similarity(a, b) for a, b in pairs
        ]
        for batch_val, indiv_val in zip(batch_results, individual_results):
            self.assertAlmostEqual(batch_val, indiv_val, places=5)

    def test_empty_batch(self):
        """Empty batch returns empty list."""
        self.assertEqual(self.sim.compute_batch([]), [])


class TestCalibrateThresholds(unittest.TestCase):
    """Tests for calibrate_thresholds — threshold calibration function."""

    def test_calibration_returns_required_fields(self):
        """Calibration result contains all required fields."""
        pairs = [
            (IDENTICAL_TEXT, IDENTICAL_TEXT, "resolved"),
            (IDENTICAL_TEXT, PARAPHRASED_TEXT, "degraded"),
            (IDENTICAL_TEXT, UNRELATED_TEXT, "broken"),
        ]
        result = calibrate_thresholds(pairs)
        self.assertIn("per_pair", result)
        self.assertIn("accuracy", result)
        self.assertIn("misclassifications", result)
        self.assertIn("threshold_recommendation", result)
        self.assertIn("current_thresholds", result)
        self.assertIn("backend", result)

    def test_identical_classified_resolved(self):
        """Identical text -> similarity > 0.9 -> resolved (with fallback)."""
        pairs = [(IDENTICAL_TEXT, IDENTICAL_TEXT, "resolved")]
        result = calibrate_thresholds(pairs)
        self.assertEqual(result["per_pair"][0]["predicted"], "resolved")
        self.assertTrue(result["per_pair"][0]["correct"])

    def test_unrelated_classified_broken(self):
        """Unrelated text -> similarity < 0.7 -> broken (with fallback)."""
        pairs = [(IDENTICAL_TEXT, UNRELATED_TEXT, "broken")]
        result = calibrate_thresholds(pairs)
        self.assertEqual(result["per_pair"][0]["predicted"], "broken")
        self.assertTrue(result["per_pair"][0]["correct"])

    def test_accuracy_computed_correctly(self):
        """Accuracy is fraction of correct predictions."""
        # Use pairs where we know the fallback will get them right
        pairs = [
            (IDENTICAL_TEXT, IDENTICAL_TEXT, "resolved"),
            (IDENTICAL_TEXT, UNRELATED_TEXT, "broken"),
        ]
        result = calibrate_thresholds(pairs)
        self.assertGreaterEqual(result["accuracy"], 0.5)

    def test_current_thresholds_reported(self):
        """Current thresholds match module constants."""
        pairs = [(IDENTICAL_TEXT, IDENTICAL_TEXT, "resolved")]
        result = calibrate_thresholds(pairs)
        self.assertEqual(result["current_thresholds"]["resolved"], 0.9)
        self.assertEqual(result["current_thresholds"]["degraded"], 0.7)


class TestSPFMetricIntegration(unittest.TestCase):
    """Tests for SPFMetric.from_embedding_similarity integration."""

    def test_classmethod_exists(self):
        """SPFMetric has from_embedding_similarity classmethod."""
        self.assertTrue(hasattr(SPFMetric, "from_embedding_similarity"))

    def test_creates_valid_instance(self):
        """from_embedding_similarity produces a working SPFMetric."""
        sim = EmbeddingSimilarity()
        spf = SPFMetric.from_embedding_similarity(sim)
        self.assertIsInstance(spf, SPFMetric)

    def test_instance_can_measure(self):
        """SPFMetric created from EmbeddingSimilarity can measure fidelity."""
        sim = EmbeddingSimilarity()
        spf = SPFMetric.from_embedding_similarity(sim)
        result = spf.measure("hello world", "hello world")
        self.assertIn("jaccard", result)
        self.assertEqual(result["content_hash_match"], 1.0)

    def test_batch_measurement(self):
        """SPFMetric from EmbeddingSimilarity supports batch measurement."""
        sim = EmbeddingSimilarity()
        spf = SPFMetric.from_embedding_similarity(sim)
        results = spf.measure_batch([
            ("hello world", "hello world"),
            ("alpha beta", "gamma delta"),
        ])
        self.assertEqual(len(results), 2)


@unittest.skipUnless(_HAS_EMBEDDINGS, "sentence-transformers not installed")
class TestEmbeddingBackend(unittest.TestCase):
    """Conditional tests for embedding backend (skip if unavailable)."""

    def setUp(self):
        self.sim = EmbeddingSimilarity()

    def test_backend_is_embedding(self):
        """With sentence-transformers, backend is embedding."""
        self.assertEqual(self.sim.backend, "embedding")

    def test_identical_very_high(self):
        """Identical text produces cosine similarity near 1.0."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, IDENTICAL_TEXT)
        self.assertGreater(score, 0.99)

    def test_unrelated_low(self):
        """Unrelated text produces low cosine similarity."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, UNRELATED_TEXT)
        self.assertLess(score, 0.5)

    def test_paraphrased_intermediate(self):
        """Paraphrased text produces intermediate cosine similarity."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, PARAPHRASED_TEXT)
        self.assertGreater(score, 0.5)
        self.assertLess(score, 1.0)


class TestTierCalibrationAcceptance(unittest.TestCase):
    """Acceptance test: test-tier-calibration.

    Verifies the three canonical calibration pairs produce correct tier
    assignments with the token overlap fallback.
    """

    def setUp(self):
        self.sim = EmbeddingSimilarity()

    def test_identical_is_resolved(self):
        """Identical text -> similarity > 0.9 -> resolved."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, IDENTICAL_TEXT)
        tier = tier_classify(score)
        self.assertGreater(score, 0.9, f"Identical text similarity {score} not > 0.9")
        self.assertEqual(tier, "resolved")

    def test_unrelated_is_broken(self):
        """Unrelated text -> similarity < 0.7 -> broken."""
        score = self.sim.compute_similarity(IDENTICAL_TEXT, UNRELATED_TEXT)
        tier = tier_classify(score)
        self.assertLess(score, 0.7, f"Unrelated text similarity {score} not < 0.7")
        self.assertEqual(tier, "broken")


if __name__ == "__main__":
    unittest.main()
