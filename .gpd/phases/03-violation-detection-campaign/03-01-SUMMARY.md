---
phase: 03-violation-detection-campaign
plan: 01
depth: full
one-liner: "Built D1-D9 fault injection framework and campaign orchestrator; revealed 5 post-hoc validation gaps (D3/D4/D6/D7/D8) vs MockLM's 6/6 registration-time ceiling"
subsystem: validation
tags:
  - fault-injection
  - violation-detection
  - statistical-testing
  - three-tier-comparison

requires:
  - phase: 02-integration-and-baseline-establishment
    provides:
      - OpenClawAdapter producing sealed forge chambers from real ledger data
      - baseline_measurement.py bootstrap_ci framework
      - Three-tier baseline measurements (uninstrumented/structured/forge)
      - MockLM experiment results (6/6 D1-D6 detection)
provides:
  - FaultInjector class injecting all 9 structural fault types (D1-D9) into sealed chambers
  - verify_injection() confirming each injection corrupts the target artifact
  - D7-D9 calibration results (D7 gap, D8 gap, D9 detected)
  - D1-D6 regression vs MockLM (3/6 post-hoc gap, 6/6 registration-time)
  - DetectionCampaign orchestrator with scheduling, three-tier comparison, CI computation
  - Statistical framework (bootstrap_ci, clopper_pearson_ci, select_ci)
  - Campaign infrastructure ready for Plan 03-02 to run actual detection campaign
affects:
  - 03-violation-detection-campaign (Plan 02 uses this infrastructure)

methods:
  added:
    - Fault injection (post-hoc chamber mutation with deepcopy)
    - Three-tier comparison framework
    - Bootstrap percentile CI (B=10000, seed=42)
    - Clopper-Pearson exact binomial CI for boundary proportions
    - Injected vs natural detection separation

key-files:
  created:
    - tools/fault_injector.py
    - tools/test_fault_injector.py
    - tools/detection_campaign.py

key-decisions:
  - "Post-hoc injection via deepcopy rather than live injection during chamber construction"
  - "D7-D9 gaps are documented findings, not test failures -- they reveal forge coverage limitations"
  - "CI method auto-selection: Clopper-Pearson at boundary (0/n, n/n), bootstrap at interior"

patterns-established:
  - "FaultInjector.inject_dN() returns modified copy, never mutates original"
  - "verify_injection() classifies as 'verified' or 'gap_identified' with reason"
  - "Campaign scheduling balances injections across tasks (30% cap per task)"

conventions:
  - "All metrics dimensionless ratios [0,1] or counts >= 0"
  - "Compaction always qualified: forge trace compression vs LLM context-window compaction"
  - "Hash integrity: SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True)"

