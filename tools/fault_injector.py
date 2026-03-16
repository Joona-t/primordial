"""
fault_injector.py -- D1-D9 fault injection framework for violation detection campaign.

Wraps sealed forge chambers to inject each of 9 structural fault types at
configurable positions. Each injection method returns a MODIFIED COPY of the
chamber (never mutates the original).

Fault taxonomy (D1-D9):
  D1: Null collapse -- typed absence output replaced with bare None
  D2: Broken provenance -- source_refs point to nonexistent artifact IDs
  D3: Corrupted hashes -- content modified after hash computation
  D4: Fake source refs -- refs are valid IDs but point to wrong artifact
  D5: Missing state label -- output_state removed from null output
  D6: Illegal transition -- forced illegal state transition
  D7: Forge trace compression data loss -- cursor-advancement refs silently dropped
  D8: Context pressure corruption -- truncated output simulating memory pressure
  D9: Post-seal registration -- stage registered after chamber seal

Convention compliance:
  - "Compaction" always qualified per Convention #6
  - All metrics dimensionless ratios in [0, 1] or counts >= 0
  - Uses deepcopy for all mutations, never modifies original

Does NOT modify any existing forge tool code. Wraps their output.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from typing import Any

# Ensure tools/ is importable
import sys
from pathlib import Path

_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from forge_chamber import (
    ForgeChamberError,
    register_stage,
    seal_chamber,
    validate_chamber,
)
from forge_nulls import (
    TRANSITION_TABLE,
    V1_ABSENCE_STATES,
    validate_transition,
)
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary


# --- Fault type constants ---

FAULT_TYPES = [
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
]

FAULT_DESCRIPTIONS = {
    "D1": "Null collapse: typed absence replaced with bare None",
    "D2": "Broken provenance: source_refs point to nonexistent artifact IDs",
    "D3": "Corrupted hashes: content modified after hash computation",
    "D4": "Fake source refs: valid IDs but point to wrong artifact",
    "D5": "Missing state label: output_state removed from null output",
    "D6": "Illegal transition: forced illegal state transition",
    "D7": "Forge trace compression data loss: cursor-advancement refs silently dropped",
    "D8": "Context pressure corruption: truncated output simulating memory pressure",
    "D9": "Post-seal registration: stage registered after chamber seal",
}

# MockLM-documented detection mechanisms for D1-D6
MOCKLM_DETECTION = {
    "D1": "ForgeNullError",
    "D2": "ForgeRefError",
    "D3": "ForgeChamberError",
    "D4": "ForgeChamberError",
    "D5": "ForgeChamberError",
    "D6": "ForgeChamberError",
}


class FaultInjector:
    """Injects structural faults (D1-D9) into sealed forge chambers.

    Operates on sealed chambers (post-hoc), not during live processing.
    Each injection method returns a MODIFIED COPY of the chamber.
    """

    def __init__(self, chamber: dict):
        """Initialize with a sealed chamber dict.

        Args:
            chamber: A sealed forge chamber from OpenClawAdapter.finalize()
                     or process_ledger(). Must have 'stages' list.
        """
        self._original = chamber

    @property
    def original(self) -> dict:
        """The unmodified original chamber."""
        return self._original

    @property
    def stage_count(self) -> int:
        """Number of stages in the original chamber."""
        return len(self._original.get("stages", []))

    def _deep_copy(self) -> dict:
        """Return a deep copy of the original chamber.

        Handles set -> list conversion for artifact_index (sets are not
        directly deepcopyable when mixed with other types in some contexts).
        """
        # Convert set to list for deepcopy, then back
        orig_index = self._original.get("artifact_index")
        if isinstance(orig_index, set):
            self._original["artifact_index"] = sorted(orig_index)

        result = copy.deepcopy(self._original)

        # Restore original
        if isinstance(orig_index, set):
            self._original["artifact_index"] = orig_index

        # Convert back to set in copy
        idx = result.get("artifact_index")
        if isinstance(idx, list):
            result["artifact_index"] = set(idx)

        return result

    def _validate_stage_index(self, stage_index: int) -> None:
        """Validate that stage_index is in range."""
        if stage_index < 0 or stage_index >= self.stage_count:
            raise ValueError(
                f"stage_index {stage_index} out of range [0, {self.stage_count})"
            )

    # --- D1: Null collapse ---

    def inject_d1_null_collapse(self, stage_index: int) -> dict:
        """D1: Replace typed absence output with bare None.

        Strips the output_state field from the specified stage,
        leaving a bare None output without typed absence annotation.

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Replace typed absence with bare None
        artifact["output"] = None
        # Remove output_state if present (creating ambiguous null)
        artifact.pop("output_state", None)
        # Also strip from status to make it clearly corrupted
        artifact["status"] = "complete"  # Contradicts None output

        return chamber

    # --- D2: Broken provenance ---

    def inject_d2_broken_provenance(self, stage_index: int) -> dict:
        """D2: Replace source_refs with refs to nonexistent artifact IDs.

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Replace refs with ghost references
        ghost_refs = [
            {"ref": "artifact:ghost:stage:phantom:r1", "state": "resolved"},
            {"ref": "artifact:ghost:stage:specter:r1", "state": "resolved"},
        ]
        artifact["refs"] = ghost_refs

        # Also corrupt summary source_refs if summary exists
        summary = stage.get("summary")
        if summary is not None:
            summary["source_refs"] = ghost_refs

        return chamber

    # --- D3: Corrupted hashes ---

    def inject_d3_corrupted_hashes(self, stage_index: int) -> dict:
        """D3: Modify artifact content AFTER hash computation.

        The hash field no longer matches the content, violating
        hash integrity convention (#10): json.dumps(obj, sort_keys=True,
        ensure_ascii=True).

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Modify output AFTER hash was computed
        current_output = artifact.get("output")
        if current_output is not None:
            artifact["output"] = current_output + " [CORRUPTED_POST_HASH]"
        else:
            # If output was null, set it to something to break the hash
            artifact["output"] = "[CORRUPTED_POST_HASH]"

        # The hash field now does not match the modified content
        # Do NOT recompute the hash -- that's the corruption

        return chamber

    # --- D4: Fake source refs ---

    def inject_d4_fake_source_refs(self, stage_index: int) -> dict:
        """D4: Replace source_refs with valid but wrong artifact refs.

        The refs are syntactically valid IDs that exist in the chamber's
        artifact_index, but point to the WRONG artifact (a different
        stage than the logical parent).

        Args:
            stage_index: Index of the stage to corrupt (must be > 0).

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Find a stage that is NOT the logical parent
        # The logical parent is typically stage_index - 1
        available_ids = list(chamber.get("artifact_index", set()))
        # Remove this stage's own ID and chamber ID
        own_id = artifact.get("id", "")
        chamber_id = chamber.get("chamber_id", "")

        # Filter to artifact IDs (not chamber or summary IDs)
        candidate_ids = [
            aid for aid in available_ids
            if aid != own_id
            and aid != chamber_id
            and aid.startswith("artifact:")
        ]

        if not candidate_ids:
            # If no other artifacts exist, create a self-referencing loop
            candidate_ids = [own_id]

        # Get the current refs to find the correct parent
        current_refs = artifact.get("refs", [])
        correct_parent_ids = {
            r.get("ref") for r in current_refs
            if isinstance(r, dict) and r.get("state") == "resolved"
        }

        # Pick an ID that is NOT the correct parent
        wrong_ids = [aid for aid in candidate_ids if aid not in correct_parent_ids]
        if not wrong_ids:
            wrong_ids = candidate_ids  # fallback: any valid ID

        fake_ref = wrong_ids[0]
        artifact["refs"] = [{"ref": fake_ref, "state": "resolved"}]

        return chamber

    # --- D5: Missing state label ---

    def inject_d5_missing_state_label(self, stage_index: int) -> dict:
        """D5: Remove output_state from a null-output stage.

        Leaves ambiguous absence: output is None but no typed absence state.

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Force output to None and strip state label
        artifact["output"] = None
        artifact.pop("output_state", None)
        # Keep status as-is to create inconsistency

        return chamber

    # --- D6: Illegal transition ---

    def inject_d6_illegal_transition(self, stage_index: int) -> dict:
        """D6: Force an illegal state transition.

        Changes the stage's output_state to create a (from, to) pair
        that TRANSITION_TABLE classifies as illegal. Uses validate_transition()
        from forge_nulls.py to confirm the transition is indeed illegal.

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Force output to null with an illegal transition
        # Initial states (not_invoked, not_generated) have no incoming transitions
        # except self-transitions. So transitioning FROM any state TO not_invoked
        # is illegal (except from not_invoked itself).

        # Set output to null and assign output_state to create illegal transition
        artifact["output"] = None

        # Find an illegal target state. We use "not_invoked" as target
        # because nothing can transition INTO initial states.
        # The "from" state is whatever the previous stage had.
        artifact["output_state"] = "not_invoked"

        # Verify this actually creates an illegal transition
        # by checking against at least one non-initial source state
        for from_state in sorted(V1_ABSENCE_STATES):
            if from_state == "not_invoked":
                continue  # self-transition is legal
            if not validate_transition(from_state, "not_invoked"):
                # Confirmed: this transition is illegal
                break

        return chamber

    # --- D7: Forge trace compression data loss ---

    def inject_d7_compaction_data_loss(self, stage_index: int) -> dict:
        """D7: Silently drop task_ids from cursor-advancement source_refs.

        During a cursor-advancement artifact (compact type), silently drops
        some task_ids from the source_refs list. The remaining refs still
        form a valid-looking ref list, but information is lost.

        NOTE: "compaction" here refers to forge trace compression
        (cursor advancement), NOT LLM context-window compaction.

        Args:
            stage_index: Index of the stage to corrupt (should be a
                         cursor-advancement stage for realistic injection).

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Drop some refs from the source_refs list
        refs = artifact.get("refs", [])
        if len(refs) > 1:
            # Drop half the refs (silent data loss)
            keep_count = max(1, len(refs) // 2)
            artifact["refs"] = refs[:keep_count]
        elif len(refs) == 1:
            # Only one ref -- drop it entirely
            artifact["refs"] = []

        # Also corrupt the output text to hide the loss
        output = artifact.get("output", "")
        if isinstance(output, str) and "task artifact(s)" in output:
            # Rewrite the count to match the reduced refs
            new_count = len(artifact["refs"])
            import re
            artifact["output"] = re.sub(
                r"\d+ task artifact\(s\)",
                f"{new_count} task artifact(s)",
                output,
            )

        # Also modify summary if present
        summary = stage.get("summary")
        if summary is not None and isinstance(summary.get("source_refs"), list):
            keep = max(1, len(summary["source_refs"]) // 2)
            summary["source_refs"] = summary["source_refs"][:keep]

        return chamber

    # --- D8: Context pressure corruption ---

    def inject_d8_context_pressure_corruption(self, stage_index: int) -> dict:
        """D8: Truncate artifact output mid-string.

        Simulates memory pressure corruption. The output is non-null
        but incomplete, and if the stage has a summary, the summary
        content is also corrupted.

        Args:
            stage_index: Index of the stage to corrupt.

        Returns:
            Modified copy of the chamber.
        """
        self._validate_stage_index(stage_index)
        chamber = self._deep_copy()
        stage = chamber["stages"][stage_index]
        artifact = stage["artifact"]

        # Truncate output mid-string
        output = artifact.get("output")
        if output is not None and isinstance(output, str) and len(output) > 10:
            # Cut at roughly 40% -- mid-string truncation
            cut_point = max(5, len(output) * 2 // 5)
            artifact["output"] = output[:cut_point]
        elif output is None:
            # Force a truncated output where there was none
            artifact["output"] = "[TRUNCATED_BY_CONTEXT_PRES"
            artifact.pop("output_state", None)

        # Corrupt summary text too
        summary = stage.get("summary")
        if summary is not None:
            summary_text = summary.get("summary", "")
            if isinstance(summary_text, str) and len(summary_text) > 5:
                cut = max(3, len(summary_text) * 2 // 5)
                summary["summary"] = summary_text[:cut]
                # Recompute summary_hash to create hash mismatch
                # Actually DON'T recompute -- let the old hash stand
                # so the hash verification catches it

        return chamber

    # --- D9: Post-seal registration ---

    def inject_d9_post_seal_registration(self) -> dict:
        """D9: Attempt to register a new stage after the chamber is sealed.

        This violates chamber seal semantics (sealed chambers are immutable).

        Returns:
            Modified copy of the chamber with the illegal registration attempt.

        Raises:
            ForgeChamberError: Always raised -- this IS the expected behavior.
                The test verifies that the error is raised.
        """
        chamber = self._deep_copy()

        # Ensure chamber is sealed
        if chamber.get("status") != "sealed":
            chamber["status"] = "sealed"

        # Attempt to register a new stage -- this MUST raise ForgeChamberError
        new_artifact = create_v1_stage_artifact(
            stage_id="artifact:injected:stage:post-seal:r1",
            seat="injected-post-seal",
            producer_name="fault-injector",
            producer_role="post-seal-injector",
            output="This should not be allowed in a sealed chamber",
        )
        new_summary = create_v1_stage_summary(
            new_artifact,
            "Illegally registered after seal.",
        )

        # This will raise ForgeChamberError because chamber is sealed
        register_stage(chamber, new_artifact, new_summary)

        # Should never reach here
        return chamber  # pragma: no cover

    # --- Injection verification ---

    def verify_injection(
        self,
        injected_chamber: dict,
        fault_type: str,
    ) -> dict:
        """Verify that an injection produced a detectable corruption.

        Args:
            injected_chamber: The chamber after fault injection.
            fault_type: The fault type (D1-D9).

        Returns:
            Dict with verification results:
            {
                "verified": bool,
                "original_valid": bool,
                "injected_invalid": bool,
                "errors": list,
                "detection_mechanism": str | None,
                "gap_identified": bool,
                "gap_reason": str | None,
            }
        """
        # Check original chamber validity
        original_errors = validate_chamber(self._original)
        original_valid = len(original_errors) == 0

        # Check injected chamber validity
        injected_errors = validate_chamber(injected_chamber)
        injected_invalid = len(injected_errors) > 0

        # Determine detection mechanism
        detection_mechanism = None
        gap_identified = False
        gap_reason = None

        if injected_invalid:
            # Identify which error type caught the fault
            error_codes = [e.get("code", "") for e in injected_errors]
            if any("REF" in c for c in error_codes):
                detection_mechanism = "ref_resolution_check"
            elif any("INDEX" in c for c in error_codes):
                detection_mechanism = "artifact_index_check"
            elif any("ABSENCE" in c or "NULL" in c for c in error_codes):
                detection_mechanism = "null_discipline_check"
            elif any("DUPLICATE" in c for c in error_codes):
                detection_mechanism = "duplicate_id_check"
            elif any("SCHEMA" in c for c in error_codes):
                detection_mechanism = "schema_validation"
            else:
                detection_mechanism = "chamber_validation"
        else:
            # Forge validation did not catch this fault
            gap_identified = True
            gap_reason = (
                f"validate_chamber() returned no errors for {fault_type} injection. "
                f"The corrupted artifact passes all current validation checks."
            )

        verified = original_valid and injected_invalid

        return {
            "verified": verified,
            "original_valid": original_valid,
            "injected_invalid": injected_invalid,
            "errors": injected_errors,
            "detection_mechanism": detection_mechanism,
            "gap_identified": gap_identified,
            "gap_reason": gap_reason,
            "fault_type": fault_type,
        }

    # --- Random injection ---

    def inject_random(
        self,
        fault_type: str,
        seed: int | None = None,
    ) -> dict:
        """Randomly select a valid stage index and inject the specified fault.

        Args:
            fault_type: One of D1-D9.
            seed: Random seed for reproducibility.

        Returns:
            Modified copy of the chamber.

        Raises:
            ValueError: If fault_type is unknown or no valid stage exists.
        """
        if fault_type not in FAULT_TYPES:
            raise ValueError(
                f"Unknown fault type: {fault_type}. Must be one of {FAULT_TYPES}"
            )

        rng = random.Random(seed)

        if fault_type == "D9":
            # D9 does not take a stage_index
            return self.inject_d9_post_seal_registration()

        # Select a random valid stage index
        if self.stage_count == 0:
            raise ValueError("Cannot inject fault: chamber has no stages")

        stage_index = rng.randint(0, self.stage_count - 1)

        inject_method = {
            "D1": self.inject_d1_null_collapse,
            "D2": self.inject_d2_broken_provenance,
            "D3": self.inject_d3_corrupted_hashes,
            "D4": self.inject_d4_fake_source_refs,
            "D5": self.inject_d5_missing_state_label,
            "D6": self.inject_d6_illegal_transition,
            "D7": self.inject_d7_compaction_data_loss,
            "D8": self.inject_d8_context_pressure_corruption,
        }[fault_type]

        return inject_method(stage_index)


# --- Statistical framework ---


def bootstrap_ci(
    values: list[float],
    n_boot: int = 10_000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Compute bootstrap percentile confidence interval.

    Args:
        values: Sample values.
        n_boot: Number of bootstrap resamples.
        seed: Random seed for reproducibility.
        alpha: Significance level (default 0.05 for 95% CI).

    Returns:
        (lower, upper) bounds of the confidence interval.
    """
    import numpy as np

    if not values:
        raise ValueError("Cannot compute bootstrap CI on empty values")

    if len(values) == 1:
        return (values[0], values[0])

    arr = np.array(values, dtype=np.float64)
    rng = np.random.default_rng(seed=seed)

    boot_means = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means[i] = np.mean(sample)

    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    return (lower, upper)


def clopper_pearson_ci(
    k: int,
    n: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Compute Clopper-Pearson exact binomial confidence interval.

    Used for proportions at boundary values (0/n or n/n) where
    bootstrap CIs degenerate to zero width.

    Args:
        k: Number of successes.
        n: Number of trials.
        alpha: Significance level (default 0.05 for 95% CI).

    Returns:
        (lower, upper) bounds of the confidence interval.
    """
    from scipy.stats import beta

    if n == 0:
        return (0.0, 1.0)

    if k == 0:
        lower = 0.0
    else:
        lower = float(beta.ppf(alpha / 2, k, n - k + 1))

    if k == n:
        upper = 1.0
    else:
        upper = float(beta.ppf(1 - alpha / 2, k + 1, n - k))

    return (lower, upper)


def select_ci(
    k: int,
    n: int,
    values: list[float] | None = None,
    alpha: float = 0.05,
) -> tuple[float, float, str]:
    """Auto-select appropriate CI method.

    Uses Clopper-Pearson for boundary proportions (k=0 or k=n),
    bootstrap for interior proportions.

    Args:
        k: Number of successes.
        n: Number of trials.
        values: Sample values for bootstrap (required if not boundary).
        alpha: Significance level.

    Returns:
        (lower, upper, method) where method is "clopper_pearson" or "bootstrap".
    """
    if k == 0 or k == n:
        lower, upper = clopper_pearson_ci(k, n, alpha)
        return (lower, upper, "clopper_pearson")

    if values is None:
        # Fall back to Clopper-Pearson if no values provided
        lower, upper = clopper_pearson_ci(k, n, alpha)
        return (lower, upper, "clopper_pearson")

    lower, upper = bootstrap_ci(values, alpha=alpha)
    return (lower, upper, "bootstrap")
