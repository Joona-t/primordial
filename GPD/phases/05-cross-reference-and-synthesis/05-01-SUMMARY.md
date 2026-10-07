---
phase: 05-cross-reference-and-synthesis
plan: 01
depth: full
one-liner: "Built programmatic synthesis pipeline: loads Phase 2-4 JSON data, computes 12-row side-by-side table with MockLM ceiling/gap/differential, all 4 consistency checks pass, 39 validation tests green"
subsystem: [analysis, validation]
tags: [synthesis, cross-reference, side-by-side-table, gap-analysis, consistency-checks]

requires:
  - phase: 02-integration-and-baseline-establishment
    provides: Three-tier baseline metrics (uninstrumented, structured, forge)
  - phase: 03-violation-detection-campaign
    provides: Injection detection rates, FPR, natural violations, anchor comparison
  - phase: 04-compaction-survival-measurement
    provides: Structural reachability curve, backtracking threshold, violation regression

provides:
  - Side-by-side metrics table (12 observables x 6 columns) as JSON and Markdown
  - Gap computation for all 3 applicable MockLM-vs-forge observables
  - 4 automated consistency checks (three-tier ordering, pre-compaction match, detection sum, rate arithmetic)
  - Test suite with 39 tests covering data loading, table completeness, consistency, anchors, gap arithmetic

affects: [05-02-cross-reference-report]

methods:
  added: [programmatic JSON aggregation, dual-output synthesis (JSON + Markdown), gap classification]
  patterns: [load-compute-validate pipeline, source traceability annotation per row]

key-files:
  created:
    - tools/synthesis.py
    - tools/test_synthesis.py
    - data/synthesis/synthesis-report.json
    - data/synthesis/side-by-side-table.md

key-decisions:
  - "MockLM ceiling values hardcoded as benchmark anchors (not loaded from JSON) -- they are the reference standard"
  - "Compression ratio sourced from pre_compaction_baseline (1.1959x) rather than baseline-report (1.1793x) -- compaction-report is the Phase 4 canonical source"
  - "Gap direction: ceiling - forge for rates/reachability (higher is better), forge - ceiling for compression (lower is better)"

patterns-established:
  - "Every table value annotated with source_file and source_field for traceability"
  - "Consistency checks run automatically and embedded in JSON output"

conventions:
  - "N/A -- formal systems research, all metrics dimensionless ratios or counts"
  - "compaction_terminology: always qualified (forge trace compression vs simulated LLM compaction)"
  - "ci_method: Clopper-Pearson for boundary, Bootstrap percentile (B=10000, seed=42) for interior"

