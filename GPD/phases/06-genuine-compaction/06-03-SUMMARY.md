---
phase: 06-genuine-compaction
plan: 03
depth: full
one-liner: "Built and dry-run-validated pilot Track A runner (6 trials, 3 categories, provenance-aware toggle); live API execution blocked by missing ANTHROPIC_API_KEY — go/no-go deferred"
subsystem: [orchestration, validation, experiment-design]
tags: [compaction, pilot, track-a, dry-run, pipeline-validation, environment-gate]

requires:
  - phase: 06-genuine-compaction
    plan: 01
    provides: [summary_parser.py, embedding_similarity.py]
  - phase: 06-genuine-compaction
    plan: 02
    provides: [genuine_compaction_runner.py, task_templates.py, RunnerConfig, GenuineCompactionRunner, CodingTaskTemplate, DebuggingTaskTemplate, SpecificationTaskTemplate]
provides:
  - run_pilot_track_a.py: end-to-end pilot runner with 6-trial matrix, cost guards, analysis, and reporting
  - pilot-results.jsonl: dry-run JSONL (6 lines, valid schema, all metrics in range)
  - pilot-analysis.json: aggregated statistics with anchor comparisons and go/no-go assessment
  - pilot-report.md: full pilot report with per-category metrics, provenance-aware delta, anchor comparisons, tier distribution, variance estimate
affects: [06-04 Track B, 06-05 Track C ablation, full Track A execution after API key provisioned]

methods:
  added: [cost estimation for Sonnet API calls, automated go/no-go assessment with quantitative criteria, pilot analysis pipeline with anchor comparisons]
  patterns: [trial matrix specification, per-category breakdown, provenance-aware delta computation, three-anchor comparison framework (MockLM ceiling, Knowledge Objects 60% loss, v1.0 simulated)]

key-files:
  created:
    - tools/run_pilot_track_a.py
    - data/compaction/genuine/pilot-results.jsonl
    - data/compaction/genuine/pilot-analysis.json
    - docs/pilot-report.md

key-decisions:
  - "Go/no-go computed automatically from quantitative thresholds: pipeline_valid (>=4 complete), compaction_fires (>=4 events), metrics_measurable (not all 0 or all 1), live_mode (not dry-run)"
  - "Dry-run produces deterministic uniform data (survival=0.25 for all trials) — this is expected because synthetic compaction is midpoint-split by design"
  - "Zero provenance-aware delta in dry-run is expected — the synthetic compaction does not use provenance_aware_instructions"
  - "Environment gate documented honestly: forbidden proxy fp-dry-run-only is triggered, claim-pipeline-valid is blocked"

patterns-established:
  - "Pilot analysis pattern: global stats + per-category + provenance delta + three-anchor comparison + tier distribution + go/no-go"
  - "Cost guard pattern: estimate before each trial, running total, hard limit"
  - "Report generation: automated markdown from analysis JSON"

conventions:
  - "artifact ID format: artifact:<run>:iter:<n>:r1 (CONVENTIONS.md #5)"
  - "compaction disambiguation: forge=lossless, LLM=lossy (CONVENTIONS.md #6)"
  - "all metrics dimensionless (CONVENTIONS.md #7)"
  - "JSONL mode field: 'live' for API calls, 'dry-run' for simulated"
  - "dry-run data labeled as such in all outputs (mode='dry-run' in JSONL, NOTE banner in report)"

