# Consistency Check: Phase 03 (Violation Detection Campaign)

**Checked:** 2026-03-16
**Mode:** Rapid (post-phase cross-phase consistency check)
**Phase:** 03-violation-detection-campaign (Plans 01 and 02)
**Checked against:** Full conventions ledger, Phases 01 and 02 accumulated state

---

## 1. Convention Compliance (Phase 03 vs Full Ledger)

All 18 canonical physics conventions are N/A for this formal-systems project. Checked Phase 03 against all 11 project-specific custom conventions from CONVENTIONS.md.

| # | Convention | Introduced | Relevant to Phase 03? | Compliant? | Evidence | Notes |
|---|-----------|-----------|----------------------|-----------|---------|-------|
| 1 | Absence State Ontology (8 states) | Phase 1 | Yes | Yes | fault_injector.py imports V1_ABSENCE_STATES from forge_nulls; D1/D5/D6 injections operate on these states; no additional states introduced | |
| 2 | Absence Object Canonical Form | Phase 1 | Yes | Yes | D1 (null collapse) strips typed absence to bare None; D5 strips output_state; both correctly target canonical form fields | |
| 3 | State Transition Legality (8x8 matrix) | Phase 1 | Yes | Yes | fault_injector.py imports TRANSITION_TABLE and validate_transition from forge_nulls for D6 injection; uses them to force known-illegal transitions | |
| 4 | Provenance Reference Format | Phase 1 | Yes | Yes | D2 injection uses ghost artifact IDs ("artifact:ghost:stage:phantom:r1"); D4 uses valid-but-wrong refs; both correctly target source_refs structure | |
| 5 | Artifact ID Format | Phase 1 | Yes | Yes | Injected ghost IDs follow colon-separated hierarchical format per convention; no format violations introduced | |
| 6 | Compaction Disambiguation | Phase 1 | Yes | Yes | Grep found ZERO instances of unqualified "compaction" in fault_injector.py, detection_campaign.py, and violation-report.md; all uses are qualified (forge trace compression, context pressure corruption, LLM context-window compaction) | |
| 7 | Metrics Definitions | Phase 1 | Yes | Yes | detection_rate = violations_detected/total_violations matches convention; FPR = false_alarms/clean_runs matches convention; all metrics dimensionless ratios in [0,1] or non-negative integer counts | |
| 8 | Violation Classification (D1-D9) | Phase 1 | Yes | Yes | D1-D9 taxonomy used exactly as defined in CONVENTIONS.md; structural-only scope maintained; no semantic errors classified as violations | |
| 9 | Unit System (N/A) | Phase 1 | Yes | Yes | All quantities are dimensionless ratios or counts; no physical units introduced | |
| 10 | Hash Integrity (SHA-256) | Phase 1 | Yes | Yes | D3 injection modifies content after hash computation using SHA-256 on canonical JSON (json.dumps with sort_keys=True, ensure_ascii=True) per convention | |
| 11 | Protocol Versioning | Phase 1 | No | N/A | Phase 3 does not modify chamber/trace schemas; operates on sealed chambers from Phase 2 adapter | |

**Compliance matrix result:** 10/10 relevant conventions compliant, 1 not applicable. Zero violations.

---

## 2. Provides/Requires Chain Verification

### Phase 02 -> Phase 03 transfers

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|----------|----------|----------|--------------|-------------|-----------------|--------|
| OpenClawAdapter producing sealed forge chambers | Phase 02 Plan 02 | Phase 03 Plan 01 | Yes -- same class, same process_ledger() entry point | Yes -- same ledger path used | Yes -- same artifact ID format, same typed absence | OK |
| baseline_measurement.py bootstrap_ci framework | Phase 02 Plan 03 | Phase 03 Plan 01 | Yes -- same bootstrap CI methodology (B=10000, seed=42, percentile method) | Yes -- bootstrap_ci() reimplemented in fault_injector.py with identical parameters | Yes -- same convention (95% CI, [0,1] bounds) | OK |
| Three-tier baseline measurements | Phase 02 Plan 04 | Phase 03 Plan 02 | Yes -- uninstrumented=0.0 reachability/0 detection, forge=1.0 reachability/0 detection on clean data | Yes -- Phase 3 differential uses these as comparison arms; uninstrumented_detected=0, structured_detected=0 for all injected faults matches floor | Yes | OK |
| MockLM experiment results (6/6 D1-D6) | Phase 01 (ref-mock-experiment) | Phase 03 Plans 01-02 | Yes -- same fault taxonomy D1-D6, same detection mechanisms | Yes -- 6/6 ceiling correctly cited; 3/6 real data gap documented with architectural explanation | Yes | OK |
| TRANSITION_TABLE (64 entries, 45 legal, 19 illegal) | Phase 01 Plan 01 | Phase 03 Plan 01 | Yes -- imported directly from forge_nulls.py; used by D6 injection to force known-illegal transitions | Yes -- table dimensions and counts match (64 entries) | Yes | OK |
| validate_chamber() | Phase 01 | Phase 03 | Yes -- same structural validation function; used for verify_injection() and campaign detection | Yes -- same function imported from forge_chamber | Yes | OK |

