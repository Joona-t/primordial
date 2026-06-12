"""Tests for Semantic Provenance Fidelity (SPF) metric."""

import unittest
from semantic_provenance_fidelity import (
    tokenize,
    jaccard_similarity,
    token_overlap_ratio,
    weighted_token_overlap,
    SPFMetric,
    measure_compaction_fidelity,
)


class TestTokenize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(tokenize("hello world"), ["hello", "world"])

    def test_lowercases(self):
        self.assertEqual(tokenize("Hello WORLD"), ["hello", "world"])

    def test_strips_punctuation(self):
        tokens = tokenize("error: missing 'user_id' key.")
        self.assertIn("error", tokens)
        self.assertIn("user_id", tokens)
        self.assertNotIn(":", tokens)

    def test_empty(self):
        self.assertEqual(tokenize(""), [])


class TestJaccard(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(jaccard_similarity("hello world", "hello world"), 1.0)

    def test_disjoint(self):
        self.assertEqual(jaccard_similarity("hello world", "foo bar"), 0.0)

    def test_partial_overlap(self):
        sim = jaccard_similarity("hello world foo", "hello bar foo")
        # intersection = {hello, foo}, union = {hello, world, foo, bar}
        self.assertAlmostEqual(sim, 2 / 4)

    def test_both_empty(self):
        self.assertEqual(jaccard_similarity("", ""), 1.0)

    def test_one_empty(self):
        self.assertEqual(jaccard_similarity("hello", ""), 0.0)

    def test_symmetric(self):
        a, b = "hello world", "world foo"
        self.assertEqual(jaccard_similarity(a, b), jaccard_similarity(b, a))


class TestTokenOverlap(unittest.TestCase):
    def test_full_preservation(self):
        self.assertEqual(token_overlap_ratio("hello world", "hello world extra"), 1.0)

    def test_partial_loss(self):
        ratio = token_overlap_ratio("hello world foo bar", "hello world")
        self.assertAlmostEqual(ratio, 0.5)

    def test_total_loss(self):
        self.assertEqual(token_overlap_ratio("hello world", "foo bar"), 0.0)

    def test_empty_original(self):
        self.assertEqual(token_overlap_ratio("", "anything"), 0.0)


class TestWeightedOverlap(unittest.TestCase):
    def test_identical(self):
        self.assertAlmostEqual(
            weighted_token_overlap("hello world", "hello world"), 1.0
        )

    def test_repeated_tokens_weight_more(self):
        # "error error error fix" → error appears 3x, fix 1x
        # If recovered has "error" but not "fix": 3/4 preserved
        ratio = weighted_token_overlap("error error error fix", "error occurred")
        self.assertAlmostEqual(ratio, 3 / 4)


class TestSPFMetric(unittest.TestCase):
    def setUp(self):
        self.spf = SPFMetric()  # no embedding model

    def test_measure_returns_all_fields(self):
        result = self.spf.measure("hello world", "hello")
        self.assertIn("jaccard", result)
        self.assertIn("token_overlap", result)
        self.assertIn("weighted_overlap", result)
        self.assertIn("content_hash_match", result)
        self.assertIn("original_tokens", result)
        self.assertIn("recovered_tokens", result)

    def test_exact_match_detected(self):
        result = self.spf.measure("exact text", "exact text")
        self.assertEqual(result["content_hash_match"], 1.0)
        self.assertEqual(result["jaccard"], 1.0)

    def test_no_match(self):
        result = self.spf.measure("alpha beta", "gamma delta")
        self.assertEqual(result["content_hash_match"], 0.0)
        self.assertEqual(result["jaccard"], 0.0)

    def test_batch(self):
        pairs = [("a b c", "a b"), ("x y", "x y")]
        results = self.spf.measure_batch(pairs)
        self.assertEqual(len(results), 2)

    def test_aggregate(self):
        measurements = [
            self.spf.measure("hello world foo", "hello world foo"),
            self.spf.measure("alpha beta gamma", "alpha"),
        ]
        agg = self.spf.aggregate(measurements)
        self.assertEqual(agg["count"], 2)
        self.assertIn("jaccard", agg)
        self.assertLessEqual(agg["jaccard"]["mean"], 1.0)
        self.assertGreaterEqual(agg["jaccard"]["min"], 0.0)

    def test_aggregate_empty(self):
        self.assertEqual(self.spf.aggregate([]), {})

    def test_embedding_cosine_none_without_model(self):
        result = self.spf.measure("hello", "hello")
        self.assertIsNone(result["embedding_cosine"])


class TestCompactionFidelity(unittest.TestCase):
    def test_basic_measurement(self):
        chamber = {"chamber_id": "test:chamber:1"}
        originals = {
            "art:1": "The builder produced output.",
            "art:2": "The critic reviewed output.",
        }
        recovered = {
            "art:1": "Builder output produced.",
            "art:2": "The critic reviewed output.",
        }
        result = measure_compaction_fidelity(chamber, originals, recovered)
        self.assertEqual(result["aggregate"]["artifacts_measured"], 2)
        self.assertEqual(result["aggregate"]["artifacts_lost"], 0)
        self.assertIn("art:1", result["per_artifact"])
        self.assertIn("art:2", result["per_artifact"])

    def test_lost_artifacts_tracked(self):
        chamber = {"chamber_id": "test:chamber:2"}
        originals = {"art:1": "text", "art:2": "text", "art:3": "text"}
        recovered = {"art:1": "text"}
        result = measure_compaction_fidelity(chamber, originals, recovered)
        self.assertEqual(result["aggregate"]["artifacts_lost"], 2)
        self.assertAlmostEqual(result["aggregate"]["loss_rate"], 2 / 3, places=3)
        self.assertIn("art:2", result["lost_artifact_ids"])
        self.assertIn("art:3", result["lost_artifact_ids"])

    def test_empty_inputs(self):
        result = measure_compaction_fidelity({}, {}, {})
        self.assertEqual(result["aggregate"]["artifacts_measured"], 0)


if __name__ == "__main__":
    unittest.main()