plan_contract_ref: "GPD/phases/06-genuine-compaction/06-03-PLAN.md#/contract"
contract_results:
  claims:
    claim-pipeline-valid:
      status: blocked
      summary: "Pipeline logic validated end-to-end in dry-run mode (6/6 trials complete, all metrics valid, JSONL schema correct). However, live API validation is blocked by missing ANTHROPIC_API_KEY. Forbidden proxy fp-dry-run-only is triggered."
      linked_ids: [deliv-pilot-results, deliv-pilot-runner, test-pipeline-live, ref-mock-experiment]
    claim-pilot-magnitude:
      status: blocked
      summary: "Dry-run produces deterministic synthetic data (survival=0.25, reachability=0.25) which validates pipeline computation but does not measure genuine LLM compaction behavior. Magnitude estimates require live API calls."
      linked_ids: [deliv-pilot-report, deliv-pilot-analysis, test-magnitude-estimate, ref-mock-experiment, ref-knowledge-objects, ref-v1-simulated]
  deliverables:
    deliv-pilot-results:
      status: partial
      path: "data/compaction/genuine/pilot-results.jsonl"
      summary: "6-line JSONL with valid schema and all required fields. Mode is 'dry-run' — not genuine API data. All metric values in valid ranges."
      linked_ids: [claim-pipeline-valid, test-pipeline-live]
    deliv-pilot-analysis:
      status: partial
      path: "data/compaction/genuine/pilot-analysis.json"
      summary: "Aggregated pilot statistics computed correctly on dry-run data. Three anchor comparisons populated. Go/no-go = BLOCKED (dry-run only). Analysis pipeline validated."
      linked_ids: [claim-pilot-magnitude, test-magnitude-estimate]
    deliv-pilot-report:
      status: partial
      path: "docs/pilot-report.md"
      summary: "Full report generated with all required sections: per-category metrics, MockLM anchor comparison, variance estimate, go/no-go recommendation. Report clearly labeled as dry-run."
      linked_ids: [claim-pilot-magnitude, test-magnitude-estimate]
    deliv-pilot-runner:
      status: passed
      path: "tools/run_pilot_track_a.py"
      summary: "Complete pilot execution script: 6-trial matrix, cost guards ($50 limit), progress logging, automatic analysis + report generation. Supports both --dry-run and live mode. Ready for live API execution when ANTHROPIC_API_KEY is provisioned."
      linked_ids: [claim-pipeline-valid, test-pipeline-live]
  acceptance_tests:
    test-pipeline-live:
      status: blocked
      summary: "Dry-run validation passed all criteria: 6/6 complete (>= 4 required), 6/6 trigger compaction events (>= 4 required), JSONL parseable, no crashes. But acceptance test requires live API mode (not dry-run). Blocked by environment gate: ANTHROPIC_API_KEY not set."
      linked_ids: [claim-pipeline-valid, deliv-pilot-results, deliv-pilot-runner]
    test-magnitude-estimate:
      status: blocked
      summary: "Analysis pipeline computed all metrics and anchor comparisons correctly on dry-run data. But magnitude estimates from dry-run are meaningless (deterministic synthetic compaction). Live API data required for genuine magnitude assessment."
      linked_ids: [claim-pilot-magnitude, deliv-pilot-analysis, deliv-pilot-report]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM ceiling (survival=1.0, reachability=1.0) used as anchor. Dry-run pilot shows survival=0.25, delta=-0.75 from ceiling. Expected direction (genuine < ceiling) but dry-run delta is from synthetic midpoint split, not genuine LLM behavior."
    ref-knowledge-objects:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "Knowledge Objects 60% fact loss (40% survival) anchor computed in analysis. Dry-run survival=0.25 < 0.40, labeled 'worse_or_equal'. But this comparison is meaningless on synthetic data — it tests the computation pipeline, not the hypothesis."
    ref-v1-simulated:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "v1.0 simulated compaction reachability (0.82 at 50% deletion) anchor populated in analysis. Note added: comparison requires matching compression ratio. Dry-run data is not comparable to simulated deletion."
  forbidden_proxies:
    fp-dry-run-only:
      status: violated
      notes: "This forbidden proxy is triggered. Plan 03 ran in dry-run mode only due to missing ANTHROPIC_API_KEY. Pipeline logic is validated but claim-pipeline-valid remains BLOCKED until live API trials are run. This is an honest environment gate, not an attempt to bypass the requirement."
    fp-no-compaction-triggered:
      status: rejected
      notes: "Even in dry-run mode, all 6/6 trials triggered compaction events (synthetic). The trial matrix and task templates are designed to reach the 80K threshold. Live mode would use compact_20260112 API with configurable threshold."
  uncertainty_markers:
    weakest_anchors:
      - "compact_20260112 API behavior in live mode completely untested — dry-run validates pipeline only"
      - "N=6 pilot is too small for any statistical conclusion (by design — pilot validates pipeline)"
    unvalidated_assumptions:
      - "Token estimates assume ~700 tokens per LLM response — actual responses may be longer or shorter"
      - "Cost estimate ($2-5/trial) is approximate — actual costs depend on model response length and compaction behavior"
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-pipeline-valid
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    metric: "pipeline completion rate and schema validity"
    threshold: ">= 4/6 trials complete with valid JSONL"
    verdict: inconclusive
    recommended_action: "Set ANTHROPIC_API_KEY and re-run: python3 tools/run_pilot_track_a.py"
    notes: "Pipeline logic validated in dry-run. Live API validation pending environment gate resolution."
  - subject_id: claim-pilot-magnitude
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-knowledge-objects
    comparison_kind: baseline
    metric: "artifact_id_survival vs 0.4 Knowledge Objects threshold"
    threshold: "survival != 0 AND survival != 1 (measurable range)"
    verdict: inconclusive
    recommended_action: "Run live pilot to obtain genuine magnitude estimates"
    notes: "Dry-run survival=0.25 is from deterministic midpoint split, not genuine LLM behavior."
  - subject_id: claim-pilot-magnitude
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-v1-simulated
    comparison_kind: prior_work
    metric: "structural_reachability vs v1.0 simulated (0.82 at 50% deletion)"
    threshold: "reachability in plausible range [0, 1]"
    verdict: inconclusive
    recommended_action: "Match compression ratio from live pilot to simulated deletion percentage for fair comparison"
    notes: "Dry-run reachability=0.25 is not comparable to v1.0 simulated results."

