---
phase: 03-violation-detection-campaign
plan: 02
depth: full
one-liner: "D1-D9 injection campaign detects 4/9 fault types (44.4%); zero natural violations on 30 clean runs (CP upper bound 11.6%); FPR = 0.0%; three-tier ordering confirmed for all 9 types"
subsystem: [validation, analysis]
tags: [fault-injection, detection-campaign, three-tier-comparison, false-positive-rate, violation-detection]

requires:
  - phase: 03-violation-detection-campaign/03-01
    provides: "FaultInjector (D1-D9), DetectionCampaign orchestrator, CI framework, D7-D9 calibration"
  - phase: 02-integration-and-baseline-establishment/02-04
    provides: "Three-tier baselines (uninstrumented=0.0, forge reachability=1.0, compression=1.18x)"
provides:
  - "D1-D9 detection rates per tier with 95% CIs (campaign-report.json)"
  - "Aggregate forge detection rate: 0.444 [0.344, 0.544] on injected faults"
  - "Differential detection: +0.444 (forge vs uninstrumented/structured)"
  - "Natural violation count: 0 (CP upper bound 11.6% at 0/30)"
  - "False positive rate: 0.0 (0/30, CP upper bound 11.6%)"
  - "MockLM anchor comparison: 3/6 D1-D6 post-hoc vs 6/6 registration-time"
  - "D7-D9 gap analysis: D9 detected (seal enforcement), D7/D8 undetectable by structural validation"
  - "Violation report (docs/violation-report.md)"
affects: [04-compaction-survival, 05-synthesis-and-writeup]

methods:
  added: [fault-injection-campaign, three-tier-differential-detection, clopper-pearson-boundary-ci]
  patterns: [post-hoc-chamber-validation, injected-vs-natural-separation, forbidden-proxy-audit]

key-files:
  created:
    - data/campaign/injection-results.json
    - data/campaign/clean-results.json
    - data/campaign/campaign-report.json
    - docs/violation-report.md
  modified: []

key-decisions:
  - "CC-009: Post-hoc injection reveals architectural gap vs MockLM registration-time detection (3/6 D1-D6 vs 6/6). Gap is real, not a bug."
  - "CC-010: D7/D8 gaps are findings about forge coverage limitations, not test failures."
  - "Accepted negative finding on natural violations: forge mechanism proven on injected faults; natural violations are zero on this sample."

patterns-established:
  - "Injected vs natural detection ALWAYS tallied separately (fp-synthetic-only enforcement)"
  - "Clopper-Pearson exact binomial CI for boundary proportions (0/n or n/n)"
  - "Bootstrap percentile CI (B=10000, seed=42) for interior proportions"

conventions:
  - "All metrics dimensionless ratios in [0, 1] or non-negative integer counts"
  - "CI method: Clopper-Pearson for boundary, bootstrap for interior"
  - "Natural vs injected strictly separated in all metrics"
  - "Compaction always qualified: forge trace compression vs LLM context-window compaction"

