"""Embedding Similarity Module — Phase 6 of Primordial v2.0.

Extends semantic_provenance_fidelity.py with:
1. EmbeddingSimilarity class with sentence-transformers primary backend
   and token overlap fallback
2. Three-tier classification (resolved/degraded/broken)
3. Threshold calibration for post-Track-A recalibration
4. Integration with existing SPFMetric

NOTE: sentence-transformers is currently MISSING from the environment.
The module MUST work with only the token overlap fallback. The embedding
backend is optional and enabled when the dependency is installed.

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
  cosine_similarity = "[dimensionless, range -1 to 1]"
  jaccard_similarity = "[dimensionless, range 0-1]"
"""

import logging
from typing import ClassVar

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from semantic_provenance_fidelity import (
    jaccard_similarity,
    token_overlap_ratio,
    weighted_token_overlap,
    SPFMetric,
)

logger = logging.getLogger(__name__)


# --- Three-Tier Classification ---

# Thresholds per protocol Section 5.3
# These are provisional and will be recalibrated after Track A pilot data.
# Uncertainty marker: weakest_anchors includes these thresholds.
RESOLVED_THRESHOLD = 0.9   # similarity > 0.9 -> resolved
DEGRADED_THRESHOLD = 0.7   # 0.7 <= similarity <= 0.9 -> degraded
                            # similarity < 0.7 -> broken


def tier_classify(similarity: float) -> str:
    """Classify similarity score into three tiers per protocol Section 5.3.

    Tier definitions:
    - similarity > 0.9:  "resolved"  (near-exact preservation)
    - 0.7 <= similarity <= 0.9: "degraded" (paraphrased but semantically intact)
    - similarity < 0.7:  "broken"    (significant information loss)

    Args:
        similarity: A similarity score in [-1, 1] (cosine) or [0, 1] (Jaccard).

    Returns:
        One of "resolved", "degraded", or "broken".

    Reference: Zahn & Chana (March 2026) — 60% fact loss per LLM compression
    pass sets expectation that many refs will land in degraded/broken tiers.
    Thresholds calibrated against this baseline.

    [CONFIDENCE: MEDIUM] — Thresholds are provisional. Validated against
    synthetic calibration pairs but not yet against genuine LLM compaction data.
    """
    if similarity > RESOLVED_THRESHOLD:
        return "resolved"
    elif similarity >= DEGRADED_THRESHOLD:
        return "degraded"
    else:
        return "broken"


# --- Embedding Similarity Engine ---

class EmbeddingSimilarity:
    """Semantic similarity with sentence-transformers primary and token overlap fallback.

    Primary backend: sentence-transformers with all-MiniLM-L6-v2 model.
    Fallback backend: combined Jaccard + weighted token overlap from
    semantic_provenance_fidelity.py.

    The fallback is always available (zero dependencies). The embedding
    backend is enabled only when sentence-transformers is installed.

    Attributes:
        backend: str — "embedding" or "token_overlap"
        model_name: str | None — sentence-transformers model name if loaded
    """

    DEFAULT_MODEL: ClassVar[str] = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str | None = None):
        """Initialize with auto-detected backend.

        Args:
            model_name: sentence-transformers model name. Defaults to
                all-MiniLM-L6-v2. Set to None to force fallback mode.
        """
        self._embedder = None
        self.model_name = model_name if model_name is not None else self.DEFAULT_MODEL
        self.backend = "token_overlap"  # default

        if model_name is not False:  # False = explicitly disable embedding
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.model_name)
                self.backend = "embedding"
                logger.info(
                    "EmbeddingSimilarity: using embedding backend (%s)",
                    self.model_name,
                )
            except ImportError:
                logger.info(
                    "EmbeddingSimilarity: sentence-transformers not available, "
                    "using token overlap fallback"
                )
            except Exception as e:
                logger.warning(
                    "EmbeddingSimilarity: failed to load model %s: %s. "
                    "Falling back to token overlap.",
                    self.model_name, e,
                )

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity between two texts.

        Returns cosine similarity (embedding backend) or a combined
        Jaccard + weighted token overlap score (fallback backend).

        Args:
            text_a: First text.
            text_b: Second text.

        Returns:
            Similarity score. Range depends on backend:
            - Embedding: [-1, 1] (cosine similarity)
            - Fallback: [0, 1] (average of Jaccard and weighted overlap)
        """
        if self._embedder is not None:
            return self._compute_embedding_similarity(text_a, text_b)
        return self._compute_fallback_similarity(text_a, text_b)

    def compute_batch(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Batch similarity computation for efficiency.

        For the embedding backend, encodes all texts at once to leverage
        batch processing. For the fallback, computes individually.

        Args:
            pairs: List of (text_a, text_b) tuples.

        Returns:
            List of similarity scores, one per pair.
        """
        if not pairs:
            return []

        if self._embedder is not None:
            return self._compute_embedding_batch(pairs)

        return [self._compute_fallback_similarity(a, b) for a, b in pairs]

    def _compute_embedding_similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity via sentence-transformers embeddings."""
        import numpy as np
        embeddings = self._embedder.encode([text_a, text_b])
        norm_a = np.linalg.norm(embeddings[0])
        norm_b = np.linalg.norm(embeddings[1])
        if norm_a == 0 or norm_b == 0:
            return 0.0
        cosine = float(np.dot(embeddings[0], embeddings[1]) / (norm_a * norm_b))
        return round(cosine, 6)

    def _compute_embedding_batch(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Batch cosine similarity via sentence-transformers."""
        import numpy as np
        # Flatten all texts, encode once
        all_texts = []
        for a, b in pairs:
            all_texts.extend([a, b])
        embeddings = self._embedder.encode(all_texts)

        results = []
        for i in range(len(pairs)):
            emb_a = embeddings[2 * i]
            emb_b = embeddings[2 * i + 1]
            norm_a = np.linalg.norm(emb_a)
            norm_b = np.linalg.norm(emb_b)
            if norm_a == 0 or norm_b == 0:
                results.append(0.0)
            else:
                cosine = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
                results.append(round(cosine, 6))
        return results

    def _compute_fallback_similarity(self, text_a: str, text_b: str) -> float:
        """Combined Jaccard + weighted token overlap as fallback.

        Uses the average of Jaccard similarity and weighted token overlap
        to provide a more robust baseline than either metric alone.
        Jaccard measures set overlap; weighted overlap respects term frequency.
        """
        jacc = jaccard_similarity(text_a, text_b)
        weighted = weighted_token_overlap(text_a, text_b)
        # Average of both metrics for robustness
        return round((jacc + weighted) / 2, 6)


