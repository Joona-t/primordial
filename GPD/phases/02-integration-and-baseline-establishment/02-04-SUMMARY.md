---
phase: 02-integration-and-baseline-establishment
plan: 04
depth: full
one-liner: "Three-tier baseline measurement on real Zarathustra ledger data: uninstrumented floor confirmed, forge reachability 1.0, trace compression 1.18x, 6 cursor state loss events detected"
subsystem: validation
tags: [baseline, measurement, three-tier, forge, provenance, cursor-reset, bootstrap-ci]

requires:
  - phase: 02-integration-and-baseline-establishment (Plan 02-02)
    provides: OpenClaw adapter (openclaw_adapter.py) for forge-instrumented tier
  - phase: 02-integration-and-baseline-establishment (Plan 02-03)
    provides: Task corpus, measurement framework, structured logging baseline
provides:
  - Baseline measurement data across all three tiers (data/baselines/)
  - Machine-readable baseline report (data/baselines/baseline-report.json)
  - Human-readable comparison report (docs/baseline-report.md)
  - Measurement pipeline script (tools/run_baseline_measurement.py)
affects: [phase-3-violation-detection, phase-4-compaction-survival]

methods:
  added: [post-hoc-ledger-measurement, cursor-reset-detection, three-tier-comparison]
  patterns: [bootstrap-ci-on-deterministic-data, forge-vs-mocklm-gap-analysis]

key-files:
  created:
    - tools/run_baseline_measurement.py
    - docs/baseline-report.md
    - data/baselines/baseline-report.json
    - data/baselines/uninstrumented/ (3 run files + metrics.json)
    - data/baselines/structured-logging/ (3 run files + metrics.json)
    - data/baselines/forge-instrumented/ (3 run files + metrics.json)

key-decisions:
  - "vs_vanilla_pct sign reversal explained: chamber metadata (+460%) vs trace compression (-87%) measure different things"
  - "Cursor resets (6 detected) are queue-worker state loss events, NOT LLM context-window compaction"
  - "Clean data produces zero violations across all tiers (correct behavior, not a deficiency)"

patterns-established:
  - "Deterministic pipeline: same input -> identical metrics across runs (CV=0% on all primary metrics)"
  - "Cursor reset detection: queue_byte_start=0 after task.done = state loss event"
  - "Forge trace compression on real data (1.18x) slightly exceeds MockLM ceiling (1.10x)"

conventions:
  - "All uses of 'compaction' qualified per Convention #6 (terminology audit passed)"
  - "Metrics formulas match CONVENTIONS.md #7 exactly"
  - "Bootstrap 95% CIs with fixed seed (42) for reproducibility"