plan_contract_ref: "GPD/phases/03-violation-detection-campaign/03-02-PLAN.md#/contract"
contract_results:
  claims:
    claim-violation-detection:
      status: partial
      summary: "Forge detects 4/9 structural fault types (D1, D2, D5, D9) on injected faults with differential +0.444 vs baselines, CI excluding zero. Three-tier ordering holds for all 9 types. However, zero natural violations surfaced on 30 clean runs. Mechanism validated; practical value on this sample is unproven."
      linked_ids: [deliv-violation-report, deliv-campaign-data, test-real-violation, test-differential-detection, test-fpr-acceptable, ref-mock-experiment, ref-baseline-data, ref-plan-03-01]
      evidence:
        - verifier: executor
          method: injection campaign + clean campaign
          confidence: high
          claim_id: claim-violation-detection
          deliverable_id: deliv-violation-report
          acceptance_test_id: test-differential-detection
          reference_id: ref-mock-experiment
          evidence_path: "data/campaign/campaign-report.json"
  deliverables:
    deliv-violation-report:
      status: passed
      path: "docs/violation-report.md"
      summary: "Human-readable report with all 8 required sections: executive summary, injection results with D1-D9 table, natural violation assessment (0 with CP bound), FPR, MockLM anchor comparison table, forbidden proxy audit, methodology, limitations."
      linked_ids: [claim-violation-detection, test-real-violation, test-differential-detection]
    deliv-campaign-data:
      status: passed
      path: "data/campaign/"
      summary: "Machine-readable campaign data: injection-results.json (90 injection records), clean-results.json (30 clean runs), campaign-report.json (aggregate metrics with CIs, anchor comparison, forbidden proxy audit)."
      linked_ids: [claim-violation-detection, test-differential-detection, test-fpr-acceptable]
  acceptance_tests:
    test-real-violation:
      status: failed
      summary: "NEGATIVE FINDING: Zero naturally-occurring violations detected after 30 clean runs. Clopper-Pearson 95% upper bound on natural violation rate: 11.6%. Result honestly reported; injected detections NOT conflated with natural. User accepted negative finding."
      linked_ids: [claim-violation-detection, deliv-campaign-data, deliv-violation-report, ref-mock-experiment]
    test-differential-detection:
      status: passed
      summary: "Differential detection rate delta = +0.444, bootstrap 95% CI [0.344, 0.544] excludes zero. Forge detects strictly more than uninstrumented and structured baselines. Three-tier ordering holds for all 9 fault types."
      linked_ids: [claim-violation-detection, deliv-campaign-data, ref-baseline-data]
    test-fpr-acceptable:
      status: passed
      summary: "FPR = 0.0% (0/30 clean runs). Clopper-Pearson 95% CI [0.000, 0.116]. FPR < 5% criterion satisfied. Zero false alarms on real data."
      linked_ids: [claim-violation-detection, deliv-campaign-data]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM ceiling (6/6 D1-D6, reachability=1.0, compression=1.096) compared against real data (3/6 D1-D6, reachability=1.0, compression=1.179) in violation report Section e. Gap explained as architectural (registration-time vs post-hoc validation)."
    ref-baseline-data:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "Phase 2 baselines (uninstrumented=0.0, structured=0.0 detection) used as comparison arms for three-tier differential. Differential +0.444 with CI excluding zero."
    ref-plan-03-01:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "FaultInjector and DetectionCampaign classes from Plan 03-01 used to execute the full campaign. D7-D9 calibration results confirmed."
  forbidden_proxies:
    fp-synthetic-only:
      status: rejected
      notes: "Natural violations assessed independently (Section c of report). Zero natural violations honestly reported as negative finding with Clopper-Pearson bound. Injected and natural tallied separately via separate_injected_natural(). Report does NOT conflate them."
    fp-short-tasks:
      status: rejected
      notes: "Campaign uses real Zarathustra ledger with 47 events, 6 cursor resets (multi-task sessions), 40+ stages. Task corpus design (CC-007) includes short (S1-S3) and long (L1-L3) patterns."
  uncertainty_markers:
    weakest_anchors:
      - "Natural violation frequency is unknown. 0/30 clean runs with CP upper bound 11.6%."
      - "Post-hoc validation misses 5/9 fault types that registration-time validation catches."
    unvalidated_assumptions:
      - "Natural violations may require longer sessions, more diverse tasks, or real LLM compaction to surface."
    competing_explanations:
      - "Zero natural violations could mean: (a) no structural failures in this sample, (b) post-hoc validation cannot detect the types that do occur, or (c) structural failures are genuinely rare in coding/patching tasks."
    disconfirming_observations:
      - "Zero natural violations weakens the practical value proposition on this sample."