### Phase 03 Plan 01 -> Plan 02 transfers

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|----------|----------|----------|--------------|-------------|-----------------|--------|
| FaultInjector class (D1-D9) | Plan 03-01 | Plan 03-02 | Yes -- same class, same injection methods | Yes -- imported directly | Yes | OK |
| DetectionCampaign orchestrator | Plan 03-01 | Plan 03-02 | Yes -- same class, same scheduling/comparison/CI methods | Yes -- imported directly | Yes | OK |
| D7-D9 calibration results | Plan 03-01 | Plan 03-02 | Yes -- D7/D8 gaps, D9 detected by seal enforcement | Yes -- campaign confirms calibration results | Yes | OK |
| D1-D6 post-hoc detection (3/6) | Plan 03-01 | Plan 03-02 | Yes -- same 3 types detected (D1, D2, D5), same 3 undetected (D3, D4, D6) | Yes -- 30/60 = 0.5 in campaign-report.json matches 3/6 per-type | Yes | OK |

**All provides/requires pairs verified: 10/10 consistent.**

---

## 3. Numerical Spot-Checks

### 3a. Aggregate detection rate arithmetic

- Forge detected: D1(10) + D2(10) + D3(0) + D4(0) + D5(10) + D6(0) + D7(0) + D8(0) + D9(10) = 40
- Total injections: 9 types x 10 = 90
- Rate: 40/90 = 0.4444... (matches campaign-report.json value of 0.4444444444444444)
- **PASS**

### 3b. D1-D6 sub-aggregate

- D1(10) + D2(10) + D3(0) + D4(0) + D5(10) + D6(0) = 30
- Total D1-D6: 60
- Rate: 30/60 = 0.5 (matches "d1_d6_aggregate_rate": 0.5)
- Types detected: 3/6 (D1, D2, D5) -- matches all references
- **PASS**

### 3c. Clopper-Pearson CI at 0/30 (FPR bound)

- Expected: Beta.ppf(0.975, 1, 30) = 0.1157...
- campaign-report.json reports: 0.11570330822202778
- 03-VERIFICATION.md independently confirmed: 0.115703
- **PASS**

### 3d. Clopper-Pearson CI at 10/10 (detection at boundary)

- Expected lower bound: Beta.ppf(0.025, 10, 1) = 0.6915...
- campaign-report.json reports: 0.6915028921812392
- **PASS**

### 3e. Bootstrap CI for aggregate forge rate

- Data: 40/90 binary outcomes
- campaign-report.json reports: [0.34444..., 0.54444...]
- 03-VERIFICATION.md independently recomputed: [0.344444, 0.544444]
- **PASS** (match to 6+ decimal places)

---

## 4. Cross-Phase Numerical Consistency

### 4a. Test count evolution

| Phase | New Tests | Total Tests | Source |
|-------|-----------|-------------|--------|
| Phase 1 Plan 01 | 0 (code additions, no new test files) | 103 | 01-01-SUMMARY.md |
| Phase 1 Plan 02 | 198 | 301 | 01-02-SUMMARY.md |
| Phase 2 Plan 02 | 53 | 354 | 02-02-SUMMARY.md |
| Phase 3 Plan 01 | 44 (fault_injector tests) | claimed 354 existing + 44 new | 03-01-SUMMARY.md |
| Phase 3 Verification | 50 in test_fault_injector.py | 404 total | 03-VERIFICATION.md, STATE.md |

Note: Plan 03-01 SUMMARY says "44 new tests" and "354 existing tests pass". The VERIFICATION report says "50/50 tests pass" for test_fault_injector.py. STATE.md says "Total test count: 404 (354 existing + 50 new fault injector/campaign tests)". The count grew from 44 to 50 between Plan 03-01 and the Phase 3 verification -- this is explained by Plan 03-01 Task 1 creating 44 tests, and then additional tests being added in the Task 2 campaign orchestrator commit. The final verified count of 50 in test_fault_injector.py is the authoritative number.

