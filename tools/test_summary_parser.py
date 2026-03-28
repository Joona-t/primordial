"""Tests for Summary Parser — LLM Compaction Output Extraction.

Covers all 5 functions in summary_parser.py with synthetic summaries
that model realistic LLM compaction output patterns: prose embedding,
bracket formatting, code blocks, paraphrasing, near-misses, and messy text.

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless; LLM compaction = lossy"
"""

import unittest

from summary_parser import (
    extract_artifact_ids,
    extract_source_refs,
    extract_state_labels,
    parse_summary_provenance,
    classify_ref_tier,
    ARTIFACT_ID_PATTERN,
)
from forge_nulls import V1_ABSENCE_STATES


# --- Synthetic Summary Corpus ---
# 10 synthetic summaries covering extraction edge cases

SUMMARY_PROSE = (
    "In the previous steps, the artifact:run100:stage:builder:r1 was created "
    "by the builder agent. It produced a JSON schema with 12 fields. "
    "Subsequently, artifact:run100:stage:critic:r1 reviewed the output and "
    "approved it with minor suggestions."
)

SUMMARY_BRACKETS = (
    "[PROVENANCE: artifact:run200:stage:builder:r1] "
    "The builder produced authentication middleware. "
    "[PROVENANCE: artifact:run200:stage:critic:r1] "
    "The critic approved with caveats."
)

SUMMARY_CODE_BLOCK = (
    "The following artifacts were produced:\n"
    "```\n"
    "artifact:run300:stage:builder:r1\n"
    "artifact:run300:stage:validator:r1\n"
    "```\n"
    "Both passed validation checks."
)

SUMMARY_DUPLICATES = (
    "artifact:run400:stage:builder:r1 was referenced multiple times. "
    "First in the design phase (artifact:run400:stage:builder:r1) and again "
    "during review. Also artifact:run400:stage:critic:r1 appeared once."
)

SUMMARY_NEAR_MISSES = (
    "The artifact_id field was set to 'builder_output'. "
    "We also saw artifact:incomplete without a revision. "
    "And artifact: with nothing after it. "
    "But artifact:run500:stage:builder:r1 is valid."
)

SUMMARY_EXPLICIT_REFS = (
    "source_ref: artifact:run600:stage:builder:r1 -> artifact:run600:stage:critic:r1 "
    "was established during the review phase. "
    "source_ref: artifact:run600:stage:critic:r1 -> artifact:run600:stage:validator:r1 "
    "was established during validation."
)

SUMMARY_IMPLICIT_REFS = (
    "The critic output was derived from artifact:run700:stage:builder:r1. "
    "The validator was based on artifact:run700:stage:critic:r1. "
    "The final report was built on artifact:run700:stage:validator:r1."
)

SUMMARY_STATE_LABELS = (
    "Three artifacts were not_generated due to timeout. "
    "The configuration was marked as deleted after cleanup. "
    "Two entries remain pruned_recoverable pending manual review. "
    "The status field is unknown for iteration 5. "
    "Output was withheld per policy. "
    "The input was flagged as invalid. "
    "Reference resolution is unresolved. "
    "Stage 3 was not_invoked in this run."
)

SUMMARY_MIXED = (
    "Summary of compaction experiment run 800:\n"
    "[PROVENANCE: artifact:run800:iter:0:r1]\n"
    "Step 1 designed the auth data model. "
    "derived from artifact:run800:iter:0:r1, "
    "artifact:run800:iter:1:r1 implemented JWT middleware. "
    "Some outputs were pruned_recoverable during LLM compaction. "
    "The debug log was marked as deleted."
)

SUMMARY_EMPTY = ""