comparison_verdicts:
  - subject_id: claim-violation-detection
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    metric: detection_rate_d1_d6
    threshold: "match MockLM 6/6"
    verdict: tension
    recommended_action: "Extend validate_chamber() to add hash re-verification (D3), ref correctness (D4), transition legality (D6) to close post-hoc gap."
    notes: "3/6 vs 6/6. Gap is architectural (post-hoc vs registration-time), not a quality deficiency."
  - subject_id: test-differential-detection
    subject_kind: acceptance_test
    subject_role: decisive
    reference_id: ref-baseline-data
    comparison_kind: baseline
    metric: differential_detection_rate
    threshold: "delta > 0, CI excludes zero"
    verdict: pass
    recommended_action: "No action needed. Differential is statistically significant."
    notes: "delta = +0.444, CI [0.344, 0.544]."
  - subject_id: test-real-violation
    subject_kind: acceptance_test
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    metric: natural_violation_count
    threshold: ">= 1"
    verdict: fail
    recommended_action: "Accept negative finding. Consider extended campaign on diverse data or Phase 4 compaction testing to surface natural violations."
    notes: "0 natural violations. CP 95% upper bound: 11.6%. User approved acceptance of negative finding."

duration: 50min
completed: 2026-03-16
---

# Phase 3 Plan 02: Violation Detection Campaign Summary

**D1-D9 injection campaign detects 4/9 fault types (44.4%); zero natural violations on 30 clean runs (CP upper bound 11.6%); FPR = 0.0%; three-tier ordering confirmed for all 9 types**

## Performance

- **Duration:** ~50 min (across 3 tasks including checkpoint)
- **Started:** 2026-03-16T01:30:00Z
- **Completed:** 2026-03-16T02:20:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint, approved)
- **Files modified:** 5 (4 created + 1 report)

## Key Results

- **Forge detection rate:** 40/90 = 44.4% [95% CI: 0.344, 0.544] on D1-D9 injected faults
- **Per-type detection:** D1, D2, D5, D9 at 100% (10/10 each). D3, D4, D6, D7, D8 at 0% (post-hoc validation gaps)
- **Differential detection:** +0.444 (forge vs uninstrumented/structured), CI excludes zero
- **D1-D6 vs MockLM ceiling:** 3/6 types (50%), gap is architectural (post-hoc vs registration-time)
- **Natural violations:** 0 detected (NEGATIVE FINDING, Clopper-Pearson upper bound 11.6%)
- **False positive rate:** 0.0% (0/30 clean runs, CP upper bound 11.6%)
- **Three-tier ordering:** Holds for all 9 fault types (forge >= structured >= uninstrumented)

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute D1-D9 injection campaign and clean campaign** - `0c07e35` (compute)
2. **Task 2: Produce violation report with anchor comparison** - `d11226c` (docs)
3. **Task 3: Verification checkpoint** - human-verify, user approved (no separate commit)

## Files Created/Modified

- `data/campaign/injection-results.json` - Per-injection detection records (90 injections, 9 types x 10)
- `data/campaign/clean-results.json` - Per-run validation output (30 clean runs)
- `data/campaign/campaign-report.json` - Aggregate metrics, CIs, anchor comparison, forbidden proxy audit
- `docs/violation-report.md` - Human-readable violation report with all 8 sections

## Next Phase Readiness

- **Phase 4 (compaction survival):** Campaign data and detection infrastructure ready. Key question: will LLM context-window compaction (vs cursor-based state loss tested here) surface natural violations?
- **Phase 5 (synthesis):** Violation report ready for writeup. The honest negative finding on natural violations, the detection mechanism validation, and the post-hoc gap analysis are all documented.
- **Potential improvement:** Extending `validate_chamber()` with hash re-verification (D3), ref correctness (D4), and transition legality (D6) could close the D1-D6 gap from 3/6 to 6/6.

## Contract Coverage

- **Claim IDs advanced:** claim-violation-detection -> partial (mechanism proven, natural violations negative)
- **Deliverable IDs produced:** deliv-violation-report -> passed, deliv-campaign-data -> passed
- **Acceptance test IDs run:** test-real-violation -> FAILED (negative finding, honestly reported), test-differential-detection -> PASSED, test-fpr-acceptable -> PASSED
- **Reference IDs surfaced:** ref-mock-experiment -> compared, ref-baseline-data -> compared, ref-plan-03-01 -> read
- **Forbidden proxies rejected:** fp-synthetic-only -> AVOIDED, fp-short-tasks -> AVOIDED
- **Decisive comparison verdicts:** MockLM ceiling -> tension (3/6 vs 6/6), differential detection -> pass, natural violations -> fail (0, accepted)