**STATUS:** Consistent. The evolution 103 -> 301 -> 354 -> 404 is fully traceable.

### 4b. MockLM anchor values across phases

| Metric | Phase 1 (source) | Phase 2 (baseline) | Phase 3 (campaign) | Match? |
|--------|-----------------|-------------------|-------------------|--------|
| Violation detection | 6/6 D1-D6 | N/A (clean data) | 3/6 D1-D6 post-hoc (gap documented) | Consistent -- gap explained |
| Reachability | 1.0 | 1.0 | 1.0 (clean data) | Yes |
| Trace compression | ~1.10 (mean) | 1.18 | 1.179 (in campaign-report.json) | Consistent -- real data slightly higher |
| FPR | 0.0 | 0.0 | 0.0 (0/30) | Yes |

**PASS** -- MockLM anchor values propagated consistently across all three phases.

### 4c. FPR sample size evolution within Phase 3

Plan 03-01 SUMMARY (Key Quantities table) reports "Clean FPR: 0.0 (0/5), CI [0.0, 0.522]". Plan 03-02 reports "FPR: 0.0 (0/30), CI [0.0, 0.116]". These are different measurements: Plan 03-01 ran a preliminary 5-run calibration during orchestrator testing; Plan 03-02 ran the full 30-run clean campaign. The CI correctly narrowed from [0, 0.522] to [0, 0.116] with the larger sample. **Not a discrepancy -- expected sample size growth.**

---

## 5. Semantic Consistency Checks

### 5a. Detection rate definition consistency

Phase 3 defines detection_rate = violations_detected / total_violations, matching CONVENTIONS.md #7 exactly. The denominator is "total injections of that type" (10 per type), not "total injections overall" (90). Per-type rates and aggregate rate are both reported, matching the convention requirement for both.

**PASS**

### 5b. Injected vs natural separation consistency

Phase 3 enforces fp-synthetic-only at code level (separate_injected_natural function) and at reporting level (separate sections in violation-report.md and separate fields in campaign-report.json). The aggregate detection rate of 0.444 is clearly labeled as applying to injected faults only. The natural violation count of 0 is reported separately with its own CI.

**PASS**

### 5c. Violation classification scope

Phase 3 classifies only structural violations (illegal transitions, missing metadata) per CONVENTIONS.md #8. The D1-D9 taxonomy matches exactly. No semantic errors or hallucinations are classified as violations.

**PASS**

---

## 6. Data Integrity Cross-Check

### 6a. Separated detections count (80) vs forge-detected injections (40)

campaign-report.json reports:
- `forge.detected: 40` (aggregate, in detection_rates.aggregate.forge)
- `separated.injected_detections_count: 80`

These measure different things: 40 is the number of _injected chambers_ where forge detected the fault (binary per chamber). 80 is the total number of _individual validation error entries_ across those 40 chambers (some chambers produce multiple validation errors). This is semantically consistent -- each detected D1/D2/D5/D9 injection produces an average of 2 validation errors per detected chamber (80/40 = 2.0), which is reasonable (e.g., a null collapse might trigger both a missing_state and a bare_null error).

**Not a discrepancy** -- but the difference between "chambers detected" and "individual validation errors" should be documented to avoid confusion in downstream phases.

### 6b. Three-tier ordering

campaign-report.json confirms forge >= structured >= uninstrumented for all 9 types. For D3/D4/D6/D7/D8, all three tiers detect 0 (trivial ordering). For D1/D2/D5/D9, forge detects 10, structured detects 0, uninstrumented detects 0 (strict ordering).

**PASS**

---

## 7. state.json vs STATE.md Synchronization

| Field | state.json | STATE.md | Match? |
|-------|-----------|---------|--------|
| current_phase | "2" | "3 (complete)" | MISMATCH |
| current_phase_name | "Integration and Baseline Establishment" | "Violation Detection Campaign" | MISMATCH |
| status | "Executing Phase 2, Wave 1 complete" | "Phase 3 complete" | MISMATCH |
| progress_percent | 28 | 60% | MISMATCH |
| total_tests (intermediate_results) | "301" | "404" | MISMATCH |
| decisions | 8 entries (through CC-008) | 11 entries (through CC-011) | MISMATCH |

**FINDING:** state.json is stale -- it reflects Phase 2 Plan 01 completion state while STATE.md reflects Phase 3 completion. The sync timestamp in state.json ("_synced_at": "2026-03-16T00:40:34") predates Phase 3 execution. This is a known pattern: STATE.md is the primary source of truth (updated by the executor), while state.json is a machine-readable snapshot that may lag.