plan_contract_ref: "GPD/phases/05-cross-reference-and-synthesis/05-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-table-complete:
      status: passed
      summary: "12-row side-by-side table is complete and consistent: all observables populated for all applicable columns, every value traces to a specific JSON field via source_file/source_field annotations"
      linked_ids: [deliv-synthesis-script, deliv-synthesis-json, deliv-side-by-side-md]
      evidence:
        - verifier: automated-tests
          method: 39 pytest tests including table completeness, consistency, and integration
          confidence: high
          claim_id: claim-table-complete
    claim-anchor-surfaced:
      status: passed
      summary: "MockLM ceiling surfaced in rows 1 (6/6 detection), 6 (1.0 reachability), 10 (1.096x compression) with gap computation for all three"
      linked_ids: [deliv-synthesis-json, deliv-side-by-side-md]
      evidence:
        - verifier: automated-tests
          method: TestAnchor and TestGapArithmetic test classes
          confidence: high
          claim_id: claim-anchor-surfaced
  deliverables:
    deliv-synthesis-script:
      status: passed
      path: "tools/synthesis.py"
      summary: "Python synthesis script with load_campaign_data(), load_compaction_data(), load_baseline_data(), compute_side_by_side_table(), compute_gaps(), JSON and Markdown output"
      linked_ids: [claim-table-complete]
    deliv-synthesis-json:
      status: passed
      path: "data/synthesis/synthesis-report.json"
      summary: "Machine-readable synthesis report with side_by_side_table, gaps, mockLM_ceiling, consistency_checks, and source_files"
      linked_ids: [claim-table-complete, claim-anchor-surfaced]
    deliv-side-by-side-md:
      status: passed
      path: "data/synthesis/side-by-side-table.md"
      summary: "Human-readable Markdown table with 7 columns, gap analysis section, consistency checks section, and source traceability table"
      linked_ids: [claim-table-complete, claim-anchor-surfaced]
    deliv-synthesis-tests:
      status: passed
      path: "tools/test_synthesis.py"
      summary: "39-test suite covering data loading (13), table completeness (4), consistency (7), anchors (4), gap arithmetic (7), integration (4)"
      linked_ids: [claim-table-complete, claim-anchor-surfaced]
  acceptance_tests:
    test-data-consistency:
      status: passed
      summary: "All table values match source JSON exactly -- programmatic loading ensures no transcription error. Verified by test_source_traceability_complete and test_no_none_values"
      linked_ids: [deliv-synthesis-json, ref-campaign-data, ref-compaction-data, ref-baseline-data]
    test-three-tier-ordering:
      status: passed
      summary: "forge >= structured >= uninstrumented holds for all 9 fault types (detection rate), reachability, and provenance depth"
      linked_ids: [deliv-synthesis-json, ref-baseline-data]
    test-anchor-match:
      status: passed
      summary: "MockLM ceiling values in table: 6/6 (row 1), 1.0 (row 6), 1.096x (row 10). Gaps: 3 types (D1-D6), 0.0 (reachability), 0.0999x (compression). All gaps computed, none cherry-picked."
      linked_ids: [deliv-synthesis-json, ref-mock-experiment]
    test-detection-rate-consistency:
      status: passed
      summary: "sum(per_type_detected) = 40 = aggregate_detected. 40/90 = 0.4444 matches aggregate rate exactly."
      linked_ids: [deliv-synthesis-json, ref-campaign-data]
    test-pre-compaction-match:
      status: passed
      summary: "Phase 2 baseline reachability (1.0) = Phase 4 pre-compaction reachability (1.0) = MockLM ceiling (1.0). Three-way match confirmed."
      linked_ids: [deliv-synthesis-json, ref-compaction-data, ref-baseline-data, ref-mock-experiment]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM ceiling surfaced in 3 table rows with gap computation for each. All gaps classified (zero or explained)."
    ref-campaign-data:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "campaign-report.json loaded programmatically. Per-type rates, aggregate, clean summary, and anchor comparison all consumed."
    ref-compaction-data:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "compaction-report.json loaded programmatically. Pre-compaction baseline, deletion sweep, violation regression, and backtracking threshold all consumed."
    ref-baseline-data:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "baseline-report.json loaded programmatically. Three-tier metrics (uninstrumented, structured, forge) all consumed."
  forbidden_proxies:
    fp-manual-transcription:
      status: rejected
      notes: "All values loaded programmatically via load_*_data() functions. No manual copying from SUMMARY.md files. Traceability annotations (source_file, source_field) in every row."
    fp-missing-gaps:
      status: rejected
      notes: "All 3 applicable gaps computed: D1-D6 detection (gap=3, explained), pre-compaction reachability (gap=0, zero), compression (gap=0.0999, explained). No cherry-picking."
  uncertainty_markers:
    weakest_anchors:
      - "MockLM compression ratio (1.096x) measured on controlled test data; real forge compression (1.1959x) measured on different data structure"
    unvalidated_assumptions: []
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-anchor-surfaced
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    metric: gap_computation
    threshold: "all applicable gaps computed"
    verdict: pass
    recommended_action: "None -- all gaps computed and classified"
    notes: "3/3 applicable gaps: D1-D6 detection (3 types, explained), reachability (0, zero), compression (0.0999x, explained)"

duration: 5min
completed: 2026-03-16
---

# Phase 5 Plan 01: Synthesis Script Summary

**Built programmatic synthesis pipeline: loads Phase 2-4 JSON data, computes 12-row side-by-side table with MockLM ceiling/gap/differential, all 4 consistency checks pass, 39 validation tests green**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-16T03:52:38Z
- **Completed:** 2026-03-16T03:57:08Z
- **Tasks:** 2
- **Files modified:** 4

## Key Results