plan_contract_ref: "GPD/phases/02-integration-and-baseline-establishment/02-04-PLAN.md#/contract"
contract_results:
  claims:
    claim-baseline-measured:
      status: partial
      summary: "Uninstrumented and structured logging baselines measured on real ledger sample data. Floor established (reachability=0, detection=0). Structured logging intermediate position confirmed. Methodology validated. PARTIAL because: (a) data is from one ledger sample, not full task corpus execution on VM, (b) no LLM compaction events observed (data too short), (c) detection_rate requires violation injection (Phase 3)."
      linked_ids: [deliv-baseline-data, deliv-baseline-report, test-reproducible, test-floor-established]
    claim-forge-baseline-measured:
      status: partial
      summary: "Forge-instrumented baseline produces valid chambers with reachability=1.0, provenance depth=21, trace compression=1.18x. All chambers pass validate_chamber(). PARTIAL because full task corpus execution on VM is pending."
      linked_ids: [deliv-baseline-data, deliv-baseline-report, test-forge-chambers-valid, test-forge-provenance-positive]
  deliverables:
    deliv-baseline-data:
      status: produced
      path: "data/baselines/"
      summary: "13 files: 3 per-run results per tier + 3 tier metrics + 1 aggregate report JSON"
      linked_ids: [claim-baseline-measured, claim-forge-baseline-measured]
    deliv-baseline-report:
      status: produced
      path: "docs/baseline-report.md"
      summary: "Side-by-side metrics table, gap analysis for all 5 metrics vs MockLM ceiling, forbidden proxy audit, cursor state loss analysis, Phase 3 readiness assessment"
      linked_ids: [claim-baseline-measured, claim-forge-baseline-measured]
  acceptance_tests:
    test-reproducible:
      status: passed
      summary: "CV=0.0% for all primary metrics (reachability, detection) across all tiers. Pipeline is deterministic on same input data."
      linked_ids: [claim-baseline-measured, deliv-baseline-data]
    test-compaction-triggered:
      status: not-yet-testable
      summary: "No LLM compaction events in sample data (47 events, ~2.5K tokens -- far below 128K threshold). Requires VM execution of LONG tasks. 6 cursor resets (queue-worker state loss) detected as mitigation."
      linked_ids: [claim-baseline-measured]
    test-floor-established:
      status: passed
      summary: "Uninstrumented: reachability=0.0, detection=0. Structured logging: detection=0 on clean data, reachability=0.0. Floor values match ref-vanilla-baseline-prior exactly."
      linked_ids: [claim-baseline-measured, deliv-baseline-data, deliv-baseline-report]
    test-anchor-comparison:
      status: partial
      summary: "Forge reachability=1.0 matches MockLM ceiling (no LLM compaction in sample). Forge trace compression=1.18 exceeds MockLM mean=1.10. Detection comparison requires violation injection (Phase 3). vs_vanilla_pct sign reversal documented."
      linked_ids: [deliv-baseline-report]
    test-forge-chambers-valid:
      status: passed
      summary: "validate_chamber() returns [] (zero errors) on all 3 forge-instrumented runs (100% pass rate)."
      linked_ids: [claim-forge-baseline-measured, deliv-baseline-data]
    test-forge-provenance-positive:
      status: passed
      summary: "reachability_fraction=1.0 on all forge-instrumented runs. Provenance depth=21 (all chains reach root)."
      linked_ids: [claim-forge-baseline-measured, deliv-baseline-data]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "MockLM ceiling values compared: reachability EXACT match (1.0), detection N/A (clean data), trace compression forge exceeds (+0.08), false positives EXACT match (0.0). vs_vanilla_pct sign reversal explained."
    ref-vanilla-baseline-prior:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "Vanilla floor values match exactly: reachability=0.0, violations=0, no provenance, no hashing."
  forbidden_proxies:
    fp-short-tasks:
      status: partially-addressed
      notes: "Sample data too short for LLM compaction. Task corpus has 3 LONG tasks targeting 128K+ tokens. 6 cursor resets (queue-worker state loss) observed as structural state loss coverage."
    fp-shallow-traces:
      status: rejected
      notes: "Maximum provenance depth=21 (far exceeds minimum of 3). Not trivially shallow."
    fp-self-report:
      status: rejected
      notes: "All metrics computed from independent structural analysis (BFS reachability, validate_chamber, trace_stats, verify_trace). No self-reported metrics."
  uncertainty_markers:
    weakest_anchors:
      - "Sample data is 47 events from one session -- not statistically representative of the full task corpus"
      - "No LLM compaction events in sample data -- compaction survival measurement deferred to VM execution"
      - "Detection rate is 0/0 on clean data -- violation injection needed for meaningful detection comparison"
    unvalidated_assumptions:
      - "Pipeline will produce identical results on full VM task data (not yet tested)"
      - "vs_vanilla_pct metric needs standardized comparison basis (documented in gap analysis)"
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-baseline-measured
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-vanilla-baseline-prior
    comparison_kind: floor
    metric: reachability_fraction
    threshold: "uninstrumented = 0.0"
    verdict: pass
    recommended_action: "None -- floor confirmed"
    notes: "Exact match with prior vanilla baseline"
  - subject_id: claim-forge-baseline-measured
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-mock-experiment
    comparison_kind: ceiling
    metric: reachability_fraction
    threshold: "forge reachability <= 1.0"
    verdict: pass
    recommended_action: "Test with LLM compaction data in Phase 4"
    notes: "forge=1.0 matches MockLM ceiling (no LLM compaction in sample)"
  - subject_id: claim-forge-baseline-measured
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-mock-experiment
    comparison_kind: ceiling
    metric: compression_ratio
    threshold: "forge compression comparable to MockLM ~1.10"
    verdict: pass
    recommended_action: "None -- forge 1.18 slightly exceeds MockLM 1.10"
    notes: "Real data has more structural repetition, enabling better dedup"

duration: 15min
completed: 2026-03-16
---

# Plan 02-04: Three-Tier Baseline Measurement Summary

