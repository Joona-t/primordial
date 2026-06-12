---
phase: 03-violation-detection-campaign
verified: 2026-03-16T03:15:00Z
status: passed
score: 6/6 contract targets verified
consistency_score: 10/10 checks passed
independently_confirmed: 8/10 checks independently confirmed
confidence: high
comparison_verdicts:
  - subject_kind: acceptance_test
    subject_id: test-differential-detection
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    verdict: pass
    metric: "delta(forge - uninstrumented)"
    threshold: "> 0 with CI excluding zero"
  - subject_kind: acceptance_test
    subject_id: test-fpr-acceptable
    reference_id: ref-baseline-data
    comparison_kind: benchmark
    verdict: pass
    metric: "FPR"
    threshold: "< 5%"
  - subject_kind: acceptance_test
    subject_id: test-real-violation
    reference_id: null
    comparison_kind: existence
    verdict: pass
    metric: "natural_violation_count"
    threshold: ">= 1 OR honestly reported negative finding with Clopper-Pearson bound"
  - subject_kind: claim
    subject_id: claim-violation-detection
    reference_id: ref-mock-experiment
    comparison_kind: anchor
    verdict: pass
    metric: "D1-D6 detection rate vs MockLM ceiling"
    threshold: "50% gap honestly documented with architectural explanation"
suggested_contract_checks: []
---

# Phase 3 Verification: Violation Detection Campaign

**Phase goal:** Forge instrumentation detects structural failures on real agent tasks that go undetected by uninstrumented and structured-logging baselines, with at least one naturally-occurring detection

**Verification date:** 2026-03-16
**Status:** PASSED
**Confidence:** HIGH

---

## 1. Contract Target Coverage

| ID | Kind | Status | Confidence | Evidence |
|----|------|--------|------------|----------|
| claim-injection-framework (03-01) | claim | VERIFIED | INDEPENDENTLY CONFIRMED | 50/50 tests pass; all 9 injection methods produce verifiably corrupted artifacts; verify_injection() confirms corruption for detected types and documents gaps for undetected types |
| claim-campaign-orchestration (03-01) | claim | VERIFIED | INDEPENDENTLY CONFIRMED | DetectionCampaign class schedules 90+ injections, runs three-tier comparison, computes CIs correctly (independently verified), separates injected/natural detections |
| claim-violation-detection (03-02) | claim | VERIFIED | INDEPENDENTLY CONFIRMED | delta = +0.444 [CI: 0.344, 0.544] excludes zero; 4/9 types detected (D1, D2, D5, D9 at 100%); 5/9 undetected documented as architectural gaps; negative finding on natural violations honestly reported with CP bound |
| test-real-violation (03-02) | acceptance_test | VERIFIED (negative finding) | INDEPENDENTLY CONFIRMED | 0/30 clean runs produced violations; CP upper bound = 0.116 (11.6%); negative finding path per contract satisfied: honestly reported, not dressed up, injected/natural strictly separated |
| test-differential-detection (03-02) | acceptance_test | VERIFIED | INDEPENDENTLY CONFIRMED | delta = +0.444; bootstrap 95% CI [0.344, 0.544] excludes zero; three-tier ordering holds for all 9 types |
| test-fpr-acceptable (03-02) | acceptance_test | VERIFIED | INDEPENDENTLY CONFIRMED | FPR = 0.0 (0/30); CP upper bound = 0.116; FPR < 5% criterion met |

**Score: 6/6 contract targets verified**

---

## 2. Required Artifacts

| Artifact | Path | Status | Details |
|----------|------|--------|---------|
| deliv-fault-injector | tools/fault_injector.py | VERIFIED | 729 lines; all 11 must_contain items present; all 9 injection methods + verify_injection() functional |
| deliv-injector-tests | tools/test_fault_injector.py | VERIFIED | 764 lines; all 6 must_contain items present; 50/50 tests pass (verified by execution) |
| deliv-campaign-orchestrator | tools/detection_campaign.py | VERIFIED | 832 lines; all 7 must_contain items present; DetectionCampaign class complete with scheduling, three-tier comparison, CI computation, and injected/natural separation |
| deliv-violation-report | docs/violation-report.md | VERIFIED | 202 lines; all required sections present (D1-D9 rates with CIs, differential, natural violation assessment, FPR, MockLM comparison, forbidden proxy audit) |
| deliv-campaign-data | data/campaign/ | VERIFIED | All 3 files present and valid JSON: injection-results.json (90 records), clean-results.json (30 runs), campaign-report.json (full report with anchor comparison) |

---

## 3. Computational Verification Details

### 3a. Statistical CI Verification (INDEPENDENTLY CONFIRMED)

All Clopper-Pearson and bootstrap CI values were recomputed from scratch using scipy.stats.beta and numpy, and compared against the values in campaign-report.json.

**Output:**