class TestExtractArtifactIds(unittest.TestCase):
    """Tests for extract_artifact_ids — precision and recall on artifact ID extraction."""

    def test_prose_embedding(self):
        """IDs embedded in natural prose are extracted."""
        ids = extract_artifact_ids(SUMMARY_PROSE)
        self.assertIn("artifact:run100:stage:builder:r1", ids)
        self.assertIn("artifact:run100:stage:critic:r1", ids)
        self.assertEqual(len(ids), 2)

    def test_bracket_formatting(self):
        """IDs in [PROVENANCE: ...] brackets are extracted."""
        ids = extract_artifact_ids(SUMMARY_BRACKETS)
        self.assertIn("artifact:run200:stage:builder:r1", ids)
        self.assertIn("artifact:run200:stage:critic:r1", ids)
        self.assertEqual(len(ids), 2)

    def test_code_block_extraction(self):
        """IDs inside code blocks are extracted."""
        ids = extract_artifact_ids(SUMMARY_CODE_BLOCK)
        self.assertIn("artifact:run300:stage:builder:r1", ids)
        self.assertIn("artifact:run300:stage:validator:r1", ids)
        self.assertEqual(len(ids), 2)

    def test_deduplication_preserves_order(self):
        """Duplicate IDs are removed, first occurrence order preserved."""
        ids = extract_artifact_ids(SUMMARY_DUPLICATES)
        self.assertEqual(ids[0], "artifact:run400:stage:builder:r1")
        self.assertEqual(ids[1], "artifact:run400:stage:critic:r1")
        self.assertEqual(len(ids), 2)

    def test_near_miss_rejection(self):
        """Malformed IDs do not match — zero false positives.

        Precision = 1.0: No false positives allowed.
        - 'artifact_id' (underscore instead of colon) must NOT match
        - 'artifact:incomplete' (no revision) must NOT match
        - 'artifact:' alone must NOT match
        """
        ids = extract_artifact_ids(SUMMARY_NEAR_MISSES)
        # Only the valid ID should match
        self.assertEqual(ids, ["artifact:run500:stage:builder:r1"])

    def test_empty_text(self):
        """Empty text returns empty list."""
        self.assertEqual(extract_artifact_ids(""), [])

    def test_no_artifacts(self):
        """Text with no artifact IDs returns empty list."""
        self.assertEqual(extract_artifact_ids("Just regular text, nothing special."), [])

    def test_iter_format_ids(self):
        """IDs using iter format (from compaction_experiment.py) are extracted."""
        text = "artifact:run100:iter:5:r1 was produced"
        ids = extract_artifact_ids(text)
        self.assertEqual(ids, ["artifact:run100:iter:5:r1"])

    def test_multiple_revision_numbers(self):
        """IDs with different revision numbers are treated as distinct."""
        text = "artifact:run100:stage:builder:r1 and artifact:run100:stage:builder:r2"
        ids = extract_artifact_ids(text)
        self.assertEqual(len(ids), 2)

    def test_precision_is_perfect(self):
        """Precision = 1.0 across entire test corpus — no false positives.

        Acceptance test: test-id-extraction.
        """
        # Collect all extracted IDs from all summaries
        all_summaries = [
            SUMMARY_PROSE, SUMMARY_BRACKETS, SUMMARY_CODE_BLOCK,
            SUMMARY_DUPLICATES, SUMMARY_NEAR_MISSES, SUMMARY_EXPLICIT_REFS,
            SUMMARY_IMPLICIT_REFS, SUMMARY_STATE_LABELS, SUMMARY_MIXED,
            SUMMARY_EMPTY,
        ]
        for summary in all_summaries:
            ids = extract_artifact_ids(summary)
            for aid in ids:
                # Every extracted ID must match the canonical pattern
                self.assertRegex(
                    aid,
                    r'^artifact:[a-zA-Z0-9_][a-zA-Z0-9_.:-]*:r\d+$',
                    f"False positive: {aid!r}",
                )


class TestExtractSourceRefs(unittest.TestCase):
    """Tests for extract_source_refs — provenance relationship extraction."""

    def test_explicit_refs(self):
        """Explicit 'source_ref: X -> Y' patterns extracted."""
        refs = extract_source_refs(SUMMARY_EXPLICIT_REFS)
        self.assertEqual(len(refs), 2)
        self.assertEqual(
            refs[0],
            ("artifact:run600:stage:builder:r1", "artifact:run600:stage:critic:r1"),
        )
        self.assertEqual(
            refs[1],
            ("artifact:run600:stage:critic:r1", "artifact:run600:stage:validator:r1"),
        )

    def test_implicit_refs(self):
        """Implicit 'derived from X' / 'based on X' patterns extracted."""
        refs = extract_source_refs(SUMMARY_IMPLICIT_REFS)
        self.assertEqual(len(refs), 3)
        # All implicit refs have target=None
        for source, target in refs:
            self.assertIsNone(target)
        sources = [r[0] for r in refs]
        self.assertIn("artifact:run700:stage:builder:r1", sources)
        self.assertIn("artifact:run700:stage:critic:r1", sources)
        self.assertIn("artifact:run700:stage:validator:r1", sources)

    def test_mixed_refs(self):
        """Mixed text with implicit refs extracted correctly."""
        refs = extract_source_refs(SUMMARY_MIXED)
        # "derived from artifact:run800:iter:0:r1"
        self.assertTrue(len(refs) >= 1)
        self.assertEqual(refs[0][0], "artifact:run800:iter:0:r1")
        self.assertIsNone(refs[0][1])

    def test_no_refs(self):
        """Text with no ref patterns returns empty list."""
        refs = extract_source_refs("Just some regular text.")
        self.assertEqual(refs, [])

    def test_empty_text(self):
        """Empty text returns empty list."""
        self.assertEqual(extract_source_refs(""), [])

    def test_malformed_refs_rejected(self):
        """Malformed refs do not produce false positive extractions."""
        text = "derived from some idea. Based on nothing. Extending the codebase."
        refs = extract_source_refs(text)
        self.assertEqual(refs, [])