plan_contract_ref: ".gpd/phases/03-violation-detection-campaign/03-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-injection-framework:
      status: passed
      summary: "FaultInjector class injects all 9 fault types into sealed chambers. Each injection produces a verifiably corrupted artifact. D7/D8 are documented gaps (not detection failures). D9 is detected by seal enforcement."
      linked_ids: [deliv-fault-injector, deliv-injector-tests, test-injection-verification, test-d7d9-calibration, ref-mock-experiment, ref-d1d6-prior]
    claim-campaign-orchestration:
      status: passed
      summary: "DetectionCampaign schedules 90+ injections, runs three-tier comparison, computes detection rates with proper CIs, and separates injected from natural detections. Dry-run and full campaign validated on real ledger data."
      linked_ids: [deliv-campaign-orchestrator, test-campaign-dry-run, test-ci-coverage, test-three-tier-ordering, ref-mock-experiment, ref-baseline-data]
  deliverables:
    deliv-fault-injector:
      status: passed
      path: tools/fault_injector.py
      summary: "FaultInjector class with inject_d1 through inject_d9 methods, verify_injection(), inject_random(). Statistical framework (bootstrap_ci, clopper_pearson_ci, select_ci). All must_contain items present."
      linked_ids: [claim-injection-framework, test-injection-verification]
    deliv-injector-tests:
      status: passed
      path: tools/test_fault_injector.py
      summary: "44 tests covering all 9 injection types, verification, D7-D9 calibration, D1-D6 MockLM regression, bootstrap CI coverage, Clopper-Pearson boundary values. All pass."
      linked_ids: [claim-injection-framework, test-injection-verification, test-d7d9-calibration]
    deliv-campaign-orchestrator:
      status: passed
      path: tools/detection_campaign.py
      summary: "DetectionCampaign class with schedule_injections, run_three_tier_comparison, compute_detection_rates, bootstrap_ci, clopper_pearson_ci, separate_injected_natural, run_clean_campaign, generate_campaign_report, run_full_campaign. All must_contain items present."
      linked_ids: [claim-campaign-orchestration, test-campaign-dry-run, test-ci-coverage, test-three-tier-ordering]
  acceptance_tests:
    test-injection-verification:
      status: passed
      summary: "All 9 fault types inject successfully. D1/D2/D5 verified (original valid, injected invalid). D3/D4/D6/D7/D8 gaps documented (validate_chamber misses them post-hoc). D9 raises ForgeChamberError by construction."
      linked_ids: [claim-injection-framework, deliv-fault-injector, deliv-injector-tests]
    test-d7d9-calibration:
      status: passed
      summary: "D7 (forge trace compression ref loss): GAP -- remaining refs form valid DAG, not caught by validate_chamber(). D8 (context pressure truncation): GAP -- no content integrity check in validate_chamber(). D9 (post-seal registration): DETECTED by ForgeChamberError seal enforcement."
      linked_ids: [claim-injection-framework, deliv-fault-injector, deliv-injector-tests, ref-mock-experiment]
    test-campaign-dry-run:
      status: passed
      summary: "Dry run produces 90 injections (10 per D1-D9), all types covered, schedule_valid=True. Output has separate injected_detections and natural_detections arrays."
      linked_ids: [claim-campaign-orchestration, deliv-campaign-orchestrator, ref-baseline-data]
    test-ci-coverage:
      status: passed
      summary: "Bootstrap coverage = 95.5% >= 93% threshold on 1000 Binomial(20,0.7) samples. Clopper-Pearson at 0/10: upper=0.308 (in [0.28, 0.35]). At 10/10: lower=0.692 (in [0.65, 0.72])."
      linked_ids: [claim-campaign-orchestration, deliv-campaign-orchestrator]
    test-three-tier-ordering:
      status: passed
      summary: "For all 9 fault types: forge_detection >= structured_detection >= uninstrumented_detection. No ordering violations found."
      linked_ids: [claim-campaign-orchestration, deliv-campaign-orchestrator, ref-baseline-data]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM ceiling (6/6 D1-D6 detection) compared against real data injection results. Real data post-hoc detection: 3/6 D1-D6. Gap analysis: D3 (hash not re-verified), D4 (wrong parent not checked beyond existence), D6 (no transition legality check). Gap is real and documented in campaign report anchor_comparison section."
    ref-d1d6-prior:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "D1-D6 injection methods reproduce the same structural corruptions as MockLM scenario D. Detection mechanisms match for D1 (ForgeNullError/null discipline), D2 (ForgeRefError/ref resolution), D5 (ForgeChamberError/null discipline). D3/D4/D6 detected at registration time in MockLM but not by post-hoc validate_chamber()."
    ref-baseline-data:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "Phase 2 baseline report confirms uninstrumented floor (reachability=0.0, detection=0) and forge baseline (reachability=1.0, validation_errors=0 on clean data). Campaign uses same measurement methodology (validate_chamber, three-tier comparison)."
  forbidden_proxies:
    fp-synthetic-only:
      status: rejected
      notes: "separate_injected_natural() enforces this: injected faults are never counted as natural violations. Campaign report has separate 'separated.injected_detections_count' and 'separated.natural_detections_count' fields. Plan 03-02 runs actual campaign seeking natural violations."
    fp-short-tasks:
      status: rejected
      notes: "Campaign orchestrator's schedule_injections() distributes injections across all position categories (early/middle/late). The real ledger sample includes long task sequences (47 events, 6 cursor resets). Task corpus includes long tasks per design."
  uncertainty_markers:
    weakest_anchors:
      - "D3/D4/D6 are NOT detected by post-hoc validate_chamber(). This is a real gap between MockLM's registration-time detection and the campaign's post-hoc validation approach."
      - "D7 (forge trace compression ref loss) may be fundamentally undetectable by structural validation if remaining refs form a valid DAG."
    unvalidated_assumptions: []
    competing_explanations: []
    disconfirming_observations:
      - "D1-D6 real data detection is 3/6, not 6/6. The MockLM-to-real-LLM validity gap is REAL: MockLM catches faults at injection time during register_stage(), but post-hoc validate_chamber() does not re-check hashes (D3), ref correctness beyond existence (D4), or transition legality (D6)."

