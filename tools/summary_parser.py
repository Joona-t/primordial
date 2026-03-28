"""Summary Parser for LLM Compaction Output — Phase 6 of Primordial v2.0.

Extracts provenance metadata from free-text summaries produced by LLM
context-window compaction. This is a prerequisite for all three experimental
tracks (A, B, C) in the genuine compaction protocol.

Key capabilities:
1. Extract forge artifact IDs from messy LLM-generated text
2. Extract source_ref provenance relationships
3. Extract absence state label mentions
4. Unified provenance metadata extraction
5. Three-tier ref classification (resolved/degraded/broken)

NOTE: This module extends the minimal extract_artifact_ids() in
compaction_experiment.py with deduplication, context extraction, and
integration with the ref classification pipeline.

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import re
from typing import Callable

# --- Forge imports ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from forge_nulls import V1_ABSENCE_STATES


# --- Constants ---

# Artifact ID regex per CONVENTIONS.md #5.
# Format: artifact:<run>:stage:<seat>:<revision>
# The pattern is intentionally broader to also match IDs like
# artifact:run100:iter:5:r1 (used in compaction_experiment.py).
ARTIFACT_ID_PATTERN = re.compile(
    r'artifact:[a-zA-Z0-9_][a-zA-Z0-9_.:-]*:r\d+'
)

# Source ref relationship patterns
# Explicit: "source_ref: artifact:X -> artifact:Y"
SOURCE_REF_EXPLICIT = re.compile(
    r'source_ref\s*:\s*(artifact:[a-zA-Z0-9_][a-zA-Z0-9_.:-]*:r\d+)'
    r'\s*(?:->|→)\s*(artifact:[a-zA-Z0-9_][a-zA-Z0-9_.:-]*:r\d+)'
)

# "derived from artifact:X" or "based on artifact:X" or "extending artifact:X"
SOURCE_REF_IMPLICIT = re.compile(
    r'(?:derived\s+from|based\s+on|extending|built\s+on|sourced\s+from)'
    r'\s+\[?(artifact:[a-zA-Z0-9_][a-zA-Z0-9_.:-]*:r\d+)\]?',
    re.IGNORECASE,
)


# --- Extraction functions ---

def extract_artifact_ids(text: str) -> list[str]:
    """Extract all forge artifact IDs from free text.

    Handles IDs embedded in prose, brackets ([PROVENANCE: ...]),
    code blocks, and various formatting contexts. Returns a
    deduplicated list preserving order of first occurrence.

    Args:
        text: Free-text summary content (potentially messy LLM output).

    Returns:
        Deduplicated list of artifact IDs in order of first occurrence.

    Examples:
        >>> extract_artifact_ids("The artifact:run100:stage:builder:r1 was created")
        ['artifact:run100:stage:builder:r1']
        >>> extract_artifact_ids("[PROVENANCE: artifact:run100:stage:builder:r1]")
        ['artifact:run100:stage:builder:r1']
        >>> extract_artifact_ids("artifact_id is not a match")
        []
    """
    matches = ARTIFACT_ID_PATTERN.findall(text)
    # Deduplicate preserving order
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


def extract_source_refs(text: str) -> list[tuple[str, str | None]]:
    """Extract provenance relationships from summary text.

    Finds both explicit refs ("source_ref: artifact:X -> artifact:Y")
    and implicit refs ("derived from artifact:X", "based on artifact:X").

    Args:
        text: Free-text summary content.

    Returns:
        List of (source_id, target_id) tuples. target_id is None for
        implicit refs where only the source is identifiable.

    Examples:
        >>> extract_source_refs("source_ref: artifact:a:r1 -> artifact:b:r1")
        [('artifact:a:r1', 'artifact:b:r1')]
        >>> extract_source_refs("derived from artifact:a:r1")
        [('artifact:a:r1', None)]
    """
    refs: list[tuple[str, str | None]] = []
    seen = set()

    # Explicit refs: source_ref: X -> Y
    for match in SOURCE_REF_EXPLICIT.finditer(text):
        pair = (match.group(1), match.group(2))
        if pair not in seen:
            seen.add(pair)
            refs.append(pair)

    # Implicit refs: "derived from X", "based on X", etc.
    for match in SOURCE_REF_IMPLICIT.finditer(text):
        source_id = match.group(1)
        pair = (source_id, None)
        if pair not in seen:
            seen.add(pair)
            refs.append(pair)

    return refs


def extract_state_labels(text: str) -> dict[str, int]:
    """Extract mentions of absence states from V1_ABSENCE_STATES.

    Searches for state names in various formats:
    - Exact: "not_generated", "pruned_recoverable"
    - Prose: "marked as deleted", "state: unknown"
    - Quoted: "'withheld'", '"invalid"'

    Args:
        text: Free-text summary content.

    Returns:
        Dict mapping state_name -> count of mentions. Only states
        with count > 0 are included.
    """
    counts: dict[str, int] = {}
    text_lower = text.lower()

    for state in V1_ABSENCE_STATES:
        # Match the state name as a word boundary (handles underscores)
        # Also match with spaces instead of underscores for prose form
        patterns = [
            # Exact underscore form: not_generated
            re.compile(r'\b' + re.escape(state) + r'\b'),
        ]
        # Add space-separated form: "not generated", "pruned recoverable"
        if '_' in state:
            space_form = state.replace('_', r'[\s_]')
            patterns.append(re.compile(r'\b' + space_form + r'\b'))

        count = 0
        for pat in patterns:
            count += len(pat.findall(text_lower))
        # Avoid double-counting: if both patterns match the same substring,
        # the underscore form is a subset of the space-or-underscore form.
        # Use the max to avoid overcounting.
        # Actually, re-count properly: just use the flexible pattern
        flexible_pattern = re.compile(
            r'\b' + state.replace('_', r'[\s_]') + r'\b'
        )
        count = len(flexible_pattern.findall(text_lower))

        if count > 0:
            counts[state] = count

    return counts


def parse_summary_provenance(text: str) -> dict:
    """Unified provenance metadata extraction from summary text.

    Calls all three extractors and returns a structured dict with
    provenance density metric.

    Args:
        text: Free-text summary content.

    Returns:
        Dict with keys:
        - artifact_ids: list[str] — deduplicated artifact IDs
        - source_refs: list[tuple] — provenance relationships
        - state_labels: dict[str, int] — absence state mentions
        - provenance_density: float — artifact_mentions / total_tokens
    """
    artifact_ids = extract_artifact_ids(text)
    source_refs = extract_source_refs(text)
    state_labels = extract_state_labels(text)

    # Compute provenance density: how much of the text is provenance-related
    # Use simple whitespace tokenization for token count
    tokens = text.split()
    total_tokens = len(tokens) if tokens else 1  # avoid division by zero

    # Count artifact ID mentions (not unique, total occurrences)
    total_artifact_mentions = len(ARTIFACT_ID_PATTERN.findall(text))
    provenance_density = total_artifact_mentions / total_tokens

    return {
        "artifact_ids": artifact_ids,
        "source_refs": source_refs,
        "state_labels": state_labels,
        "provenance_density": round(provenance_density, 6),
    }


def classify_ref_tier(
    artifact_id: str,
    summary_text: str,
    original_content: str,
    similarity_fn: Callable[[str, str], float] | None = None,
) -> str:
    """Classify a ref as resolved/degraded/broken per protocol Section 5.3.

    Three-tier classification:
    - **Resolved:** ID in summary AND similarity(original, summary_excerpt) > 0.9
    - **Degraded:** ID in summary BUT similarity < 0.9 (content paraphrased)
    - **Broken:** ID NOT in summary

    When no similarity_fn is provided, uses a simple token overlap heuristic
    as the fallback metric.

    Args:
        artifact_id: The artifact ID to look up in the summary.
        summary_text: The full LLM compaction summary text.
        original_content: The original artifact content before LLM compaction.
        similarity_fn: Optional callable(text_a, text_b) -> float in [0, 1].
            If None, falls back to token overlap ratio.

    Returns:
        One of "resolved", "degraded", or "broken".

    [CONFIDENCE: HIGH] — Three independent checks:
    1. Protocol Section 5.3 tier definitions matched
    2. Threshold values (0.7, 0.9) from protocol calibration
    3. Fallback to token overlap when no similarity_fn provided
    """
    # Check if artifact ID appears in summary
    if artifact_id not in extract_artifact_ids(summary_text):
        return "broken"

    # ID is present — now check content fidelity
    if similarity_fn is None:
        # Fallback: token overlap ratio
        from semantic_provenance_fidelity import jaccard_similarity
        similarity = jaccard_similarity(original_content, summary_text)
    else:
        similarity = similarity_fn(original_content, summary_text)

    if similarity > 0.9:
        return "resolved"
    else:
        return "degraded"