# --- Threshold Calibration ---

def calibrate_thresholds(
    pairs: list[tuple[str, str, str]],
    similarity_engine: EmbeddingSimilarity | None = None,
) -> dict:
    """Calibrate tier thresholds against labeled data.

    Given labeled calibration pairs, computes actual similarity for each
    and reports whether the default thresholds (0.7, 0.9) correctly
    separate the tiers.

    Args:
        pairs: List of (text_a, text_b, expected_tier) tuples.
            expected_tier is one of "resolved", "degraded", "broken".
        similarity_engine: Optional EmbeddingSimilarity instance.
            If None, creates one with default settings.

    Returns:
        Dict with:
        - per_pair: list of {text_a, text_b, expected, actual_similarity, predicted, correct}
        - accuracy: fraction of correctly classified pairs
        - misclassifications: list of incorrect predictions
        - threshold_recommendation: dict with suggested adjustments
        - current_thresholds: dict with current values
    """
    if similarity_engine is None:
        similarity_engine = EmbeddingSimilarity()

    results = []
    for text_a, text_b, expected_tier in pairs:
        sim = similarity_engine.compute_similarity(text_a, text_b)
        predicted = tier_classify(sim)
        results.append({
            "text_a_preview": text_a[:50],
            "text_b_preview": text_b[:50],
            "expected": expected_tier,
            "actual_similarity": sim,
            "predicted": predicted,
            "correct": predicted == expected_tier,
        })

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / max(len(results), 1)
    misclassifications = [r for r in results if not r["correct"]]

    # Compute per-tier similarity ranges
    tier_ranges: dict[str, list[float]] = {"resolved": [], "degraded": [], "broken": []}
    for r in results:
        tier_ranges[r["expected"]].append(r["actual_similarity"])

    # Recommend threshold adjustments if misclassification occurs
    recommendation = {
        "resolved_threshold": RESOLVED_THRESHOLD,
        "degraded_threshold": DEGRADED_THRESHOLD,
        "adjustment_needed": len(misclassifications) > 0,
    }

    if misclassifications:
        # Suggest midpoint between adjacent tier ranges
        for tier_name, sims in tier_ranges.items():
            if sims:
                recommendation[f"{tier_name}_range"] = {
                    "min": round(min(sims), 4),
                    "max": round(max(sims), 4),
                    "mean": round(sum(sims) / len(sims), 4),
                }

    return {
        "per_pair": results,
        "accuracy": round(accuracy, 4),
        "misclassifications": misclassifications,
        "threshold_recommendation": recommendation,
        "current_thresholds": {
            "resolved": RESOLVED_THRESHOLD,
            "degraded": DEGRADED_THRESHOLD,
        },
        "backend": similarity_engine.backend,
    }


# --- SPFMetric Integration ---

@classmethod
def _from_embedding_similarity(cls, sim: EmbeddingSimilarity) -> "SPFMetric":
    """Create SPFMetric that uses embedding backend for cosine similarity.

    This classmethod is monkey-patched onto SPFMetric to allow
    integration without modifying the original module.

    Args:
        sim: An EmbeddingSimilarity instance (with embedding backend loaded).

    Returns:
        SPFMetric instance configured to use the embedding model.
    """
    if sim.backend == "embedding" and sim._embedder is not None:
        instance = cls(embedding_model=sim.model_name)
        # Re-use the already-loaded model to avoid double-loading
        instance._embedder = sim._embedder
        instance._model_name = sim.model_name
    else:
        # Fallback: create SPFMetric without embedding model
        instance = cls()
    return instance


# Attach the classmethod to SPFMetric
SPFMetric.from_embedding_similarity = _from_embedding_similarity
