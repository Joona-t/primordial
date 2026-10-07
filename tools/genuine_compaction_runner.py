"""Genuine Compaction Runner — Phase 6, Plan 02 of Primordial v2.0.

Orchestrates genuine LLM compaction experiments using Anthropic's
compact_20260112 beta API with pause_after_compaction for boundary capture.

Refactors and extends compaction_experiment.py with:
1. Structured RunnerConfig/TrialResult dataclasses
2. Integration with summary_parser for provenance extraction
3. Integration with embedding_similarity for SPF measurement
4. JSONL logging to data/compaction/genuine/
5. Dry-run mode (no API calls) for pipeline validation
6. Retry logic with exponential backoff

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Forge tools
import sys
sys.path.insert(0, str(Path(__file__).parent))

from compaction_experiment import (
    inject_artifact_markers,
    compute_artifact_survival,
    CompactionEvent,
)
from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from semantic_provenance_fidelity import SPFMetric
from findings_ledger import FindingsLedger, Finding
from summary_parser import (
    extract_artifact_ids as sp_extract_artifact_ids,
    extract_source_refs,
    parse_summary_provenance,
    classify_ref_tier,
)
from embedding_similarity import EmbeddingSimilarity, tier_classify


# --- Configuration ---

@dataclass
class RunnerConfig:
    """Configuration for a genuine compaction experiment."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    threshold: int = 80000  # tokens before triggering LLM compaction
    pause_after_compaction: bool = True
    provenance_aware_instructions: str | None = None
    max_retries: int = 3
    retry_base_delay: float = 2.0  # seconds, doubles each retry
    output_dir: str = "data/compaction/genuine"
    dry_run: bool = False
    num_iterations: int = 20


# --- Compaction Snapshot ---

@dataclass
class CompactionSnapshot:
    """Before/after state at a LLM compaction boundary."""
    artifact_ids: list[str]
    ref_graph: list[tuple[str, str | None]]
    chamber_hash: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "artifact_ids": self.artifact_ids,
            "ref_graph": [list(r) for r in self.ref_graph],
            "chamber_hash": self.chamber_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class BoundaryCapture:
    """Full capture of a LLM compaction boundary event."""
    pre_snapshot: CompactionSnapshot
    post_snapshot: CompactionSnapshot
    summary_text: str
    surviving_ids: list[str]
    lost_ids: list[str]
    tier_classification: dict[str, str]  # artifact_id -> resolved/degraded/broken
    spf_scores: dict
    provenance_metadata: dict

    def to_dict(self) -> dict:
        return {
            "pre_snapshot": self.pre_snapshot.to_dict(),
            "post_snapshot": self.post_snapshot.to_dict(),
            "summary_text": self.summary_text[:2000],
            "surviving_ids": self.surviving_ids,
            "lost_ids": self.lost_ids,
            "tier_classification": self.tier_classification,
            "spf_scores": self.spf_scores,
            "provenance_metadata": self.provenance_metadata,
        }


# --- Trial Result ---

@dataclass
class TrialResult:
    """Result of a single compaction experiment trial."""
    trial_id: str
    track: str
    task_category: str
    model: str
    mode: str  # "live" or "dry-run"
    provenance_aware: bool
    threshold: int
    num_iterations: int
    compaction_events: list[dict]
    aggregate_metrics: dict
    trace_stats: dict
    chamber_validation: list
    timestamp: str
    boundaries: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- Provenance-Aware Instructions ---

DEFAULT_PROVENANCE_INSTRUCTIONS = (
    'Preserve all artifact IDs (strings matching "artifact:*:r*"), all source_ref '
    "links between artifacts, and all absence state labels. These are provenance "
    "metadata that must survive summarization intact. Also preserve task state, "
    "next steps, and key decisions."
)


# --- GenuineCompactionRunner ---