duration: 8min
completed: 2026-03-28
---

# Phase 6 Plan 03: Pilot Track A Execution Summary

**Built and dry-run-validated pilot Track A runner (6 trials, 3 categories, provenance-aware toggle); live API execution blocked by missing ANTHROPIC_API_KEY — go/no-go deferred**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T04:30:00Z
- **Completed:** 2026-03-28T04:38:00Z
- **Tasks:** 2/2 (Task 1 executed + dry-run; Task 2 checkpoint executed with auto-assessment)
- **Files created:** 4

## Key Results

- **Pipeline validated in dry-run:** 6/6 trials complete, all metrics in valid ranges, JSONL schema correct, analysis + report auto-generated [CONFIDENCE: HIGH — pipeline logic validated, but live API behavior untested]
- **Dry-run metrics (synthetic, deterministic):** survival=0.25, reachability=0.25, degraded_fraction=0.25, compression_ratio=214.55, semantic_fidelity=0.0161 [CONFIDENCE: HIGH for pipeline correctness; N/A for genuine compaction behavior]
- **Go/no-go: BLOCKED** — dry-run only, live API required. Pipeline passes 3/4 criteria (pipeline_valid, compaction_fires, metrics_measurable) but fails live_mode criterion.
- **Environment gate:** ANTHROPIC_API_KEY not set. Forbidden proxy fp-dry-run-only is triggered. Both claims remain BLOCKED.
- **Full regression suite:** 789 passed, 4 skipped, 0 failures (no regressions from Plan 01/02 tools)

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute 6 pilot Track A trials with live API (dry-run due to env gate)** - `520ba85` (implement)

**Note:** Task 2 (checkpoint:human-verify) was executed automatically per subagent protocol. Analysis and report were generated as part of Task 1's pipeline. Go/no-go assessed using quantitative thresholds.

## Files Created/Modified

- `tools/run_pilot_track_a.py` — Pilot execution script: 6-trial matrix, cost guards, analysis, report generation
- `data/compaction/genuine/pilot-results.jsonl` — 6-line JSONL, dry-run mode, valid schema
- `data/compaction/genuine/pilot-analysis.json` — Aggregated statistics with anchor comparisons
- `docs/pilot-report.md` — Full pilot report with all required sections

## Next Phase Readiness

- **Pilot runner ready for live execution:** `python3 tools/run_pilot_track_a.py` (requires ANTHROPIC_API_KEY)
- **Analysis pipeline validated:** analyze_pilot() and write_pilot_report() work correctly on JSONL data
- **All three anchor comparisons coded:** MockLM ceiling, Knowledge Objects 60% loss, v1.0 simulated
- **Cost guards active:** $50 limit, per-trial cost estimation, running total
- **Blocker for Plan 04/05:** Plans 04 (Track B) and 05 (Track C) depend on go/no-go from this plan. Until ANTHROPIC_API_KEY is provisioned and live pilot runs, downstream plans should not proceed with live experiments.
- **No blocking for Plan 04 infrastructure:** Track B infrastructure (SWE-Bench integration) can be built independently.

## Contract Coverage

- Claim IDs: claim-pipeline-valid -> blocked (dry-run only), claim-pilot-magnitude -> blocked (dry-run only)
- Deliverable IDs: deliv-pilot-runner -> passed, deliv-pilot-results -> partial (dry-run), deliv-pilot-analysis -> partial (dry-run), deliv-pilot-report -> partial (dry-run)
- Acceptance tests: test-pipeline-live -> blocked (env gate), test-magnitude-estimate -> blocked (env gate)
- Reference IDs surfaced: ref-mock-experiment -> compared, ref-knowledge-objects -> compared, ref-v1-simulated -> compared
- Forbidden proxies: fp-dry-run-only -> VIOLATED (environment gate), fp-no-compaction-triggered -> rejected (6/6 fire events)
- Decisive comparison verdicts: all -> inconclusive (dry-run data is not genuine)