**Three-tier baseline measurement on real Zarathustra ledger data: uninstrumented floor confirmed, forge reachability 1.0, forge trace compression 1.18x, 6 cursor state loss events detected**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 auto + 1 checkpoint (checkpoint reached)
- **Files created:** 16 (1 script + 1 report + 13 data files + 1 summary)

## Key Results

| Metric | Uninstrumented | Struct. Logging | Forge | MockLM Ceiling |
|---|---|---|---|---|
| reachability | 0.0 | 0.0 | **1.0** | 1.0 |
| detection | 0 | 0 | 0 (clean data) | 6/6 |
| forge trace compression | N/A | N/A | **1.18** | ~1.10 |
| vs_vanilla_pct | 0% | +84.6% | +460.5% | -87.4% |
| false_positive | N/A | 0.0 | 0.0 | 0.0 |

- Provenance depth: 21 (deep chain across 21 task lifecycle groups)
- Cursor resets detected: 6 (all resume-type state loss events)
- Chamber validation: 0 errors on all 3 runs (100% pass rate)
- Trace round-trip verification: all runs pass (hash match + content match)
- Reproducibility: CV=0.0% for all primary metrics

## Task Commits

1. **Task 1: Three-Tier Baseline Measurement** -- `5e95005` (implement)
2. **Task 2: Baseline Report with Gap Analysis** -- `a77eeb5` (docs)
3. **Task 3: Verification Checkpoint** -- this summary

## Files Created/Modified

- `tools/run_baseline_measurement.py` -- Three-tier measurement pipeline (reusable for VM data)
- `docs/baseline-report.md` -- Human-readable report with comparison table, gap analysis, forbidden proxy audit
- `data/baselines/baseline-report.json` -- Machine-readable aggregate metrics
- `data/baselines/uninstrumented/` -- 3 per-run results + tier metrics
- `data/baselines/structured-logging/` -- 3 per-run results + tier metrics
- `data/baselines/forge-instrumented/` -- 3 per-run results + tier metrics

## Deviations from Plan

### Deviation 1: [Rule 3 - Approximation Adaptation] Sample data instead of live VM execution

- **Trigger:** OpenClaw runs on a separate VM, not accessible from this machine
- **Action:** Used existing real ledger sample data (47 events from Zarathustra) as measurement input instead of live task execution
- **Impact:** Methodology validated end-to-end. LLM compaction testing deferred to when VM access is available. All other acceptance tests pass.
- **Recovery:** Same pipeline processes VM task data without modification

### Deviation 2: [Rule 4 - Missing Component] vs_vanilla_pct comparison basis mismatch

- **Trigger:** MockLM vs_vanilla_pct compared trace-vs-verbose-logger (-87%); real baseline compares chamber-vs-raw-events (+460%)
- **Action:** Documented the sign reversal with full explanation in gap analysis. Recommended standardizing comparison basis.
- **Impact:** vs_vanilla_pct metric requires interpretation note; not directly comparable between MockLM and real baselines without stating the comparison basis.

## Open Questions

- When will the VM be available for full task corpus execution? (Required for test-compaction-triggered)
- Should vs_vanilla_pct be redefined to compare forge trace (compressed) vs raw events, for consistency with MockLM experiment?
- Will Phase 3 violation injection be against this same sample data or against live VM execution data?

## Contract Coverage

- Claim IDs: claim-baseline-measured -> partial, claim-forge-baseline-measured -> partial
- Deliverable IDs: deliv-baseline-data -> produced, deliv-baseline-report -> produced
- Acceptance tests: test-reproducible -> passed, test-floor-established -> passed, test-forge-chambers-valid -> passed, test-forge-provenance-positive -> passed, test-compaction-triggered -> not-yet-testable, test-anchor-comparison -> partial
- References: ref-mock-experiment -> read+compare, ref-vanilla-baseline-prior -> read+compare
- Forbidden proxies: fp-short-tasks -> partially-addressed, fp-shallow-traces -> rejected, fp-self-report -> rejected
- Comparison verdicts: floor (vanilla) -> pass, ceiling (MockLM reachability) -> pass, ceiling (MockLM compression) -> pass

---

_Phase: 02-integration-and-baseline-establishment_
_Plan: 04_
_Status: Checkpoint reached (awaiting verification)_
_Completed: 2026-03-16_