class TestExtractStateLabels(unittest.TestCase):
    """Tests for extract_state_labels — absence state mention detection."""

    def test_all_eight_states_detected(self):
        """All 8 V1_ABSENCE_STATES are correctly identified when present."""
        labels = extract_state_labels(SUMMARY_STATE_LABELS)
        for state in V1_ABSENCE_STATES:
            self.assertIn(
                state, labels,
                f"State '{state}' not found in summary with all states present",
            )
            self.assertGreaterEqual(labels[state], 1)

    def test_state_count_accuracy(self):
        """Count of mentions is accurate for repeated states."""
        text = "unknown unknown unknown and not_generated not_generated"
        labels = extract_state_labels(text)
        self.assertEqual(labels["unknown"], 3)
        self.assertEqual(labels["not_generated"], 2)

    def test_space_form_detected(self):
        """State names with spaces instead of underscores are detected."""
        text = "The artifact was not generated and is pruned recoverable"
        labels = extract_state_labels(text)
        self.assertIn("not_generated", labels)
        self.assertIn("pruned_recoverable", labels)

    def test_no_states_returns_empty(self):
        """Text with no state labels returns empty dict."""
        labels = extract_state_labels("Just regular text about coding.")
        self.assertEqual(labels, {})

    def test_empty_text(self):
        """Empty text returns empty dict."""
        self.assertEqual(extract_state_labels(""), {})

    def test_partial_matches_rejected(self):
        """Partial matches like 'unknown_entity' should not match 'unknown'."""
        # 'unknownly' contains 'unknown' but should not match as word boundary
        text = "The unknownly formatted output was strange."
        labels = extract_state_labels(text)
        # 'unknown' should NOT match since 'unknownly' is not 'unknown'
        self.assertNotIn("unknown", labels)


class TestParseSummaryProvenance(unittest.TestCase):
    """Tests for parse_summary_provenance — unified extraction."""

    def test_returns_all_fields(self):
        """Unified parser returns all expected keys."""
        result = parse_summary_provenance(SUMMARY_MIXED)
        self.assertIn("artifact_ids", result)
        self.assertIn("source_refs", result)
        self.assertIn("state_labels", result)
        self.assertIn("provenance_density", result)

    def test_provenance_density_calculation(self):
        """Provenance density = artifact_mentions / total_tokens."""
        # Create controlled text: 10 tokens, 2 artifact mentions
        text = (
            "The artifact:run100:stage:builder:r1 and "
            "artifact:run100:stage:critic:r1 were created today"
        )
        result = parse_summary_provenance(text)
        tokens = text.split()
        total_mentions = len(ARTIFACT_ID_PATTERN.findall(text))
        expected_density = total_mentions / len(tokens)
        self.assertAlmostEqual(result["provenance_density"], expected_density, places=5)

    def test_empty_text_density_zero(self):
        """Empty text has provenance density of 0."""
        result = parse_summary_provenance("")
        self.assertEqual(result["provenance_density"], 0.0)
        self.assertEqual(result["artifact_ids"], [])

    def test_mixed_summary_complete(self):
        """Mixed summary extracts all types of provenance metadata."""
        result = parse_summary_provenance(SUMMARY_MIXED)
        self.assertTrue(len(result["artifact_ids"]) >= 2)
        self.assertTrue(len(result["source_refs"]) >= 1)
        self.assertIn("pruned_recoverable", result["state_labels"])
        self.assertIn("deleted", result["state_labels"])
        self.assertGreater(result["provenance_density"], 0)