class GenuineCompactionRunner:
    """Orchestrates genuine LLM compaction experiments.

    Dry-run mode (synthetic data for pipeline validation) is the only
    supported execution path in this codebase.

    Live-API mode (calling Anthropic's raw Messages API with the
    compact_20260112 beta feature) is intentionally disabled per fleet
    CLAUDE.md Rule #10 ("NO PAID LLM API, EVER") — see BUG-020 in
    BUGS_AND_ITERATIONS.md. This runner never constructs an
    `anthropic.Anthropic()` client and never reads ANTHROPIC_API_KEY to  # paid-api-gate:doc-ref
    decide whether to spend money: dry-run vs. live is governed solely by
    the explicit `RunnerConfig.dry_run` flag, so a stray inherited API key
    in the environment can never silently flip this pipeline into paid
    billing (the exact failure mode documented in astrospark BUG-010).
    Calling `run_trial()` with `dry_run=False` raises immediately with a
    pointer to this policy instead of attempting a live call.

    Usage:
        config = RunnerConfig(dry_run=True)
        ledger = FindingsLedger()
        runner = GenuineCompactionRunner(config, ledger)
        result = runner.run_trial(task_template)  # TaskTemplate instance
        runner.log_results(result)
    """

    def __init__(self, config: RunnerConfig, ledger: FindingsLedger | None = None):
        self.config = config
        self.ledger = ledger
        self.spf = SPFMetric()
        self.similarity = EmbeddingSimilarity()
        self._chamber = None
        self._artifact_ids: list[str] = []
        self._iteration_outputs: dict[str, str] = {}  # artifact_id -> output text
        self._compaction_count = 0
        self._boundaries: list[BoundaryCapture] = []
        self._events: list[CompactionEvent] = []

    def run_trial(self, task_template) -> TrialResult:
        """Execute one experiment trial.

        Args:
            task_template: A TaskTemplate instance (from task_templates.py)
                that provides generate_iteration(n) -> str.

        Returns:
            TrialResult with all metrics and boundary captures.
        """
        # Reset state for this trial
        self._artifact_ids = []
        self._iteration_outputs = {}
        self._compaction_count = 0
        self._boundaries = []
        self._events = []

        # Determine mode. Deliberately NOT gated on os.environ["ANTHROPIC_API_KEY"]:  # paid-api-gate:doc-ref
        # a stray inherited key must never silently switch this pipeline into paid
        # live-API mode (see BUG-020 / astrospark BUG-010). Only the explicit
        # RunnerConfig.dry_run flag controls dispatch.
        if self.config.dry_run:
            return self._run_dry(task_template)
        else:
            return self._run_live(task_template)

    def capture_boundary(
        self,
        messages: list[dict],
        compaction_block: dict,
        chamber,
    ) -> BoundaryCapture:
        """Capture before/after state at a LLM compaction boundary.

        Args:
            messages: Full message list at the time of LLM compaction.
            compaction_block: The compaction content block from API response.
            chamber: The forge chamber tracking artifacts.

        Returns:
            BoundaryCapture with pre/post snapshots and metrics.
        """
        now = datetime.now(timezone.utc).isoformat()
        summary_text = compaction_block.get("text", "")

        # Pre-snapshot: all artifacts known before LLM compaction
        pre_snapshot = CompactionSnapshot(
            artifact_ids=list(self._artifact_ids),
            ref_graph=self._build_ref_graph(),
            chamber_hash=self._compute_chamber_hash(chamber),
            timestamp=now,
        )

        # Parse summary with summary_parser
        provenance_metadata = parse_summary_provenance(summary_text)

        # Determine which IDs survived
        surviving_ids_set = set(provenance_metadata["artifact_ids"])
        surviving_ids = [aid for aid in self._artifact_ids if aid in surviving_ids_set]
        lost_ids = [aid for aid in self._artifact_ids if aid not in surviving_ids_set]

        # Three-tier classification for each artifact
        tier_classification = {}
        for aid in self._artifact_ids:
            original_content = self._iteration_outputs.get(aid, "")
            tier = classify_ref_tier(
                artifact_id=aid,
                summary_text=summary_text,
                original_content=original_content,
                similarity_fn=self.similarity.compute_similarity,
            )
            tier_classification[aid] = tier

        # SPF measurement for surviving artifacts
        spf_pairs = []
        for aid in surviving_ids:
            if aid in self._iteration_outputs:
                spf_pairs.append((self._iteration_outputs[aid], summary_text))

        spf_scores = {}
        if spf_pairs:
            measurements = self.spf.measure_batch(spf_pairs)
            spf_scores = self.spf.aggregate(measurements)

        # Post-snapshot
        post_snapshot = CompactionSnapshot(
            artifact_ids=surviving_ids,
            ref_graph=[(s, t) for s, t in provenance_metadata["source_refs"]],
            chamber_hash=self._compute_chamber_hash(chamber),
            timestamp=now,
        )

        boundary = BoundaryCapture(
            pre_snapshot=pre_snapshot,
            post_snapshot=post_snapshot,
            summary_text=summary_text,
            surviving_ids=surviving_ids,
            lost_ids=lost_ids,
            tier_classification=tier_classification,
            spf_scores=spf_scores,
            provenance_metadata=provenance_metadata,
        )
        self._boundaries.append(boundary)

        # Also log to findings ledger
        if self.ledger:
            survival_rate = len(surviving_ids) / max(len(self._artifact_ids), 1)
            tier_counts = {"resolved": 0, "degraded": 0, "broken": 0}
            for tier in tier_classification.values():
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            self.ledger.record(Finding(
                phase=6,
                category="compaction",
                rq="RQ3b",
                title=f"LLM compaction boundary: {survival_rate:.0%} artifact ID survival",
                description=(
                    f"Tiers: {tier_counts['resolved']} resolved, "
                    f"{tier_counts['degraded']} degraded, "
                    f"{tier_counts['broken']} broken. "
                    f"Provenance density: {provenance_metadata['provenance_density']:.4f}."
                ),
                evidence={
                    "artifact_ids_before": len(self._artifact_ids),
                    "artifact_ids_survived": len(surviving_ids),
                    "survival_rate": survival_rate,
                    "tier_classification": tier_counts,
                    "spf_scores": spf_scores,
                    "provenance_density": provenance_metadata["provenance_density"],
                },
                verdict="pending",
                confidence="high",
                tags=["COMP-04", "genuine-compaction", "boundary-capture"],
            ))

        return boundary

    def log_results(self, trial: TrialResult) -> Path:
        """Write trial results to JSONL log file.

        Args:
            trial: TrialResult to log.

        Returns:
            Path to the JSONL log file.
        """
        # Ensure output directory exists
        project_root = Path(__file__).parent.parent
        output_dir = project_root / self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write to JSONL
        log_path = output_dir / f"track-{trial.track.lower()}-{trial.trial_id}.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(trial.to_dict(), default=str) + "\n")

        return log_path

    # --- Internal methods ---

    def _run_dry(self, task_template) -> TrialResult:
        """Dry-run mode: synthetic data for pipeline validation.

        Generates synthetic conversation, simulates a LLM compaction event
        at the midpoint, and produces all metrics. Output is labeled
        mode="dry-run" in the JSONL.
        """
        trial_id = f"dry-{int(time.time())}"
        task_category = getattr(task_template, "category", "coding")
        track = getattr(task_template, "track", "A")

        # Initialize forge chamber
        self._chamber = create_chamber(f"chamber:compaction:{trial_id}:v1")

        # Generate synthetic iterations
        for i in range(self.config.num_iterations):
            prompt = task_template.generate_iteration(i)
            # Simulate a response based on the prompt
            output = self._synthetic_response(prompt, i, trial_id)
            self._register_artifact(i, output, trial_id)

        # Simulate LLM compaction event at midpoint
        midpoint = self.config.num_iterations // 2
        surviving_ids = self._artifact_ids[midpoint:]
        lost_ids = self._artifact_ids[:midpoint]

        # Build synthetic summary preserving some IDs
        summary_parts = [
            "Summary of previous work: Completed multiple implementation steps. "
        ]
        for aid in surviving_ids[:5]:
            summary_parts.append(f"[PROVENANCE: {aid}] ")
        # Add some source_refs
        if len(surviving_ids) >= 2:
            summary_parts.append(
                f"source_ref: {surviving_ids[0]} -> {surviving_ids[1]} "
            )
        summary_text = "".join(summary_parts)

        compaction_block = {"type": "compaction", "text": summary_text}

        # Capture boundary
        self.capture_boundary(
            messages=[{"role": "user", "content": "step"}] * self.config.num_iterations,
            compaction_block=compaction_block,
            chamber=self._chamber,
        )

        # Seal chamber and compute trace
        seal_chamber(self._chamber)
        trace = encode_trace(self._chamber)
        stats = trace_stats(trace)

        # Compute aggregate metrics
        survival = compute_artifact_survival(self._artifact_ids, summary_text)
        aggregate_metrics = self._compute_aggregate_metrics(survival, summary_text)

        return TrialResult(
            trial_id=trial_id,
            track=track,
            task_category=task_category,
            model=self.config.model,
            mode="dry-run",
            provenance_aware=self.config.provenance_aware_instructions is not None,
            threshold=self.config.threshold,
            num_iterations=self.config.num_iterations,
            compaction_events=[b.to_dict() for b in self._boundaries],
            aggregate_metrics=aggregate_metrics,
            trace_stats=stats,
            chamber_validation=validate_chamber(self._chamber),
            timestamp=datetime.now(timezone.utc).isoformat(),
            boundaries=[b.to_dict() for b in self._boundaries],
        )

    def _run_live(self, task_template) -> TrialResult:
        """Live-API mode is disabled fleet-wide. Always raises.

        This codebase never instantiates `anthropic.Anthropic()` and never  # paid-api-gate:doc-ref
        spends money automatically. Per CLAUDE.md Rule #10 ("NO PAID LLM
        API, EVER"): "If a feature is impossible without paid API, the
        feature gets cut, not papered over." Genuine live LLM-compaction
        measurement requires Anthropic's raw Messages API beta feature
        (compact_20260112 + pause_after_compaction), which has no
        local-CLI-subprocess (claude -p / codex exec) or sparkd
        equivalent — so rather than silently falling back to dry-run
        (which would mask a caller's explicit intent) or auto-reading
        ANTHROPIC_API_KEY from the environment (the exact silent-billing  # paid-api-gate:doc-ref
        pattern documented in astrospark BUG-010), this path fails loudly.

        See BUG-020 in BUGS_AND_ITERATIONS.md for the full rationale.
        """
        raise RuntimeError(
            "Live-API mode is disabled: primordial never calls the paid "
            "Anthropic API (fleet CLAUDE.md Rule #10 — NO PAID LLM API, "
            "EVER). Use RunnerConfig(dry_run=True) for synthetic pipeline "
            "validation. Genuine live compaction measurement is out of "
            "scope for this codebase; see BUG-020 in "
            "BUGS_AND_ITERATIONS.md."
        )

    def _api_call_with_retry(self, client, system_prompt, messages, trial_id, iteration):
        """Make API call with exponential backoff retry logic.

        Returns the response or None if all retries exhausted.
        """
        # Build context_management config for compact_20260112
        context_management = {
            "edits": [{
                "type": "compact_20260112",
                "trigger": {"type": "input_tokens", "value": self.config.threshold},
                "pause_after_compaction": self.config.pause_after_compaction,
            }]
        }

        # Add provenance-aware instructions if configured
        if self.config.provenance_aware_instructions:
            context_management["edits"][0]["instructions"] = (
                self.config.provenance_aware_instructions
            )

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=system_prompt,
                    messages=messages,
                    extra_headers={
                        "anthropic-beta": "compact-20260112",
                    },
                    context_management=context_management,
                )
                return response
            except Exception as e:
                last_error = e
                delay = self.config.retry_base_delay * (2 ** attempt)
                if self.ledger:
                    self.ledger.record(Finding(
                        phase=6,
                        category="compaction",
                        rq="RQ3b",
                        title=f"API retry {attempt + 1}/{self.config.max_retries}: "
                              f"{type(e).__name__}",
                        description=f"Trial {trial_id}, iteration {iteration}. "
                                    f"Error: {str(e)[:300]}. "
                                    f"Waiting {delay}s before retry.",
                        verdict="neutral",
                        confidence="high",
                        tags=["COMP-04", "api-retry"],
                    ))
                if attempt < self.config.max_retries - 1:
                    time.sleep(delay)

        # All retries exhausted
        if self.ledger:
            self.ledger.record(Finding(
                phase=6,
                category="compaction",
                rq="RQ3b",
                title=f"API retries exhausted: {type(last_error).__name__}",
                description=f"Trial {trial_id}, iteration {iteration}. "
                            f"Failed after {self.config.max_retries} attempts. "
                            f"Last error: {str(last_error)[:300]}",
                verdict="neutral",
                confidence="high",
                tags=["COMP-04", "api-failure"],
            ))
        return None

    def _build_system_prompt(self) -> str:
        """Build system prompt for API calls."""
        return (
            "You are a software architect working on a multi-step project. "
            "For each step, produce detailed technical output including code, "
            "analysis, and recommendations. Be thorough and verbose."
        )

    def _register_artifact(self, iteration: int, output: str, run_id: str):
        """Register an iteration output as a forge artifact."""
        marked_output, artifact_id = inject_artifact_markers(
            output, run_id, iteration
        )
        self._artifact_ids.append(artifact_id)
        self._iteration_outputs[artifact_id] = output

        source_refs = [self._artifact_ids[-2]] if len(self._artifact_ids) > 1 else []

        artifact = create_v1_stage_artifact(
            stage_id=artifact_id,
            seat="compaction-experiment",
            producer_name=f"experiment-iter-{iteration}",
            producer_role="generator",
            output=marked_output,
            source_refs=source_refs,
        )
        summary = create_v1_stage_summary(
            artifact,
            f"Iteration {iteration}: task output",
            extra_source_refs=source_refs,
        )
        register_stage(self._chamber, artifact, summary)

    def _synthetic_response(self, prompt: str, iteration: int, run_id: str) -> str:
        """Generate a synthetic response for dry-run mode."""
        return (
            f"Step {iteration + 1} output: Implementing component {iteration + 1} "
            f"as requested. This involves designing the data flow for the system, "
            f"including input validation with schema checking, processing middleware "
            f"that handles transformation and enrichment, output formatting with "
            f"configurable serializers, and error handling for all edge cases. "
            f"The implementation uses a layered architecture with dependency injection. "
            f"Key functions: process_input(), transform_data(), validate_output(), "
            f"handle_errors(). Error handling covers: malformed input (400), "
            f"unauthorized access (401), rate limiting (429), and server errors (500). "
            f"Testing includes unit tests for each function, integration tests for "
            f"the full pipeline, and performance benchmarks for throughput measurement. "
            f"Documentation follows OpenAPI 3.0 specification with examples for each "
            f"endpoint and response code. Configuration is managed via environment "
            f"variables with sensible defaults and validation at startup. "
        ) * 2  # ~500 tokens of content

    def _build_ref_graph(self) -> list[tuple[str, str | None]]:
        """Build the current provenance ref graph from registered artifacts."""
        refs = []
        for i, aid in enumerate(self._artifact_ids):
            if i > 0:
                refs.append((self._artifact_ids[i - 1], aid))
        return refs

    def _compute_chamber_hash(self, chamber) -> str:
        """Compute a hash of the current chamber state."""
        import hashlib
        if chamber is None:
            return "none"
        try:
            content = json.dumps(chamber, sort_keys=True, default=str)
            return hashlib.sha256(content.encode()).hexdigest()[:16]
        except (TypeError, ValueError):
            return "unhashable"

    def _compute_aggregate_metrics(self, survival: dict, summary_text: str) -> dict:
        """Compute aggregate metrics for a trial."""
        # Structural reachability = artifact ID survival rate
        structural_reachability = survival["survival_rate"]

        # Artifact ID survival
        artifact_id_survival = survival["survival_rate"]

        # Compression ratio: rough estimate from token counts
        total_tokens_pre = sum(
            len(text.split()) for text in self._iteration_outputs.values()
        )
        summary_tokens = len(summary_text.split())
        compression_ratio = total_tokens_pre / max(summary_tokens, 1)

        # SPF scores from boundaries
        spf_scores = {}
        if self._boundaries:
            spf_scores = self._boundaries[-1].spf_scores

        # Degraded fraction
        degraded_fraction = 0.0
        if self._boundaries:
            tiers = self._boundaries[-1].tier_classification
            total = max(len(tiers), 1)
            degraded_count = sum(1 for t in tiers.values() if t == "degraded")
            degraded_fraction = degraded_count / total

        # Semantic fidelity from SPF (use jaccard mean if available)
        semantic_fidelity = 0.0
        if spf_scores and "jaccard" in spf_scores:
            jaccard_info = spf_scores["jaccard"]
            if isinstance(jaccard_info, dict) and "mean" in jaccard_info:
                semantic_fidelity = jaccard_info["mean"]

        return {
            "structural_reachability": round(structural_reachability, 4),
            "semantic_fidelity": round(semantic_fidelity, 4),
            "artifact_id_survival": round(artifact_id_survival, 4),
            "compression_ratio": round(compression_ratio, 2),
            "degraded_fraction": round(degraded_fraction, 4),
            "spf_scores": spf_scores,
        }

    def _compute_live_aggregate_metrics(self) -> dict:
        """Compute aggregate metrics from all boundary captures in live mode."""
        if not self._boundaries:
            return {
                "structural_reachability": 1.0,
                "semantic_fidelity": 1.0,
                "artifact_id_survival": 1.0,
                "compression_ratio": 1.0,
                "degraded_fraction": 0.0,
                "spf_scores": {},
            }

        # Average across all boundaries
        total_before = 0
        total_survived = 0
        all_tiers = {"resolved": 0, "degraded": 0, "broken": 0}
        all_spf = []

        for boundary in self._boundaries:
            total_before += len(boundary.pre_snapshot.artifact_ids)
            total_survived += len(boundary.surviving_ids)
            for tier in boundary.tier_classification.values():
                all_tiers[tier] = all_tiers.get(tier, 0) + 1
            if boundary.spf_scores:
                all_spf.append(boundary.spf_scores)

        total_artifacts = max(total_before, 1)
        structural_reachability = total_survived / total_artifacts
        artifact_id_survival = structural_reachability

        total_classified = sum(all_tiers.values())
        degraded_fraction = all_tiers["degraded"] / max(total_classified, 1)

        # Merge SPF scores
        merged_spf = all_spf[-1] if all_spf else {}

        semantic_fidelity = 0.0
        if merged_spf and "jaccard" in merged_spf:
            jaccard_info = merged_spf["jaccard"]
            if isinstance(jaccard_info, dict) and "mean" in jaccard_info:
                semantic_fidelity = jaccard_info["mean"]

        # Compression ratio from total tokens
        total_pre_tokens = sum(
            len(text.split()) for text in self._iteration_outputs.values()
        )
        total_summary_tokens = sum(
            len(b.summary_text.split()) for b in self._boundaries
        )
        compression_ratio = total_pre_tokens / max(total_summary_tokens, 1)

        return {
            "structural_reachability": round(structural_reachability, 4),
            "semantic_fidelity": round(semantic_fidelity, 4),
            "artifact_id_survival": round(artifact_id_survival, 4),
            "compression_ratio": round(compression_ratio, 2),
            "degraded_fraction": round(degraded_fraction, 4),
            "spf_scores": merged_spf,
        }