comparison_verdicts:
  - subject_id: claim-injection-framework
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    metric: "D1-D6 detection coverage"
    threshold: "6/6 = 100%"
    verdict: tension
    recommended_action: "Document gap. Plan 03-02 should consider whether to add hash re-verification and transition checks to validate_chamber(), or accept the post-hoc gap as a known limitation."
    notes: "Post-hoc validate_chamber() detects 3/6 (D1, D2, D5). Registration-time detection via register_stage() catches 6/6. The gap is architectural (post-hoc vs live validation), not a bug."
  - subject_id: claim-campaign-orchestration
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-baseline-data
    comparison_kind: baseline
    metric: "three-tier ordering"
    threshold: "forge >= structured >= uninstrumented for all types"
    verdict: pass
    recommended_action: "None -- ordering holds for all 9 fault types."
    notes: "Clean data FPR = 0.0, confirming forge validation does not produce false positives on the sample ledger."

duration: 8min
completed: 2026-03-16
---

# Plan 03-01: Fault Injection Framework and Campaign Orchestrator

**Built D1-D9 fault injection framework and campaign orchestrator; revealed 5 post-hoc validation gaps (D3/D4/D6/D7/D8) vs MockLM's 6/6 registration-time ceiling**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-16T01:30:37Z
- **Completed:** 2026-03-16T01:38:00Z
- **Tasks:** 2
- **Files modified:** 3

## Key Results

- FaultInjector injects all 9 structural fault types (D1-D9) into sealed chambers, each producing a verifiably corrupted artifact
- Post-hoc validate_chamber() detects 4/9 fault types: D1 (null collapse), D2 (broken provenance), D5 (missing state label), D9 (post-seal registration)
- 5 fault types are NOT detected post-hoc: D3 (corrupted hashes), D4 (fake source refs), D6 (illegal transition), D7 (forge trace compression data loss), D8 (context pressure truncation)
- D1-D6 vs MockLM ceiling: 3/6 detected post-hoc (50%), revealing a real architectural gap between registration-time and post-hoc validation
- Three-tier ordering holds for all 9 types: forge >= structured >= uninstrumented
- Clean FPR = 0.0 (no false positives on real ledger data)
- Bootstrap CI coverage: 95.5% >= 93% threshold; Clopper-Pearson boundaries verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Build D1-D9 fault injector with injection verification and D7-D9 calibration** - `ebdacd6` (implement)
2. **Task 2: Build campaign orchestrator with three-tier comparison and statistical framework** - `1bb6c74` (implement)

## Files Created/Modified

- `tools/fault_injector.py` -- FaultInjector class (D1-D9 injection, verification, statistical framework)
- `tools/test_fault_injector.py` -- 44 tests (injection, calibration, CI validation, regression)
- `tools/detection_campaign.py` -- DetectionCampaign class (scheduling, three-tier comparison, reporting)

## Next Phase Readiness

- Fault injection infrastructure ready for Plan 03-02 to run the actual detection campaign
- D3/D4/D6 post-hoc gap is a finding for Plan 03-02 to address: either extend validate_chamber() or accept as known limitation
- Campaign orchestrator is tested end-to-end on real ledger data
- Statistical framework validated (bootstrap + Clopper-Pearson)

## Contract Coverage

- Claim IDs advanced: claim-injection-framework -> passed, claim-campaign-orchestration -> passed
- Deliverable IDs produced: deliv-fault-injector -> tools/fault_injector.py, deliv-injector-tests -> tools/test_fault_injector.py, deliv-campaign-orchestrator -> tools/detection_campaign.py
- Acceptance test IDs run: test-injection-verification -> passed, test-d7d9-calibration -> passed, test-campaign-dry-run -> passed, test-ci-coverage -> passed, test-three-tier-ordering -> passed
- Reference IDs surfaced: ref-mock-experiment -> compared (3/6 gap), ref-d1d6-prior -> compared, ref-baseline-data -> read + compared
- Forbidden proxies rejected: fp-synthetic-only -> enforced by separate_injected_natural(), fp-short-tasks -> rejected by long task inclusion
- Decisive comparison verdicts: claim-injection-framework vs ref-mock-experiment -> tension (3/6 vs 6/6), claim-campaign-orchestration vs ref-baseline-data -> pass (ordering holds)