## Validations Completed

- JSONL schema: all 6 lines have required fields (trial_id, track, task_category, model, mode, provenance_aware, threshold, compaction_events, aggregate_metrics)
- Metric ranges: structural_reachability in [0,1], artifact_id_survival in [0,1], degraded_fraction in [0,1], compression_ratio > 0
- Analysis JSON structure: 7 top-level keys (pilot_summary, global_statistics, per_category, provenance_aware_delta, anchor_comparisons, tier_distribution, go_nogo)
- Report sections: go/no-go, global stats, per-category, provenance-aware delta, 3 anchor comparisons, tier distribution, variance estimate, limitations
- All tool imports work: genuine_compaction_runner, task_templates, summary_parser, embedding_similarity
- Full regression: 789 passed, 4 skipped, 0 failures
- Dry-run metrics consistent with midpoint-split design: survival = 5/20 = 0.25 (5 IDs in summary out of 20 total)

## Decisions & Deviations

### Decisions Made

1. **Automatic go/no-go assessment:** Used quantitative thresholds from plan (>= 4 complete, >= 4 compaction events, metrics in measurable range, live mode required). No subjective judgment applied. Result: BLOCKED due to dry-run only.
2. **Task 2 auto-execution:** Plan marked Task 2 as checkpoint:human-verify, but subagent protocol requires automatic execution with quantitative thresholds. Analysis and report generated; go/no-go computed mechanically.
3. **Honest forbidden proxy reporting:** fp-dry-run-only marked as VIOLATED (not rejected or unresolved) because the plan explicitly forbids dry-run-only pipeline validation for claim-pipeline-valid.

### Deviations from Plan

**None.** Plan executed as written. The environment gate (ANTHROPIC_API_KEY not set) is an external constraint, not a deviation. The plan's environment_requirements section correctly specified ANTHROPIC_API_KEY as required.

---

**Total deviations:** 0
**Impact on plan:** Environment gate blocks live execution. Pipeline infrastructure is complete and ready for live trials.

## Issues Encountered

1. **Environment gate: ANTHROPIC_API_KEY not set.** This is the primary blocker. The runner correctly detects the missing key, falls back to dry-run mode, and prints a clear warning message. Resolution: Set ANTHROPIC_API_KEY environment variable and re-run.

## User Setup Required

To execute live pilot trials:

1. Set `ANTHROPIC_API_KEY` environment variable with a valid Anthropic API key
2. Run: `python3 tools/run_pilot_track_a.py`
3. Estimated cost: $12-30 for 6 pilot trials
4. Expected duration: 15-30 minutes (API calls are sequential)

## Open Questions

- Will compact_20260112 API behave as documented when triggered at 80K tokens? (Only live trials can answer)
- Will genuine LLM compaction produce non-uniform metrics across categories? (Dry-run data is uniform by design)
- Will provenance-aware instructions improve artifact_id_survival? (Dry-run shows zero delta because synthetic compaction ignores instructions)
- Is 20 iterations sufficient to reach 80K token threshold with Sonnet responses? (Depends on model verbosity)

## Self-Check: PASSED

- [x] tools/run_pilot_track_a.py exists
- [x] data/compaction/genuine/pilot-results.jsonl exists (6 lines)
- [x] data/compaction/genuine/pilot-analysis.json exists
- [x] docs/pilot-report.md exists
- [x] Commit 520ba85 exists (Task 1)
- [x] JSONL schema validated (all required fields present)
- [x] Metric ranges validated (all in [0,1] or >0 as required)
- [x] Report has all required sections (go/no-go, per-category, anchors, variance)
- [x] Full regression: 789 passed, 4 skipped, 0 failures
- [x] Convention consistency: artifact ID format matches CONVENTIONS.md #5
- [x] All contract IDs covered in contract_results
- [x] All forbidden proxies explicitly addressed
- [x] All must-surface references have completed actions
- [x] All comparison_verdicts entries present (none omitted)
- [x] Go/no-go computed with quantitative thresholds (not subjective)

---

_Phase: 06-genuine-compaction, Plan: 03_
_Completed: 2026-03-28_
