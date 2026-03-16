"""
detection_campaign.py -- Campaign orchestrator for Phase 3 violation detection.

Schedules D1-D9 fault injections across the task corpus, runs three-tier
comparison (uninstrumented / structured logging / forge), computes detection
rates with proper statistical confidence intervals, and separates injected
from natural detections.

Convention compliance:
  - "Compaction" always qualified per Convention #6
  - All metrics dimensionless ratios in [0, 1] or counts >= 0
  - CI method: bootstrap 95% (B=10000, seed=42) for N >= 5,
    Clopper-Pearson exact binomial for proportions at 0/n or n/n
  - Forbidden proxy guard: fp-synthetic-only enforced by
    separate_injected_natural()

Does NOT modify any existing forge tool code.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from fault_injector import (
    FAULT_TYPES,
    FAULT_DESCRIPTIONS,
    MOCKLM_DETECTION,
    FaultInjector,
    bootstrap_ci,
    clopper_pearson_ci,
    select_ci,
)
from forge_chamber import ForgeChamberError, validate_chamber
from openclaw_adapter import process_ledger


# --- Data classes ---


@dataclass
class InjectionSpec:
    """Specification for a single fault injection."""
    fault_type: str
    task_id: str
    stage_index: int
    position: str  # "early" | "middle" | "late"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InjectionResult:
    """Result of a single fault injection and detection attempt."""
    fault_type: str
    task_id: str
    stage_index: int
    position: str
    uninstrumented_detected: bool
    structured_detected: bool
    forge_detected: bool
    forge_error_type: str | None
    forge_error_detail: str | None
    verification: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TierResult:
    """Detection result from three-tier comparison for a single injection."""
    uninstrumented_detected: bool
    structured_detected: bool
    forge_detected: bool
    forge_errors: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- Campaign orchestrator ---


class DetectionCampaign:
    """Orchestrates the full injection and detection campaign.

    Builds on FaultInjector and the Phase 2 measurement framework.

    Args:
        ledger_path: Path to queue_ledger.jsonl (real data).
        task_corpus: List of task IDs to include.
        seed: Random seed for reproducible randomization.
        n_injections_per_type: Number of injections per fault type (min 10).
    """

    def __init__(
        self,
        ledger_path: str,
        task_corpus: list[str] | None = None,
        seed: int = 42,
        n_injections_per_type: int = 10,
    ):
        if n_injections_per_type < 10:
            raise ValueError(
                f"n_injections_per_type must be >= 10, got {n_injections_per_type}"
            )
        self._ledger_path = ledger_path
        self._task_corpus = task_corpus or []
        self._seed = seed
        self._n_injections = n_injections_per_type
        self._schedule: list[InjectionSpec] | None = None
        self._injection_results: list[InjectionResult] = []
        self._clean_results: list[dict] = []

    @property
    def ledger_path(self) -> str:
        return self._ledger_path

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def n_injections_per_type(self) -> int:
        return self._n_injections

    # --- Scheduling ---

    def schedule_injections(self) -> list[InjectionSpec]:
        """Schedule fault injections across the task corpus.

        For each fault type D1-D9, schedules n_injections_per_type injections.
        Randomizes injection position (early/middle/late stage indices).
        Balances across tasks: no single task gets > 30% of total injections
        for any fault type.

        Returns:
            List of InjectionSpec objects.
        """
        import random as rng_module
        rng = rng_module.Random(self._seed)

        # Build the chamber from ledger to know how many stages exist
        session_id = f"campaign-schedule-{self._seed}"
        try:
            chamber = process_ledger(self._ledger_path, session_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to process ledger for scheduling: {e}"
            ) from e

        n_stages = len(chamber.get("stages", []))
        if n_stages == 0:
            raise ValueError("Ledger produced a chamber with no stages")

        # Determine task IDs from ledger if not provided
        task_ids = self._task_corpus
        if not task_ids:
            # Extract task IDs from stage artifacts
            seen = set()
            for stage in chamber["stages"]:
                art_id = stage.get("stage_id", "")
                # Use the session_id as the task context
                task_id = art_id.split(":")[1] if ":" in art_id else "unknown"
                if task_id not in seen:
                    task_ids.append(task_id)
                    seen.add(task_id)

        if not task_ids:
            task_ids = ["default-task"]

        schedule: list[InjectionSpec] = []

        for fault_type in FAULT_TYPES:
            # Calculate max injections per task (30% cap)
            max_per_task = max(1, int(self._n_injections * 0.30))

            # Track per-task injection counts for balancing
            task_counts: dict[str, int] = {tid: 0 for tid in task_ids}

            for injection_idx in range(self._n_injections):
                # Select task (balanced distribution)
                available_tasks = [
                    tid for tid in task_ids
                    if task_counts[tid] < max_per_task
                ]
                if not available_tasks:
                    # All tasks at cap -- pick any
                    available_tasks = task_ids

                task_id = rng.choice(available_tasks)
                task_counts[task_id] += 1

                # Select stage index and position
                if fault_type == "D9":
                    # D9 doesn't need a specific stage
                    stage_index = 0
                    position = "post-seal"
                else:
                    # Randomize position within chamber
                    max_idx = n_stages - 1

                    # Determine position category
                    if max_idx <= 0:
                        stage_index = 0
                        position = "early"
                    else:
                        # Thirds: early = first 33%, middle = 33-66%, late = 67-100%
                        early_bound = max(1, max_idx // 3)
                        late_bound = max(early_bound + 1, 2 * max_idx // 3)

                        position_choice = rng.random()
                        if position_choice < 0.33:
                            stage_index = rng.randint(0, early_bound - 1)
                            position = "early"
                        elif position_choice < 0.66:
                            stage_index = rng.randint(early_bound, late_bound - 1)
                            position = "middle"
                        else:
                            stage_index = rng.randint(late_bound, max_idx)
                            position = "late"

                schedule.append(InjectionSpec(
                    fault_type=fault_type,
                    task_id=task_id,
                    stage_index=stage_index,
                    position=position,
                ))

        self._schedule = schedule
        return schedule

    # --- Three-tier comparison ---

    def run_three_tier_comparison(
        self, injected_chamber: dict, fault_type: str,
    ) -> TierResult:
        """Run injected chamber through all three tiers.

        Tier 1 (Uninstrumented): No validation -- always 0 detections.
        Tier 2 (Structured logging): Schema validation only.
        Tier 3 (Forge): Full structural validation via validate_chamber().

        Args:
            injected_chamber: Chamber with injected fault.
            fault_type: The injected fault type.

        Returns:
            TierResult with detection status per tier.
        """
        # Tier 1: Uninstrumented -- no validation capability
        uninstrumented_detected = False

        # Tier 2: Structured logging -- schema validation only
        # Structured logging checks field presence/types but not
        # structural invariants (provenance, state transitions, hashes).
        # It would only catch if the injection produced malformed JSON.
        structured_detected = False

        # Check if the injected data would fail basic schema validation
        for stage in injected_chamber.get("stages", []):
            artifact = stage.get("artifact", {})
            # Schema checks: required fields present
            required_schema_fields = ["id", "type", "schema_version"]
            for field_name in required_schema_fields:
                if field_name not in artifact:
                    structured_detected = True
                    break
            if structured_detected:
                break

        # Tier 3: Forge -- full structural validation
        forge_errors = validate_chamber(injected_chamber)
        forge_detected = len(forge_errors) > 0

        return TierResult(
            uninstrumented_detected=uninstrumented_detected,
            structured_detected=structured_detected,
            forge_detected=forge_detected,
            forge_errors=forge_errors,
        )

    # --- Detection rate computation ---

    def compute_detection_rates(
        self, results: list[InjectionResult],
    ) -> dict:
        """Compute detection rates per fault type and per tier.

        For each rate:
        - If rate is 0/n or n/n, uses Clopper-Pearson exact binomial CI.
        - Otherwise, uses bootstrap 95% CI (B=10000, seed=42).

        Args:
            results: List of injection results.

        Returns:
            Detection report with per-type and aggregate rates.
        """
        # Group by fault type
        by_type: dict[str, list[InjectionResult]] = {}
        for r in results:
            by_type.setdefault(r.fault_type, []).append(r)

        # Per-type detection rates
        per_type: dict[str, dict] = {}
        for fault_type in FAULT_TYPES:
            type_results = by_type.get(fault_type, [])
            n = len(type_results)

            if n == 0:
                per_type[fault_type] = {
                    "n": 0,
                    "uninstrumented": {"detected": 0, "rate": 0.0},
                    "structured": {"detected": 0, "rate": 0.0},
                    "forge": {"detected": 0, "rate": 0.0},
                }
                continue

            uninst_k = sum(1 for r in type_results if r.uninstrumented_detected)
            struct_k = sum(1 for r in type_results if r.structured_detected)
            forge_k = sum(1 for r in type_results if r.forge_detected)

            per_type[fault_type] = {
                "n": n,
                "uninstrumented": self._rate_with_ci(uninst_k, n, type_results, "uninstrumented_detected"),
                "structured": self._rate_with_ci(struct_k, n, type_results, "structured_detected"),
                "forge": self._rate_with_ci(forge_k, n, type_results, "forge_detected"),
            }

        # Aggregate detection rates
        total_n = len(results)
        if total_n > 0:
            total_uninst = sum(1 for r in results if r.uninstrumented_detected)
            total_struct = sum(1 for r in results if r.structured_detected)
            total_forge = sum(1 for r in results if r.forge_detected)

            aggregate = {
                "n": total_n,
                "uninstrumented": self._rate_with_ci(total_uninst, total_n, results, "uninstrumented_detected"),
                "structured": self._rate_with_ci(total_struct, total_n, results, "structured_detected"),
                "forge": self._rate_with_ci(total_forge, total_n, results, "forge_detected"),
            }
        else:
            aggregate = {"n": 0}

        # Differentials
        forge_rate = aggregate.get("forge", {}).get("rate", 0.0) if total_n > 0 else 0.0
        uninst_rate = aggregate.get("uninstrumented", {}).get("rate", 0.0) if total_n > 0 else 0.0
        struct_rate = aggregate.get("structured", {}).get("rate", 0.0) if total_n > 0 else 0.0

        differentials = {
            "delta_forge_uninstrumented": forge_rate - uninst_rate,
            "delta_forge_structured": forge_rate - struct_rate,
        }

        # D7-D9 separate reporting (new fault types without MockLM anchor)
        d7_d9 = {}
        for ft in ["D7", "D8", "D9"]:
            if ft in per_type:
                d7_d9[ft] = per_type[ft]

        return {
            "per_type": per_type,
            "aggregate": aggregate,
            "differentials": differentials,
            "d7_d9_new_findings": d7_d9,
        }

    def _rate_with_ci(
        self, k: int, n: int, results: list, attr: str,
    ) -> dict:
        """Compute rate with appropriate CI."""
        rate = k / n if n > 0 else 0.0
        values = [1.0 if getattr(r, attr, False) else 0.0 for r in results]
        lower, upper, method = select_ci(k, n, values)

        return {
            "detected": k,
            "total": n,
            "rate": rate,
            "ci_95": [lower, upper],
            "ci_method": method,
        }

    # --- Injected vs natural separation ---

    def separate_injected_natural(
        self,
        all_detections: list[dict],
        injection_schedule: list[InjectionSpec],
    ) -> tuple[list[dict], list[dict]]:
        """Separate injected detections from natural detections.

        Given all validation errors from a campaign run, separates:
        - Injected detections: errors at known injection points
        - Natural detections: errors NOT at any known injection point

        This separation is CRITICAL for the contract: fp-synthetic-only
        forbids counting injected faults as natural violations.

        Args:
            all_detections: All validation errors from the campaign.
            injection_schedule: The injection schedule with known positions.

        Returns:
            (injected_detections, natural_detections)
        """
        # Build set of known injection positions
        injection_positions = set()
        for spec in injection_schedule:
            injection_positions.add(
                (spec.fault_type, spec.task_id, spec.stage_index)
            )

        injected_detections: list[dict] = []
        natural_detections: list[dict] = []

        for detection in all_detections:
            # Try to match detection to an injection point
            det_path = detection.get("path", "")
            det_code = detection.get("code", "")

            # Parse stage index from error path (e.g., "stages[3].artifact.refs[0]")
            matched = False
            for spec in injection_schedule:
                stage_marker = f"stages[{spec.stage_index}]"
                if stage_marker in det_path:
                    injected_detections.append({
                        **detection,
                        "injection_match": {
                            "fault_type": spec.fault_type,
                            "task_id": spec.task_id,
                            "stage_index": spec.stage_index,
                        },
                    })
                    matched = True
                    break

            if not matched:
                natural_detections.append(detection)

        return injected_detections, natural_detections

    # --- Clean campaign (FPR measurement) ---

    def run_clean_campaign(
        self, n_runs_per_task: int = 5,
    ) -> dict:
        """Run the ledger through forge validation WITHOUT any injections.

        Measures false positive rate: errors on clean data are false positives.

        Args:
            n_runs_per_task: Number of clean runs (min 5).

        Returns:
            Clean results with FPR and natural violation candidates.
        """
        if n_runs_per_task < 5:
            raise ValueError(f"n_runs_per_task must be >= 5, got {n_runs_per_task}")

        clean_errors: list[list[dict]] = []
        error_counts: list[float] = []

        for run_idx in range(n_runs_per_task):
            session_id = f"clean-run-{run_idx}-seed{self._seed}"
            try:
                chamber = process_ledger(self._ledger_path, session_id)
                errors = validate_chamber(chamber)
                clean_errors.append(errors)
                error_counts.append(len(errors))
            except Exception as e:
                clean_errors.append([{
                    "code": "CLEAN_RUN_ERROR",
                    "message": str(e),
                    "path": "clean_campaign",
                }])
                error_counts.append(0)

        total_errors = sum(len(errs) for errs in clean_errors)
        total_runs = len(clean_errors)

        fpr = total_errors / total_runs if total_runs > 0 else 0.0

        # CI for FPR
        if total_errors == 0 or total_errors == total_runs:
            fpr_ci_lower, fpr_ci_upper = clopper_pearson_ci(
                min(total_errors, total_runs), total_runs
            )
            ci_method = "clopper_pearson"
        else:
            fpr_ci_lower, fpr_ci_upper = bootstrap_ci(
                [1.0 if len(e) > 0 else 0.0 for e in clean_errors]
            )
            ci_method = "bootstrap"

        # Flag high FPR
        fpr_warning = None
        if fpr > 0.05:
            fpr_warning = (
                "FPR > 5%: forge validation may be too strict for real data "
                "(Pitfall 4 from RESEARCH.md)"
            )

        # Natural violation candidates
        natural_candidates = []
        for errs in clean_errors:
            for err in errs:
                natural_candidates.append(err)

        result = {
            "n_runs": total_runs,
            "total_errors": total_errors,
            "false_positive_rate": fpr,
            "fpr_ci_95": [fpr_ci_lower, fpr_ci_upper],
            "fpr_ci_method": ci_method,
            "fpr_warning": fpr_warning,
            "natural_violation_candidates": natural_candidates,
            "error_counts_per_run": error_counts,
        }

        self._clean_results = [result]
        return result

    # --- Report generation ---

    def generate_campaign_report(
        self,
        injection_results: list[InjectionResult],
        clean_results: dict | None = None,
    ) -> dict:
        """Generate JSON-serializable campaign report.

        Args:
            injection_results: Results from injection campaign.
            clean_results: Results from clean campaign (optional).

        Returns:
            Full campaign report dict.
        """
        detection_rates = self.compute_detection_rates(injection_results)

        # Anchor comparison: D1-D6 vs MockLM ceiling (6/6)
        d1_d6_rates = {}
        d1_d6_detected_count = 0
        d1_d6_total = 0
        for ft in ["D1", "D2", "D3", "D4", "D5", "D6"]:
            type_data = detection_rates["per_type"].get(ft, {})
            forge_data = type_data.get("forge", {})
            rate = forge_data.get("rate", 0.0)
            detected = forge_data.get("detected", 0)
            total = forge_data.get("total", 0)

            d1_d6_rates[ft] = {
                "rate": rate,
                "detected": detected,
                "total": total,
                "mocklm_expected": MOCKLM_DETECTION.get(ft, "N/A"),
            }
            d1_d6_detected_count += detected
            d1_d6_total += total

        d1_d6_aggregate_rate = (
            d1_d6_detected_count / d1_d6_total if d1_d6_total > 0 else 0.0
        )

        anchor_comparison = {
            "ref": "ref-mock-experiment",
            "mocklm_ceiling": "6/6 (100%)",
            "d1_d6_aggregate_rate": d1_d6_aggregate_rate,
            "d1_d6_aggregate": f"{d1_d6_detected_count}/{d1_d6_total}",
            "d1_d6_per_type": d1_d6_rates,
            "gap_analysis": None,
        }

        if d1_d6_aggregate_rate < 1.0:
            missed = [
                ft for ft in ["D1", "D2", "D3", "D4", "D5", "D6"]
                if d1_d6_rates.get(ft, {}).get("rate", 0) < 1.0
            ]
            anchor_comparison["gap_analysis"] = {
                "missed_types": missed,
                "explanation": (
                    "MockLM catches D1-D6 at registration time (live validation). "
                    "Post-hoc validate_chamber() does not re-check hash integrity (D3), "
                    "ref correctness beyond existence (D4), or state transition "
                    "legality (D6). This is a real coverage gap in the post-hoc "
                    "validation pathway."
                ),
            }

        # Separate injected vs natural
        all_forge_errors = []
        for r in injection_results:
            if r.forge_detected:
                for err in r.verification.get("errors", []):
                    all_forge_errors.append(err)

        schedule = self._schedule or []
        injected_dets, natural_dets = self.separate_injected_natural(
            all_forge_errors, schedule,
        )

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "injection_summary": {
                "detection_rates": detection_rates,
                "total_injections": len(injection_results),
                "fault_types_tested": FAULT_TYPES,
            },
            "clean_summary": clean_results if clean_results else None,
            "anchor_comparison": anchor_comparison,
            "methodology": {
                "n_injections_per_type": self._n_injections,
                "n_clean_runs": clean_results.get("n_runs", 0) if clean_results else 0,
                "seed": self._seed,
                "ci_method": "bootstrap_95pct (B=10000, seed=42) or clopper_pearson_exact",
                "data_source": self._ledger_path,
                "task_corpus": self._task_corpus or ["auto-detected"],
            },
            "separated": {
                "injected_detections_count": len(injected_dets),
                "natural_detections_count": len(natural_dets),
                "natural_detections": natural_dets,
            },
            "d7_d9_new_findings": detection_rates.get("d7_d9_new_findings", {}),
        }

        return report

    # --- Full campaign execution ---

    def run_full_campaign(
        self,
        dry_run: bool = False,
        n_clean_runs: int = 5,
    ) -> dict:
        """End-to-end campaign execution.

        Steps: schedule -> inject -> compare -> compute -> separate -> report.

        Args:
            dry_run: If True, schedule and validate setup without executing.
            n_clean_runs: Number of clean runs for FPR measurement.

        Returns:
            Full campaign report.
        """
        # 1. Schedule
        schedule = self.schedule_injections()

        if dry_run:
            # Validate setup without executing
            return {
                "dry_run": True,
                "schedule": [s.to_dict() for s in schedule],
                "total_injections": len(schedule),
                "injections_per_type": {
                    ft: sum(1 for s in schedule if s.fault_type == ft)
                    for ft in FAULT_TYPES
                },
                "validation": {
                    "schedule_valid": len(schedule) >= 90,
                    "all_types_covered": all(
                        any(s.fault_type == ft for s in schedule)
                        for ft in FAULT_TYPES
                    ),
                    "ledger_readable": True,
                },
                "injected_detections": [],
                "natural_detections": [],
            }

        # 2. Process ledger to get base chamber
        session_id = f"campaign-{self._seed}"
        base_chamber = process_ledger(self._ledger_path, session_id)

        # 3. Run injections and three-tier comparison
        injection_results: list[InjectionResult] = []

        for spec in schedule:
            if spec.fault_type == "D9":
                # D9 is special: it tests seal enforcement
                injector = FaultInjector(base_chamber)
                try:
                    injector.inject_d9_post_seal_registration()
                    # Should not reach here
                    tier_result = TierResult(
                        uninstrumented_detected=False,
                        structured_detected=False,
                        forge_detected=False,
                    )
                except ForgeChamberError:
                    tier_result = TierResult(
                        uninstrumented_detected=False,
                        structured_detected=False,
                        forge_detected=True,
                        forge_errors=[{
                            "code": "CHAMBER.SEALED",
                            "message": "Post-seal registration rejected",
                            "path": "chamber.status",
                        }],
                    )

                injection_results.append(InjectionResult(
                    fault_type=spec.fault_type,
                    task_id=spec.task_id,
                    stage_index=spec.stage_index,
                    position=spec.position,
                    uninstrumented_detected=tier_result.uninstrumented_detected,
                    structured_detected=tier_result.structured_detected,
                    forge_detected=tier_result.forge_detected,
                    forge_error_type="ForgeChamberError" if tier_result.forge_detected else None,
                    forge_error_detail="Sealed chamber" if tier_result.forge_detected else None,
                    verification={"d9_seal_enforced": True},
                ))
                continue

            # Standard injection for D1-D8
            injector = FaultInjector(base_chamber)
            inject_method = {
                "D1": injector.inject_d1_null_collapse,
                "D2": injector.inject_d2_broken_provenance,
                "D3": injector.inject_d3_corrupted_hashes,
                "D4": injector.inject_d4_fake_source_refs,
                "D5": injector.inject_d5_missing_state_label,
                "D6": injector.inject_d6_illegal_transition,
                "D7": injector.inject_d7_compaction_data_loss,
                "D8": injector.inject_d8_context_pressure_corruption,
            }[spec.fault_type]

            # Clamp stage_index to valid range
            actual_stage_idx = min(spec.stage_index, injector.stage_count - 1)
            actual_stage_idx = max(0, actual_stage_idx)

            try:
                injected_chamber = inject_method(actual_stage_idx)
            except Exception as e:
                # Injection failed -- record as not detected
                injection_results.append(InjectionResult(
                    fault_type=spec.fault_type,
                    task_id=spec.task_id,
                    stage_index=actual_stage_idx,
                    position=spec.position,
                    uninstrumented_detected=False,
                    structured_detected=False,
                    forge_detected=False,
                    forge_error_type=None,
                    forge_error_detail=f"Injection failed: {e}",
                ))
                continue

            # Run three-tier comparison
            tier_result = self.run_three_tier_comparison(
                injected_chamber, spec.fault_type,
            )

            # Also run verify_injection for detailed info
            verification = injector.verify_injection(
                injected_chamber, spec.fault_type,
            )

            forge_error_type = None
            forge_error_detail = None
            if tier_result.forge_errors:
                first_err = tier_result.forge_errors[0]
                forge_error_type = first_err.get("code", "")
                forge_error_detail = first_err.get("message", "")

            injection_results.append(InjectionResult(
                fault_type=spec.fault_type,
                task_id=spec.task_id,
                stage_index=actual_stage_idx,
                position=spec.position,
                uninstrumented_detected=tier_result.uninstrumented_detected,
                structured_detected=tier_result.structured_detected,
                forge_detected=tier_result.forge_detected,
                forge_error_type=forge_error_type,
                forge_error_detail=forge_error_detail,
                verification=verification,
            ))

        self._injection_results = injection_results

        # 4. Run clean campaign
        clean_results = self.run_clean_campaign(n_clean_runs)

        # 5. Generate report
        report = self.generate_campaign_report(injection_results, clean_results)

        return report


# --- CLI entry point ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detection Campaign")
    parser.add_argument(
        "--ledger",
        default="integration_samples/openclaw/queue_ledger.sample.jsonl",
        help="Path to ledger file",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-n", type=int, default=10, help="Injections per type")
    args = parser.parse_args()

    campaign = DetectionCampaign(
        ledger_path=args.ledger,
        seed=args.seed,
        n_injections_per_type=args.n,
    )

    result = campaign.run_full_campaign(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