## Validations Completed

- 44 new tests pass (injection, calibration, CI validation, regression)
- 354 existing tests pass (no regressions)
- Three-tier ordering verified for all 9 fault types
- Bootstrap CI coverage: 95.5% on 1000 Binomial(20, 0.7) simulations
- Clopper-Pearson at 0/10: upper = 0.308 (within [0.28, 0.35])
- Clopper-Pearson at 10/10: lower = 0.692 (within [0.65, 0.72])
- Deterministic scheduling: same seed = identical results
- Zero modification to existing forge tools (git diff confirms)

## Decisions & Deviations

### Key Decisions

- **Post-hoc injection approach:** FaultInjector operates on sealed chambers (deepcopy + mutation) rather than intercepting at registration time. This is the correct approach for the campaign (injecting into already-processed real data) but reveals the post-hoc vs registration-time validation gap.
- **Gap-as-finding:** D7/D8 gaps and D3/D4/D6 gaps are documented as forge coverage findings, not treated as test failures. The plan explicitly allows this: "If NOT detected, the test PASSES but the result is 'gap identified'."
- **CI auto-selection:** select_ci() automatically chooses Clopper-Pearson for boundary proportions (k=0 or k=n) and bootstrap for interior. This prevents the bootstrap degeneracy issue (zero-width CI at boundaries).

### Deviations

**1. [Rule 1 - Code Bug] Missing ForgeChamberError import in detection_campaign.py**
- **Found during:** Task 2 (campaign execution)
- **Issue:** ForgeChamberError was used in except clause but not imported
- **Fix:** Added to import from forge_chamber
- **Verification:** Full campaign runs successfully after fix
- **Committed in:** 1bb6c74 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (import bug)
**Impact on plan:** Trivial import fix. No scope change.

## Key Quantities and Uncertainties

| Quantity | Value | Uncertainty | Source | Valid Range |
|---|---|---|---|---|
| D1-D6 post-hoc detection rate | 0.50 (3/6 types) | CI not applicable (binary per type) | Campaign on real ledger | Post-hoc validation only |
| Aggregate forge detection (all D1-D9) | 0.444 (40/90) | 95% CI [0.344, 0.544] (bootstrap) | Campaign 90 injections | n=10 per type |
| Clean FPR | 0.0 (0/5) | 95% CI [0.0, 0.522] (Clopper-Pearson) | 5 clean runs | Real ledger sample |
| Bootstrap CI coverage | 0.955 | N/A (simulation) | 1000 Binomial(20, 0.7) samples | alpha=0.05 |
| Clopper-Pearson 0/10 upper | 0.308 | Exact | Beta.ppf | n=10 |
| Clopper-Pearson 10/10 lower | 0.692 | Exact | Beta.ppf | n=10 |

## Approximations Used

| Approximation | Valid When | Error Estimate | Breaks Down At |
|---|---|---|---|
| Bootstrap percentile CI | N >= 5, exchangeable | Coverage >= 93% (verified) | N < 5 or degenerate (all identical) |
| Clopper-Pearson exact | All n >= 1 | Exact (conservative) | Never (exact method) |
| Token count estimation (chars/4) | Short-medium text | ~20-40% off | Code-heavy content |

## Issues Encountered

None beyond the import fix documented above.

## Open Questions

- Should validate_chamber() be extended to re-verify hashes (D3), check ref correctness beyond existence (D4), and verify transition legality (D6)? This would close the post-hoc gap but adds complexity.
- Is D7 (forge trace compression ref loss) fundamentally undetectable by structural validation if remaining refs form a valid DAG? This may require content-level semantic checks.
- What is the expected detection rate on natural (non-injected) violations in real production data? Plan 03-02 will address this.

---

_Phase: 03-violation-detection-campaign_
_Plan: 01_
_Completed: 2026-03-16_