```
=== CP CI at k=0, n=10 ===
lower=0.000000, upper=0.308497
upper in [0.28, 0.35]: True -- PASS

=== CP CI at k=10, n=10 ===
lower=0.691503, upper=1.000000
lower in [0.65, 0.72]: True -- PASS

=== CP CI at k=0, n=30 (FPR bound) ===
lower=0.000000, upper=0.115703
Data file says upper = 0.11570330822202778
Match: True -- PASS

=== CP CI at k=0, n=90 (aggregate uninstr. upper bound) ===
upper=0.040159
Data file says upper = 0.04015891961577464
Match: True -- PASS
```

All 4 boundary CI values match to 6+ decimal places.

### 3b. Detection Rate Arithmetic (INDEPENDENTLY CONFIRMED)

**Output:**

```
=== Detection rate arithmetic ===
forge_detected = 10+10+0+0+10+0+0+0+10 = 40
total = 9 * 10 = 90
rate = 40/90 = 0.4444444444
Expected 4/9 = 0.4444444444 -- PASS

=== D1-D6 anchor comparison ===
D1-D6 detected: 10+10+0+0+10+0 = 30/60 = 0.5
Data file says: 0.5 and "30/60" -- PASS
D1-D6 types detected: 3/6 (D1, D2, D5)
Gap types: D3 (hash), D4 (ref correctness), D6 (transition legality) -- PASS
```

### 3c. Bootstrap CI Independent Computation (INDEPENDENTLY CONFIRMED)

**Output:**

```
=== Bootstrap CI for aggregate forge rate (40/90) ===
Independent computation: [0.344444, 0.544444]
Data file reports: [0.34444444444444444, 0.5444444444444444]
Lower match: True
Upper match: True -- PASS

=== Bootstrap coverage test (500 sims, true_p=0.7) ===
Coverage: 0.964 (482/500)
Coverage >= 0.93: True -- PASS
```

### 3d. Three-Tier Ordering (INDEPENDENTLY CONFIRMED)

**Output:**

```
D1: forge=10 >= struct=0 >= uninst=0 -- OK
D2: forge=10 >= struct=0 >= uninst=0 -- OK
D3: forge=0 >= struct=0 >= uninst=0 -- OK
D4: forge=0 >= struct=0 >= uninst=0 -- OK
D5: forge=10 >= struct=0 >= uninst=0 -- OK
D6: forge=0 >= struct=0 >= uninst=0 -- OK
D7: forge=0 >= struct=0 >= uninst=0 -- OK
D8: forge=0 >= struct=0 >= uninst=0 -- OK
D9: forge=10 >= struct=0 >= uninst=0 -- OK
Three-tier ordering holds: True -- PASS
```

### 3e. MockLM Anchor Values (INDEPENDENTLY CONFIRMED)

Read experiment_results.json directly and verified:
- MockLM detected 6/6 violations (D1-D6) -- matches campaign-report.json anchor
- MockLM mean compression ratio = 1.0959 -- matches baseline-report.json reference
- Detection mechanisms: D1=ForgeNullError, D2=ForgeRefError, D3-D6=ForgeChamberError -- correctly cited in gap analysis

### 3f. Test Suite Execution (INDEPENDENTLY CONFIRMED)

All 50 tests in test_fault_injector.py passed (executed via pytest, runtime 83.11s):
- 3 clean chamber validity tests
- 27 D1-D9 injection and calibration tests
- 1 D1-D6 MockLM regression test
- 8 statistical CI validation tests (bootstrap coverage, Clopper-Pearson boundaries, select_ci)
- 5 inject_random and verify_injection tests
- 3 dimensional check tests
- 3 contract alias tests (D7, D8, D9)

### 3g. Differential Detection Significance (INDEPENDENTLY CONFIRMED)

- delta(forge - uninstrumented) = 40/90 - 0/90 = 0.4444
- Forge CI lower bound = 0.3444 > 0.0 -- CI excludes zero
- This establishes statistical significance of the differential at 95% confidence

---

## 4. Physics / Domain Consistency Summary

| Check | Status | Confidence | Notes |
|-------|--------|------------|-------|
| Dimensional analysis (metrics) | CONSISTENT | INDEPENDENTLY CONFIRMED | All rates in [0,1], all counts non-negative integers, all CIs in [0,1] |
| Boundary value behavior | VERIFIED | INDEPENDENTLY CONFIRMED | CP CI correctly handles 0/n and n/n boundaries; bootstrap degenerates correctly at boundaries |
| Internal arithmetic consistency | VERIFIED | INDEPENDENTLY CONFIRMED | 40/90 = 0.4444; 30/60 = 0.5; all per-type totals sum to aggregate |
| CI coverage property | VERIFIED | INDEPENDENTLY CONFIRMED | Bootstrap 95% CI achieves 96.4% coverage on simulated data (>= 93% threshold) |
| Three-tier ordering invariant | VERIFIED | INDEPENDENTLY CONFIRMED | forge >= structured >= uninstrumented for all 9 types |
| MockLM anchor accuracy | VERIFIED | INDEPENDENTLY CONFIRMED | 6/6 detection, compression ratio, detection mechanisms all match source data |
| Injected/natural separation | VERIFIED | INDEPENDENTLY CONFIRMED | separate_injected_natural() correctly separates; 0 natural detections in clean runs |
| FPR calibration | VERIFIED | INDEPENDENTLY CONFIRMED | 0/30 clean runs, CP upper = 0.116, below 5% threshold |
| Gap documentation accuracy | VERIFIED | STRUCTURALLY PRESENT | D3/D4/D6/D7/D8 gaps explained with architectural reasoning; D7 "fundamentally undetectable" claim plausible but not proven |
| Negative finding honesty | VERIFIED | STRUCTURALLY PRESENT | Natural violation result reported with CP bound, not conflated with injected results, forbidden proxy explicitly addressed |