## Key Quantities and Uncertainties

| Quantity | Symbol | Value | Uncertainty | Source | Valid Range |
| -------- | ------ | ----- | ----------- | ------ | ----------- |
| Aggregate forge detection rate | delta_forge | 0.444 | CI [0.344, 0.544] | Bootstrap B=10000 | All D1-D9 |
| D1 forge detection rate | r_D1 | 1.000 | CI [0.692, 1.000] | Clopper-Pearson | n=10 |
| D2 forge detection rate | r_D2 | 1.000 | CI [0.692, 1.000] | Clopper-Pearson | n=10 |
| D5 forge detection rate | r_D5 | 1.000 | CI [0.692, 1.000] | Clopper-Pearson | n=10 |
| D9 forge detection rate | r_D9 | 1.000 | CI [0.692, 1.000] | Clopper-Pearson | n=10 |
| D3/D4/D6/D7/D8 forge rate | r_gap | 0.000 | CI [0.000, 0.308] | Clopper-Pearson | n=10 each |
| False positive rate | FPR | 0.000 | CI [0.000, 0.116] | Clopper-Pearson | n=30 |
| Natural violation rate | p_nat | 0.000 | CP upper bound 0.116 | Clopper-Pearson | 0/30 |
| Differential (forge - uninstr) | delta | +0.444 | CI [0.344, 0.544] | Bootstrap | n=90 |

## Validations Completed

- **Three-tier ordering:** Verified forge >= structured >= uninstrumented for all 9 fault types
- **CI sanity:** All CIs bounded in [0, 1], boundary CIs use Clopper-Pearson, interior CIs use bootstrap
- **Dimensional check:** All rates dimensionless in [0, 1], all counts non-negative integers
- **Separation check:** Injected and natural detections strictly separated in all metrics
- **Anchor comparison:** MockLM ceiling surfaced with gap analysis (3/6 vs 6/6)
- **FPR assessment:** 0.0% with CI, below 5% threshold
- **Deterministic consistency:** All 30 clean runs produced identical output (0 errors each)

## Decisions & Deviations

### Decisions Made

- **CC-009:** Post-hoc injection approach reveals architectural gap vs MockLM registration-time detection. This is a real architectural difference, not a bug or test failure. Post-hoc `validate_chamber()` cannot re-verify hashes (D3), check ref correctness beyond existence (D4), or enforce state transition legality (D6).
- **CC-010:** D7/D8 gaps are findings about forge coverage limitations. D7 (trace data loss) may be fundamentally undetectable by structural validation (remaining refs still form valid DAG). D8 (content corruption) requires content integrity checks not present in structural validation.
- **User decision:** Accepted negative finding on natural violations. Forge mechanism proven on injected faults; natural violations are zero on this sample.

### Deviations from Plan

None - plan executed exactly as written. All three tasks completed per specification.

## Issues Encountered

None - campaign executed cleanly. All 90 injections, 30 clean runs, and report generation completed without errors.

## Open Questions

1. Should `validate_chamber()` be extended to close the D3/D4/D6 post-hoc gap? This would bring D1-D6 detection from 3/6 to 6/6 on real data.
2. Is D7 (forge trace compression data loss) fundamentally undetectable by structural validation alone?
3. How many diverse clean runs are needed to reduce the natural violation CP upper bound below 5%? (Answer: 59+ runs at 0 violations.)
4. Will Phase 4 compaction testing surface natural violations that static ledger analysis does not?
5. Does the absence of natural violations indicate that structural failures are genuinely rare in coding/patching tasks, or that post-hoc validation misses the types that do occur?

## User Setup Required

None - no external configuration required.

---

_Phase: 03-violation-detection-campaign_
_Plan: 02_
_Completed: 2026-03-16_
