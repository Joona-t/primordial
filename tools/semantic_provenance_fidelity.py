"""Semantic Provenance Fidelity (SPF) — measures content preservation through compaction.

This metric bridges the gap between structural reachability (does the ref resolve?)
and semantic correctness (is the content behind the ref faithful to the original?).

SPF is defined as:
    SPF(original, recovered) = cosine_similarity(embed(original), embed(recovered))

where embed() produces a dense vector representation of the text content.

v1.0 only measured structural reachability. SPF addresses the key reviewer question:
"Structural refs survive, but does the MEANING survive?"

This module provides both:
1. A pure-Python token overlap baseline (no dependencies)
2. An embedding-based metric (requires sentence-transformers, optional)
"""

import hashlib
import json
import re
from collections import Counter


# --- Token Overlap Baseline (zero dependencies) ---

def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'\b\w+\b', text.lower())


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between token sets."""
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def token_overlap_ratio(original: str, recovered: str) -> float:
    """Fraction of original tokens preserved in recovered text."""
    orig_tokens = set(tokenize(original))
    recov_tokens = set(tokenize(recovered))
    if not orig_tokens:
        return 1.0 if not recov_tokens else 0.0
    return len(orig_tokens & recov_tokens) / len(orig_tokens)


def weighted_token_overlap(original: str, recovered: str) -> float:
    """TF-weighted overlap — rarer tokens count more."""
    orig_counts = Counter(tokenize(original))
    recov_tokens = set(tokenize(recovered))
    if not orig_counts:
        return 1.0 if not recov_tokens else 0.0

    total_weight = sum(orig_counts.values())
    preserved_weight = sum(
        count for token, count in orig_counts.items()
        if token in recov_tokens
    )
    return preserved_weight / total_weight


# --- SPF Metric ---

class SPFMetric:
    """Semantic Provenance Fidelity measurement.

    Provides multiple fidelity scores between original and recovered content:
    - jaccard: token set overlap (baseline)
    - token_overlap: fraction of original tokens preserved
    - weighted_overlap: TF-weighted token preservation
    - embedding_cosine: embedding cosine similarity (if model loaded)
    - content_hash_match: exact content match via SHA-256
    """

    def __init__(self, embedding_model: str | None = None):
        """Initialize SPF metric.

        Args:
            embedding_model: sentence-transformers model name for embedding-based
                           similarity. None uses token-based metrics only.
        """
        self._embedder = None
        self._model_name = embedding_model
        if embedding_model:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(embedding_model)
            except ImportError:
                pass  # fall back to token-based

    def measure(self, original: str, recovered: str) -> dict:
        """Compute all SPF metrics between original and recovered text.

        Args:
            original: The original artifact text before compaction
            recovered: The text recovered via provenance refs after compaction

        Returns:
            dict with metric names and scores (all in [0, 1])
        """
        result = {
            "jaccard": jaccard_similarity(original, recovered),
            "token_overlap": token_overlap_ratio(original, recovered),
            "weighted_overlap": weighted_token_overlap(original, recovered),
            "content_hash_match": 1.0 if _sha256(original) == _sha256(recovered) else 0.0,
            "original_tokens": len(tokenize(original)),
            "recovered_tokens": len(tokenize(recovered)),
            "embedding_cosine": None,
        }

        if self._embedder is not None:
            import numpy as np
            embeddings = self._embedder.encode([original, recovered])
            cosine = float(np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            ))
            result["embedding_cosine"] = round(cosine, 6)

        return result

    def measure_batch(self, pairs: list[tuple[str, str]]) -> list[dict]:
        """Measure SPF for multiple original/recovered pairs."""
        return [self.measure(orig, recov) for orig, recov in pairs]

    def aggregate(self, measurements: list[dict]) -> dict:
        """Compute aggregate SPF statistics over a batch of measurements."""
        if not measurements:
            return {}

        metrics = ["jaccard", "token_overlap", "weighted_overlap"]
        if any(m.get("embedding_cosine") is not None for m in measurements):
            metrics.append("embedding_cosine")

        agg = {"count": len(measurements)}
        for metric in metrics:
            values = [m[metric] for m in measurements if m.get(metric) is not None]
            if values:
                agg[metric] = {
                    "mean": round(sum(values) / len(values), 4),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "n": len(values),
                }

        exact_matches = sum(1 for m in measurements if m["content_hash_match"] == 1.0)
        agg["exact_match_rate"] = round(exact_matches / len(measurements), 4)

        return agg


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --- Integration with Forge Chambers ---

def measure_compaction_fidelity(
    chamber: dict,
    original_artifacts: dict[str, str],
    recovered_artifacts: dict[str, str],
    embedding_model: str | None = None,
) -> dict:
    """Measure SPF across all artifacts in a chamber after compaction.

    Args:
        chamber: The forge chamber dict
        original_artifacts: {artifact_id: original_text} before compaction
        recovered_artifacts: {artifact_id: recovered_text} after compaction
        embedding_model: Optional sentence-transformers model

    Returns:
        dict with per-artifact SPF scores and aggregate statistics
    """
    spf = SPFMetric(embedding_model)

    # Match artifacts by ID
    common_ids = set(original_artifacts.keys()) & set(recovered_artifacts.keys())
    lost_ids = set(original_artifacts.keys()) - set(recovered_artifacts.keys())

    per_artifact = {}
    for aid in sorted(common_ids):
        per_artifact[aid] = spf.measure(
            original_artifacts[aid],
            recovered_artifacts[aid]
        )

    measurements = list(per_artifact.values())
    aggregate = spf.aggregate(measurements)
    aggregate["artifacts_measured"] = len(common_ids)
    aggregate["artifacts_lost"] = len(lost_ids)
    aggregate["loss_rate"] = round(len(lost_ids) / max(len(original_artifacts), 1), 4)

    return {
        "per_artifact": per_artifact,
        "aggregate": aggregate,
        "lost_artifact_ids": sorted(lost_ids),
        "chamber_id": chamber.get("chamber_id", "unknown"),
    }


if __name__ == "__main__":
    # Demo: measure SPF on synthetic compaction examples
    spf = SPFMetric()

    examples = [
        (
            "The builder agent produced a JSON schema with 12 fields including "
            "name, email, address, phone, and 8 optional metadata fields. "
            "Validation passed with no errors. Source: iteration 3 of run 42.",
            "Builder produced JSON schema (12 fields). Validation passed.",
        ),
        (
            "Error in iteration 5: TypeError at line 42 of process_data.py. "
            "The input dict was missing the 'user_id' key. Stack trace shows "
            "the call originated from batch_processor.run() → process_data.transform(). "
            "Recovery attempted by adding default value, succeeded on retry.",
            "Error in iteration 5: missing 'user_id' key. Fixed with default value.",
        ),
        (
            "The architect recommended a microservice split: auth-service, "
            "data-service, and gateway. Each service communicates via gRPC. "
            "The critic approved with one caveat: add circuit breakers to gateway.",
            "The architect recommended a microservice split: auth-service, "
            "data-service, and gateway. Each service communicates via gRPC. "
            "The critic approved with one caveat: add circuit breakers to gateway.",
        ),
    ]

    print("=" * 60)
    print("SPF Demo — Semantic Provenance Fidelity")
    print("=" * 60)

    for i, (original, recovered) in enumerate(examples, 1):
        result = spf.measure(original, recovered)
        print(f"\nExample {i}:")
        print(f"  Original:  {original[:60]}...")
        print(f"  Recovered: {recovered[:60]}...")
        print(f"  Jaccard:          {result['jaccard']:.3f}")
        print(f"  Token overlap:    {result['token_overlap']:.3f}")
        print(f"  Weighted overlap: {result['weighted_overlap']:.3f}")
        print(f"  Exact match:      {'Yes' if result['content_hash_match'] else 'No'}")

    # Aggregate
    all_measurements = [spf.measure(o, r) for o, r in examples]
    agg = spf.aggregate(all_measurements)
    print(f"\nAggregate over {agg['count']} examples:")
    for metric in ["jaccard", "token_overlap", "weighted_overlap"]:
        stats = agg[metric]
        print(f"  {metric}: mean={stats['mean']:.3f} min={stats['min']:.3f} max={stats['max']:.3f}")
    print(f"  Exact match rate: {agg['exact_match_rate']:.1%}")