class TestClassifyRefTier(unittest.TestCase):
    """Tests for classify_ref_tier — three-tier ref classification."""

    def test_resolved_tier(self):
        """ID present + high similarity = resolved."""
        summary = (
            "The builder produced output including all 12 fields. "
            "artifact:run100:stage:builder:r1 created the JSON schema "
            "with name, email, address, phone, and 8 optional metadata fields. "
            "Validation passed with no errors."
        )
        original = (
            "The builder produced output including all 12 fields. "
            "Created the JSON schema with name, email, address, phone, "
            "and 8 optional metadata fields. Validation passed with no errors."
        )
        # Use a similarity function that returns high similarity for near-matches
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            summary,
            original,
            similarity_fn=lambda a, b: 0.95,
        )
        self.assertEqual(tier, "resolved")

    def test_degraded_tier(self):
        """ID present + low similarity = degraded."""
        summary = (
            "artifact:run100:stage:builder:r1 — builder created some output"
        )
        original = (
            "The builder agent produced a comprehensive JSON schema with "
            "12 fields including name, email, address, phone, and 8 optional "
            "metadata fields. Validation passed with no errors."
        )
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            summary,
            original,
            similarity_fn=lambda a, b: 0.75,
        )
        self.assertEqual(tier, "degraded")

    def test_broken_tier(self):
        """ID not present = broken (regardless of content similarity)."""
        summary = "The builder created some output. No artifact IDs preserved."
        original = "Original content here."
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            summary,
            original,
            similarity_fn=lambda a, b: 1.0,
        )
        self.assertEqual(tier, "broken")

    def test_fallback_similarity(self):
        """Without similarity_fn, uses Jaccard as fallback."""
        # Identical text should give high Jaccard -> resolved
        text = (
            "artifact:run100:stage:builder:r1 produced a JSON schema "
            "with 12 fields including name email address phone"
        )
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            text,
            text,
            similarity_fn=None,
        )
        self.assertEqual(tier, "resolved")

    def test_broken_with_no_similarity_fn(self):
        """Broken tier works without similarity_fn too."""
        tier = classify_ref_tier(
            "artifact:run999:stage:ghost:r1",
            "No artifacts here at all.",
            "Original content.",
            similarity_fn=None,
        )
        self.assertEqual(tier, "broken")

    def test_threshold_boundary_resolved(self):
        """Similarity exactly at 0.91 -> resolved."""
        summary = "artifact:run100:stage:builder:r1 was here"
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            summary,
            "original",
            similarity_fn=lambda a, b: 0.91,
        )
        self.assertEqual(tier, "resolved")

    def test_threshold_boundary_degraded(self):
        """Similarity exactly at 0.90 -> degraded (threshold is >0.9, not >=0.9)."""
        summary = "artifact:run100:stage:builder:r1 was here"
        tier = classify_ref_tier(
            "artifact:run100:stage:builder:r1",
            summary,
            "original",
            similarity_fn=lambda a, b: 0.90,
        )
        self.assertEqual(tier, "degraded")


class TestEdgeCases(unittest.TestCase):
    """Edge case tests across all extraction functions."""

    def test_unicode_in_text(self):
        """Unicode characters in surrounding text don't break extraction."""
        text = "The artifact:run100:stage:builder:r1 was created with \u2014 dashes and \u201cspecial\u201d quotes"
        ids = extract_artifact_ids(text)
        self.assertEqual(ids, ["artifact:run100:stage:builder:r1"])

    def test_newlines_and_tabs(self):
        """Whitespace variations don't break extraction."""
        text = "Line1\nartifact:run100:stage:builder:r1\tand more"
        ids = extract_artifact_ids(text)
        self.assertEqual(ids, ["artifact:run100:stage:builder:r1"])

    def test_very_long_text(self):
        """Parser handles large text without errors."""
        text = "filler " * 10000 + "artifact:run100:stage:builder:r1" + " filler" * 10000
        ids = extract_artifact_ids(text)
        self.assertEqual(ids, ["artifact:run100:stage:builder:r1"])

    def test_arrow_unicode_in_source_ref(self):
        """Unicode arrow (→) works in explicit source refs."""
        text = "source_ref: artifact:a:r1 → artifact:b:r1"
        refs = extract_source_refs(text)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0], ("artifact:a:r1", "artifact:b:r1"))


if __name__ == "__main__":
    unittest.main()