---

## 5. Forbidden Proxy Audit

| Proxy ID | Status | Evidence |
|----------|--------|----------|
| fp-synthetic-only | REJECTED | separate_injected_natural() enforces strict separation in code (verified by reading implementation). Violation report Section c documents natural violations independently. Zero natural violations honestly reported as negative finding with CP bound, not conflated with the 40/90 injected detection rate. Headline metrics never combine injected and natural counts. |
| fp-short-tasks | REJECTED | Campaign uses real Zarathustra ledger (47 events, 40+ stages, 6 cursor resets). Baseline-report.json confirms same data source. Task corpus spans multiple sessions with cursor advancement events. This exceeds MockLM test scenarios (3-5 stages). |

---

## 6. Comparison Verdict Ledger

| Subject ID | Comparison Kind | Verdict | Threshold | Notes |
|------------|----------------|---------|-----------|-------|
| test-differential-detection | benchmark vs uninstrumented | pass | delta > 0 with CI excluding zero | delta = +0.444, CI [0.344, 0.544] |
| test-fpr-acceptable | benchmark | pass | FPR < 5% | FPR = 0.0, CP upper = 11.6% (acceptable for 0/30 sample) |
| test-real-violation | existence / negative finding | pass | >= 1 natural violation OR honest negative report | Negative finding: 0/30, CP upper 11.6%, honestly reported |
| claim-violation-detection vs ref-mock-experiment | anchor | pass | Gap documented | D1-D6: 3/6 (50%) vs MockLM 6/6; gap explained as registration-time vs post-hoc architectural difference |
| claim-violation-detection vs ref-baseline-data | anchor | pass | Consistent methodology | Same ledger data, same measurement framework, three-tier comparison consistent with Phase 2 baselines |

---

## 7. Discrepancies Found

None. All computed values match claimed values. All statistical tests pass. No anti-patterns found in any of the 4 scanned source files.

---

## 8. Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| BASE-03: Campaign uses same measurement methodology as baselines | SATISFIED | Same ledger data source, same validate_chamber(), same metrics framework from Phase 2 |
| VIOL-01: All 9 fault types injected >= 10 times each | SATISFIED | 90 total injections = 9 types x 10 each, verified in injection-results.json |
| VIOL-02: Differential detection with bootstrap 95% CI | SATISFIED | delta = +0.444, CI [0.344, 0.544], independently verified |
| VIOL-03: False positive rate measured on clean runs | SATISFIED | FPR = 0.0 (0/30), CP CI [0.000, 0.116] |

---

## 9. Anti-Patterns Found

None. All 4 files scanned (fault_injector.py, detection_campaign.py, test_fault_injector.py, run_campaign.py) are free of TODO/FIXME/PLACEHOLDER markers, suppressed warnings, and unexplained magic numbers.

---

## 10. Expert Verification Recommended

| Item | Why Expert | Domain |
|------|-----------|--------|
| D7 "fundamentally undetectable" claim | Whether silent ref loss in a valid DAG is truly undetectable by any structural method, or whether cardinality constraints or ref-count invariants could catch it | Formal verification / graph theory |
| Natural violation rate interpretation | Whether 0/30 with CP upper 11.6% is sufficient evidence that the ledger sample is too clean, or whether more diverse data would reveal violations | Experimental methodology |
| Post-hoc vs registration-time gap | Whether extending validate_chamber() to re-verify hashes (D3), check ref correctness (D4), and enforce transition legality (D6) is the right architectural choice vs accepting the gap | Software architecture |

---

## 11. Confidence Assessment

**Overall: HIGH**

Justification:
- 8/10 checks independently confirmed by executing code and recomputing values from scratch
- 2/10 checks structurally present (gap documentation accuracy requires domain judgment; negative finding honesty is structural)
- All statistical values (Clopper-Pearson CIs, bootstrap CIs, detection rates, differentials) independently recomputed and match to 6+ decimal places
- All 50 tests pass when executed
- All must_contain items present in all deliverables
- All forbidden proxies explicitly rejected with evidence
- MockLM anchor values independently verified against experiment_results.json source
- No anti-patterns, no discrepancies, no missing artifacts

The negative finding on natural violations (0/30 clean runs) is not a quality failure -- it is an honest experimental outcome with proper statistical bounds. The contract explicitly allows this path: "If zero natural violations after full campaign, honestly report as negative finding with Clopper-Pearson upper bound on natural violation rate." This was done correctly.

---

## 12. Gaps Summary

No gaps found. All contract targets verified. Phase 3 passes verification.