**Impact:** LOW. state.json is not consumed by Phase 3 artifacts (they read conventions from CONVENTIONS.md directly). The convention_lock in state.json is correct for all 18 canonical conventions (all N/A) and all 11 custom conventions. The stale position/status fields do not affect any cross-phase consistency.

**Recommendation:** Resync state.json to match STATE.md before Phase 4 begins.

---

## 8. Convention Evolution Tracking

| Change ID | Convention | Old | New | Changed In | Properly Documented? | All Post-Change Usage Correct? |
|-----------|-----------|-----|-----|-----------|---------------------|-------------------------------|
| CC-001 | Absence State Ontology (docs) | resolved as 8th state | not_generated as 8th state | Phase 1 | Yes | Yes -- Phase 3 uses not_generated throughout |
| CC-002 | Absence State Ontology (expansion) | Open: add timed_out/interrupted? | DECIDED: Not added | Phase 1 | Yes | Yes -- Phase 3 uses metadata enrichment per convention |
| CC-003 | Absence State Ontology (recoverability) | Open: binary vs graded? | DECIDED: Binary for now | Phase 1 | Yes | Yes -- Phase 3 does not introduce graded recoverability |

No new convention changes introduced in Phase 3. All Phase 1 convention changes remain correctly applied.

---

## 9. Approximation Validity

| Approximation | Validity Range | Phase 3 Usage | Within Range? |
|--------------|---------------|---------------|---------------|
| Bootstrap percentile CI | N >= 5, exchangeable | Used for aggregate forge rate (N=90) and bootstrap coverage test (N=20) | Yes |
| Clopper-Pearson exact | All N >= 1 | Used for boundary proportions (0/10, 10/10, 0/30, 0/90) | Yes |
| Token count estimation (chars/4) | Short-medium text, ~20-40% error | Mentioned in approximations but not used for any primary metric | N/A |
| Post-hoc JSONL as proxy for live runtime | When ledger captures all lifecycle events | Used throughout Phase 3 campaign | Yes (documented limitation) |

No approximation validity violations detected.

---

## 10. Decision Consistency

Phase 3 decisions CC-009, CC-010, CC-011 are:
- **CC-009:** Post-hoc vs registration-time detection gap is real, not a bug.
- **CC-010:** D7/D8 gaps are findings about forge coverage, not test failures.
- **CC-011:** Accepted negative finding on natural violations.

All three are consistent with the project's approach_policy (which explicitly allows honest negative findings) and with the forbidden proxies (which require natural violations to be assessed separately). CC-011 is particularly important: the acceptance_test "test-real-violation" failed (0 natural violations) but the contract explicitly defined the honest-negative-finding path, and the user approved it.

**PASS** -- all decisions are internally consistent and compatible with prior decisions.

---

## Summary

### Checks Performed: 14

| Check Category | Count | Pass | Fail | Warning |
|---------------|-------|------|------|---------|
| Convention compliance | 11 | 10 | 0 | 0 (1 N/A) |
| Provides/requires chain | 10 | 10 | 0 | 0 |
| Numerical spot-checks | 5 | 5 | 0 | 0 |
| Cross-phase numerical consistency | 3 | 3 | 0 | 0 |
| Semantic consistency | 3 | 3 | 0 | 0 |
| Data integrity | 2 | 2 | 0 | 0 |
| state.json synchronization | 1 | 0 | 0 | 1 |
| Convention evolution | 3 | 3 | 0 | 0 |
| Approximation validity | 4 | 4 | 0 | 0 |
| Decision consistency | 3 | 3 | 0 | 0 |
| **Total** | **45** | **43** | **0** | **1** (+ 1 N/A) |

### Issues Found: 1 (minor)

1. **state.json is stale** -- reflects Phase 2 Plan 01 state while STATE.md reflects Phase 3 completion. Impact: LOW (state.json not consumed by Phase 3 artifacts; convention_lock is correct). Recommendation: resync before Phase 4.

### No Convention Violations Detected

Phase 03 artifacts comply with all 10 applicable project conventions established across Phases 01-02. No convention drift detected.

### No Cross-Phase Numerical Inconsistencies

All quantities transferred between phases (MockLM anchors, baseline values, test counts, detection rates, CI values) are numerically consistent. The independent verification in 03-VERIFICATION.md confirms match to 6+ decimal places for all statistical quantities.

---

_Consistency check completed: 2026-03-16_
_Checked by: gpd-consistency-checker (rapid mode)_