- Side-by-side table with 12 observables x 6 comparison columns, all populated programmatically from source JSON
- MockLM ceiling surfaced with gap computation for all 3 applicable observables: D1-D6 detection (gap=3, explained), reachability (gap=0), compression (gap=0.0999x, explained)
- 4/4 consistency checks pass: three-tier ordering, pre-compaction match, detection rate sum, rate arithmetic
- 39/39 validation tests pass across 6 test categories

## Task Commits

Each task was committed atomically:

1. **Task 1: Build synthesis script with data loading, table computation, and dual output** - `0e64b34` (implement)
2. **Task 2: Write synthesis validation tests and run full consistency check** - `3dfff7f` (validate)

## Files Created/Modified

- `tools/synthesis.py` - Synthesis script: loads 3 JSON sources, computes 12-row table, outputs JSON + Markdown
- `tools/test_synthesis.py` - 39 tests covering data loading, table completeness, consistency, anchors, gap arithmetic, integration
- `data/synthesis/synthesis-report.json` - Machine-readable synthesis report
- `data/synthesis/side-by-side-table.md` - Human-readable Markdown comparison table

## Next Phase Readiness

- Side-by-side table ready for Plan 02 cross-reference report
- Consistency checks embedded in JSON output for downstream verification
- All source traceability annotations in place for audit trail

## Contract Coverage

- Claim IDs advanced: claim-table-complete -> passed, claim-anchor-surfaced -> passed
- Deliverable IDs produced: deliv-synthesis-script -> passed, deliv-synthesis-json -> passed, deliv-side-by-side-md -> passed, deliv-synthesis-tests -> passed
- Acceptance test IDs run: test-data-consistency -> passed, test-three-tier-ordering -> passed, test-anchor-match -> passed, test-detection-rate-consistency -> passed, test-pre-compaction-match -> passed
- Reference IDs surfaced: ref-mock-experiment -> compared, ref-campaign-data -> read, ref-compaction-data -> read, ref-baseline-data -> read
- Forbidden proxies rejected: fp-manual-transcription -> rejected, fp-missing-gaps -> rejected
- Decisive comparison verdicts: claim-anchor-surfaced -> pass (all 3 gaps computed and classified)

## Validations Completed

- Table completeness: 12 rows, no None values, all 9 columns present, unique observable names
- Three-tier ordering: forge >= structured >= uninstrumented for detection rates (all 9 types), reachability, provenance depth
- Pre-compaction match: Phase 2 baseline = Phase 4 pre-compaction = MockLM ceiling = 1.0
- Detection rate arithmetic: sum(per_type_detected) = 40 = aggregate_detected; 40/90 = 0.4444 exact match
- Gap arithmetic: D1-D6 = 6-3 = 3; reachability = 1.0-1.0 = 0; compression = 1.1959-1.096 = 0.0999
- Source traceability: every row annotated with source_file and source_field
- Error handling: FileNotFoundError on missing files, ValueError on malformed JSON

## Decisions Made

- MockLM ceiling values hardcoded as benchmark anchors (the reference standard), all other values loaded from JSON
- Compression ratio sourced from compaction-report pre_compaction_baseline (1.1959x) as the Phase 4 canonical measurement
- Gap direction convention: ceiling - forge for higher-is-better metrics, forge - ceiling for compression

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## Key Quantities and Uncertainties

| Quantity | Symbol | Value | Uncertainty | Source | Valid Range |
| --- | --- | --- | --- | --- | --- |
| Forge D1-D6 detection (types) | - | 3/6 | exact count | campaign-report.json | D1-D6 |
| Forge D1-D9 detection (types) | - | 4/9 | exact count | campaign-report.json | D1-D9 |
| Aggregate detection rate | - | 0.4444 | CI [0.344, 0.544] | campaign-report.json | 90 injections |
| Pre-compaction reachability | - | 1.0 | CP CI [0.292, 1.0] | compaction-report.json | pre-compaction |
| Structural reachability @ 50% | - | 0.8214 | deterministic | compaction-report.json | 50% deletion |
| Structural reachability @ 80% | - | 0.4375 | deterministic | compaction-report.json | 80% deletion |
| Forge compression ratio | - | 1.1959x | CV=0.0 | compaction-report.json | OpenClaw ledger |
| Provenance depth | - | 21 | exact count | baseline-report.json | single ledger |

---

_Phase: 05-cross-reference-and-synthesis, Plan: 01_
_Completed: 2026-03-16_
