# Milestone v1.0 Consistency Check

**Scope:** All 5 phases (10 plans) of Milestone v1.0
**Checker:** gpd-consistency-checker (full milestone audit mode)
**Date:** 2026-03-16
**Project:** Primordial Computing: Typed Absence and Provenance in Agentic Systems

---

## Executive Summary

The v1.0 milestone is **largely consistent** across all 5 phases. Notation, terminology, and parameter values are used coherently throughout. The provides/consumes dependency chain is intact and well-documented. One concrete convention violation was found in CONVENTIONS.md itself (a conflation of two distinct metrics in a test value). Two minor numerical discrepancies exist in compression ratio values cited across phases; both have documented explanations but the explanations are scattered. No sign errors, no contradictory assumptions, no broken research chains.

**Overall status:** CONSISTENT with 1 convention violation (in CONVENTIONS.md itself) and 2 minor numerical tensions requiring documentation cleanup.

---

## 1. Conventions Self-Test

Since all 18 canonical physics conventions are N/A (formal systems research), the self-test focuses on the 11 custom conventions.

### Convention #7 (Metrics Definitions) -- VIOLATION FOUND

**Issue:** CONVENTIONS.md line 159 states:

> Trace compression vs vanilla = 87% reduction (compression_ratio >= 1.87)

This conflates two distinct metrics defined earlier in the same convention entry:

- `compression_ratio = original_size / encoded_size` -- measures forge internal dedup. Actual MockLM values: 1.0846, 1.1035, 1.0997 (mean ~1.096).
- `vs_vanilla_pct = (forge_size - vanilla_size) / vanilla_size * 100` -- measures overhead comparison vs vanilla logger. Actual MockLM values: -88.72%, -88.55%, -84.77% (mean ~-87.3%).

The "87% reduction" figure comes from vs_vanilla_pct (forge traces are 87% smaller than vanilla verbose logs). But `compression_ratio >= 1.87` is wrong -- a compression_ratio of 1.87 would mean forge's own internal dedup achieves 87% compression, which it does not (actual ~1.10x).

**Severity:** MEDIUM. This error is in the conventions ledger itself (the "ground truth"). However, downstream phases do not appear to have been misled by this error: Phase 2 baseline correctly reports compression_ratio=1.18, Phase 4 reports 1.1959, and Phase 5 synthesis correctly uses "1.096x" as the MockLM ceiling for compression_ratio and treats the 87% reduction separately. The error is self-contained in CONVENTIONS.md.

**Fix:** Change line 159 to: `Trace compression vs vanilla = 87% reduction (vs_vanilla_pct ~ -87%); compression_ratio ~ 1.096x`

### All other convention test values: PASS

- Absence states: 8 canonical states match across forge_nulls.py, CONVENTIONS.md, and all phase SUMMARYs
- Transition table: 64 entries (45 legal, 19 illegal) consistent everywhere
- Compaction disambiguation: All phases qualify "compaction" correctly
- Hash integrity: SHA-256 on canonical JSON consistently specified
- Protocol versioning: forge.internal.v1 / forge.trace.v1 consistently used

---

## 2. Provides/Consumes Chain Verification

### Phase 1 --> Phase 2

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|---|---|---|---|---|---|---|
| V1_ABSENCE_STATES (8 states) | Phase 1 Plan 01 | Phase 2 Plan 02 (adapter) | YES | YES (same 8 states) | YES | OK |
| TRANSITION_TABLE (64 entries) | Phase 1 Plan 01 | Phase 3 Plan 01 (fault injection D6) | YES | YES (45 legal, 19 illegal) | YES | OK |
| validate_transition() | Phase 1 Plan 01 | Phase 3 (D6 illegal transition injection) | YES | YES | YES | OK |
| 301 test regression anchor | Phase 1 Plan 02 | Phase 2 Plan 02 (354 total) | YES | YES (301+53=354) | N/A | OK |
| MockLM ceiling (reachability=1.0, detection=6/6) | Phase 1 / state.json | All phases | YES | YES | YES | OK |

### Phase 2 --> Phase 3

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|---|---|---|---|---|---|---|
| OpenClawAdapter + sealed chambers | Phase 2 Plan 02 | Phase 3 Plan 01 (fault injection) | YES | YES (same adapter class) | YES | OK |
| Baseline reachability=1.0 | Phase 2 Plan 04 | Phase 3 Plan 02 (three-tier comparison) | YES | YES | YES | OK |
| bootstrap_ci function | Phase 2 Plan 03 | Phase 3 Plan 01 (reused) | YES | YES (B=10000, seed=42) | YES | OK |
| Three-tier methodology | Phase 2 Plan 04 | Phase 3 Plan 02 (detection campaign) | YES | YES | YES | OK |

### Phase 3 --> Phase 4

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|---|---|---|---|---|---|---|
| D1/D2/D5/D9 detected at 100% | Phase 3 Plan 02 | Phase 4 Plan 01 (regression) | YES | YES (10/10 each) | YES | OK |
| D3/D4/D6/D7/D8 gaps at 0% | Phase 3 Plan 02 | Phase 4 (acknowledged) | YES | YES (0/10 each) | YES | OK |
| Fault injector class | Phase 3 Plan 01 | Phase 4 Plan 01 (violation regression) | YES | YES | YES | OK |

### Phase 4 --> Phase 5

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|---|---|---|---|---|---|---|
| Structural reachability curve | Phase 4 Plan 02 | Phase 5 Plan 01 (synthesis table) | YES | YES (0.932 to 0.250) | YES | OK |
| Pre-compaction reachability=1.0 | Phase 4 Plan 02 | Phase 5 Plan 01 (consistency check) | YES | YES | YES | OK |
| Backtracking threshold at 80% | Phase 4 Plan 02 | Phase 5 Plan 02 (RQ3 verdict) | YES | YES | YES | OK |
| Violation regression 4/4 | Phase 4 Plan 02 | Phase 5 Plan 01 (synthesis row 12) | YES | YES | YES | OK |

### Cross-Phase (Phase 2 baseline --> Phase 4 --> Phase 5)

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
|---|---|---|---|---|---|---|
| Forge compression_ratio | Phase 2 (1.1793) | Phase 4 (1.1959) | YES | **TENSION** | YES | NOTE |

**Tension detail:** Phase 2 baseline-report.json records compression_ratio=1.1793. Phase 4 compaction-report.json pre_compaction_baseline records compression_ratio=1.1959. Phase 5 synthesis uses the Phase 4 value (1.1959x) for the side-by-side table.

Phase 5 Plan 01 key-decisions documents: "Compression ratio sourced from pre_compaction_baseline (1.1959x) rather than baseline-report (1.1793x) -- compaction-report is the Phase 4 canonical source." This acknowledges the discrepancy but does not explain WHY the values differ. The same underlying data (47-event OpenClaw ledger) should produce the same compression ratio.

**Possible cause:** The Phase 4 compaction harness may compute compression_ratio differently from the Phase 2 baseline measurement pipeline (e.g., different serialization, different inclusion of metadata fields in "original_size"). This should be investigated and documented.

**Severity:** LOW. Both values are close (~1.4% relative difference). The Phase 5 synthesis chose one source consistently. But the discrepancy should be explained or reconciled.

---

## 3. Convention Compliance Matrix

| Convention | Introduced | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Notes |
|---|---|---|---|---|---|---|---|
| #1 Absence State Ontology (8 states) | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | Same 8 states everywhere |
| #2 Absence Object Canonical Form | Phase 1 | COMPLIANT | COMPLIANT | N/A | N/A | N/A | |
| #3 State Transition Legality (64 entries) | Phase 1 | COMPLIANT | N/A | COMPLIANT | N/A | COMPLIANT | D6 injection tests illegal transitions |
| #4 Provenance Reference Format | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | N/A | source_refs chains verified |
| #5 Artifact ID Format | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | N/A | Regex-validated in Phase 2 |
| #6 Compaction Disambiguation | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | All uses qualified |
| #7 Metrics Definitions | Phase 1 | **VIOLATION** | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | See Section 1 (CONVENTIONS.md conflates compression_ratio and vs_vanilla_pct in test value) |
| #8 Violation Classification | Phase 1 | COMPLIANT | N/A | COMPLIANT | N/A | COMPLIANT | D1-D9 all structural |
| #9 Unit System (N/A) | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | All dimensionless |
| #10 Hash Integrity | Phase 1 | COMPLIANT | COMPLIANT | COMPLIANT | COMPLIANT | N/A | SHA-256 canonical JSON |
| #11 Protocol Versioning | Phase 1 | COMPLIANT | COMPLIANT | N/A | N/A | N/A | forge.internal.v1 |

---

## 4. Convention Evolution

Three convention changes (CC-001 through CC-003) were documented in Phase 1. Five additional decisions (CC-005 through CC-010) were documented in Phases 2-3.

| Change | Documented | Consistently Applied | Conversion Correct | Status |
|---|---|---|---|---|
| CC-001: resolved->not_generated | YES | YES | N/A (doc fix) | OK |
| CC-002: timed_out/interrupted not added | YES | YES | N/A (decision) | OK |
| CC-003: binary recoverability kept | YES | YES | N/A (decision) | OK |
| CC-005: Zarathustra = OpenClaw | YES | YES | N/A (identity) | OK |
| CC-006: Task corpus = coding/patching | YES | YES | N/A (scope) | OK |
| CC-007: 3 short + 3 long tasks | YES | YES | N/A (scope) | OK |
| CC-008: Real tasks, not SWE-bench | YES | YES | N/A (scope) | OK |
| CC-009: Post-hoc gap vs MockLM | YES | YES | N/A (finding) | OK |
| CC-010: D7/D8 gaps as findings | YES | YES | N/A (finding) | OK |

No undocumented convention drift detected. All convention changes have corresponding entries in CONVENTIONS.md or state.json decisions.

---

## 5. Cross-Phase Error Pattern Analysis

### 5a. Sign conventions absorbed into definitions

Not applicable (formal systems research; no sign conventions).

### 5b. Normalization factors changing

Not applicable (no state normalization conventions).

### 5c. Implicit assumptions becoming explicit constraints

| Assumption | Stated In | Used In | Status |
|---|---|---|---|
| "8 states sufficient" | Phase 1 | All phases | MAINTAINED -- no evidence of insufficiency surfaced |
| "Forge tools integrate cleanly into Zarathustra" | state.json | Phase 2 | VALIDATED -- adapter built and tested |
| "MockLM ceiling is achievable on real data" | state.json | Phase 3-5 | PARTIALLY VALIDATED -- reachability=1.0 matches, detection 3/6 vs 6/6 (explained) |
| "Natural violations will surface" | state.json | Phase 3 | NOT VALIDATED (0/30 clean runs) -- honestly reported as negative finding |

### 5d. Coupling constant convention changes

Not applicable (no coupling constants).

### 5e. Factor-of-2pi conventions

Not applicable.

### 5f. Statistical method consistency

| Method | Convention | Phase 3 | Phase 4 | Phase 5 | Status |
|---|---|---|---|---|---|
| Bootstrap CI | B=10000, seed=42 | COMPLIANT | COMPLIANT | Propagated | OK |
| Clopper-Pearson | Boundary (0/n, n/n) | COMPLIANT | COMPLIANT | Propagated | OK |
| CI auto-selection | CP at boundary, bootstrap at interior | COMPLIANT | COMPLIANT | N/A | OK |

All statistical methods are used consistently across phases.

---

## 6. End-to-End Research Chains

### Chain 1: Ontology --> Transition Table --> Violation Detection --> Synthesis

- Phase 1: 8 states formalized, 64-entry transition table (45 legal, 19 illegal)
- Phase 1: Hypothesis 10K sequences verify zero invariant violations
- Phase 2: Adapter uses V1_ABSENCE_STATES and AbsenceState.NOT_GENERATED correctly
- Phase 3: D6 (illegal transition injection) uses TRANSITION_TABLE as ground truth
- Phase 5: RQ1 verdict cites Phase 1 data correctly (PASS)

**Chain status: INTACT.** All values propagate correctly.

### Chain 2: MockLM Ceiling --> Baselines --> Detection Campaign --> Synthesis

- MockLM: reachability=1.0, detection=6/6, compression_ratio~1.096, vs_vanilla~-87%
- Phase 2: Uninstrumented floor (reachability=0.0, detection=0) confirmed
- Phase 2: Forge baseline reachability=1.0, compression_ratio=1.1793
- Phase 3: Injection campaign 40/90 = 44.4% aggregate, D1-D6 = 3/6 vs MockLM 6/6
- Phase 5: All values in synthesis table match source JSON (programmatic loading)

**Chain status: INTACT.** The MockLM-to-real gap is documented and explained (architectural, not quality).

### Chain 3: Compaction Characterization --> Harness --> Campaign --> Synthesis

- Phase 2 Plan 01: OpenClaw is queue-based (cursor advancement, not LLM summarization)
- Phase 2 Plan 01: Compaction disambiguation enforced
- Phase 4: Simulated LLM compaction via oldest-first deletion
- Phase 4: structural_reachability degrades 0.932 to 0.250
- Phase 4: Backtracking threshold at 80% deletion
- Phase 5: RQ3 verdict PARTIAL, citing simulated-only limitation

**Chain status: INTACT.** The honest scoping of "simulated" vs "genuine" compaction is maintained throughout.

### Chain 4: Forbidden Proxy Tracking

The project defines 3 forbidden proxies (fp-short-tasks, fp-shallow-traces, fp-synthetic-only). Their status is tracked across phases:

| Proxy | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Consistent? |
|---|---|---|---|---|---|
| fp-short-tasks | Partially addressed | Rejected (long task sequences) | **Unresolved** | Unresolved | YES -- Phase 4/5 are more honest than Phase 3's "rejected" |
| fp-shallow-traces | Rejected (depth=21) | Rejected | Rejected | Avoided | YES |
| fp-synthetic-only | N/A | Rejected (separation enforced) | N/A | Avoided | YES |

**Status: CONSISTENT.** The proxy tracking evolves honestly -- Phase 4 escalates fp-short-tasks to "unresolved" rather than maintaining Phase 3's "rejected" status, which is the more honest assessment since no 128K+ token sessions were tested.

---

## 7. Numerical Consistency Spot-Checks

### Test 1: Aggregate detection rate arithmetic

Phase 3 reports: 40/90 = 0.4444...
- D1: 10/10, D2: 10/10, D5: 10/10, D9: 10/10 = 40 detected
- D3: 0/10, D4: 0/10, D6: 0/10, D7: 0/10, D8: 0/10 = 0 detected
- Total detected: 40. Total injections: 90.
- 40/90 = 0.44444... CORRECT.

Phase 5 synthesis consistency check confirms: sum(per_type_detected) = 40 = aggregate_detected. PASS.

### Test 2: Clopper-Pearson CI at 0/10

Phase 3 reports: upper bound = 0.308.
Standard Clopper-Pearson at alpha=0.05, k=0, n=10: upper = 1 - (alpha/2)^(1/n) = 1 - 0.025^(1/10) = 1 - 0.025^0.1.

Using the Beta distribution: Beta.ppf(0.975, 1, 10) = 0.3085 (to 4 decimal places).
Phase 3 reports 0.3084971078187608.

This matches the scipy.stats.beta.ppf(0.975, 1, 10) value exactly. CORRECT.

### Test 3: Clopper-Pearson CI at 0/30

Phase 3 reports: CP upper bound for natural violations 0/30 = 11.6%.
Beta.ppf(0.975, 1, 30) = 0.1157... rounds to 0.116. CORRECT.

### Test 4: Pre-compaction reachability three-way match

- Phase 2 baseline: reachability_fraction = 1.0
- Phase 4 compaction-report pre_compaction_baseline: reachability_fraction = 1.0
- MockLM ceiling: reachability = 1.0
- Phase 5 consistency check: pre_compaction_match = true

CORRECT. Three-way match confirmed.

### Test 5: Structural reachability at 50% deletion

Phase 4 reports structural_reachability = 0.8214 at 50% deletion.
Source data: resolved_refs=92, degraded_refs=0, broken_refs=20, total_refs=112.
structural_reachability = resolved / total = 92/112 = 0.82142857... CORRECT.

### Test 6: MockLM compression ratio

experiment_results.json: 1.0846, 1.1035, 1.0997 (scenarios A, B, C).
Mean = (1.0846 + 1.1035 + 1.0997) / 3 = 3.2878 / 3 = 1.09593...
Rounded to 3 decimal places: 1.096. This matches the "1.096x" used in Phase 5 synthesis. CORRECT.

Note: Scenario D had violations and is excluded from the compression ratio average, which is correct since D is the violation-injection scenario.

---

## 8. Dimensional Consistency

All metrics are dimensionless ratios or counts per Convention #9. Verified:

- reachability_fraction in [0, 1] -- confirmed across all phases
- compression_ratio in (1, inf) -- confirmed (1.1793, 1.1959, 1.096)
- vs_vanilla_pct in (-100, inf) -- confirmed (-87%, +460%)
- detection_rate in [0, 1] -- confirmed (0.0, 0.444, 1.0)
- false_positive_rate in [0, 1] -- confirmed (0.0)
- All CIs bounded within valid metric ranges -- confirmed

No dimensional inconsistencies found. (This check is straightforward since all metrics are dimensionless in this formal systems project.)

---

## 9. Narrative Coherence

### Problem-Method Alignment: YES

The research question ("Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss?") is addressed by:
- Phase 1: Formalizing the typed absence ontology
- Phase 2: Integrating with a real agent runtime (OpenClaw/Zarathustra)
- Phase 3: Testing violation detection via fault injection
- Phase 4: Measuring compaction survival
- Phase 5: Synthesizing across phases with honest verdicts

### Result-Problem Alignment: YES (with honest limitations)

The results directly address the research question:
- RQ1 (formalization): PASS -- the ontology works
- RQ2 (detection): PARTIAL -- mechanism works on injected faults, no natural violations
- RQ3 (compaction): PARTIAL -- structural resilience characterized under simulation only

The PARTIAL verdicts are honest assessments, not evasions.

### Conclusion-Evidence Alignment: YES

No overclaiming detected. Key examples of honest scoping:
- "44.4% rate is ENTIRELY on injected faults" (Phase 5)
- "Simulated results are analytical lower bounds, not empirical measurements" (Phase 4)
- "Zero natural violations weakens the practical value proposition" (Phase 3)
- "fp-short-tasks honestly reported as unresolved" (Phase 4-5)

### Open Threads Acknowledged: YES

All unresolved questions are documented:
1. Natural violation frequency unknown (0/30 with CP UB 11.6%)
2. Genuine LLM compaction not tested (simulated only)
3. fp-short-tasks unresolved (no 128K+ token sessions)
4. D3/D4/D6 post-hoc gap not closed
5. vs_vanilla_pct comparison basis mismatch between MockLM and real baselines

---

## 10. Detailed Findings

### Finding 1: CONVENTIONS.md Metric Conflation (MEDIUM)

**Convention #7, line 159 of CONVENTIONS.md**

The MockLM anchor values section states:
> Trace compression vs vanilla = 87% reduction (compression_ratio >= 1.87)

This is internally inconsistent with Convention #7's own metric definitions:
- `compression_ratio = original_size / encoded_size` -- values around 1.10
- `vs_vanilla_pct = (forge_size - vanilla_size) / vanilla_size * 100` -- values around -87%

The parenthetical "(compression_ratio >= 1.87)" is wrong. A compression_ratio of 1.87 would mean forge internal dedup achieves 87% compression, but actual values are ~1.10 (about 10% compression). The 87% figure describes vs_vanilla_pct, which compares forge trace size to vanilla verbose logger size -- a different comparison entirely.

**Impact:** Low. No downstream phase appears to have used the incorrect test value. Phase 2/3/4/5 all correctly report compression_ratio in the 1.10-1.20 range. The error is confined to CONVENTIONS.md.

**Suggested fix:** Replace line 159 with:
```
- vs_vanilla_pct ~ -87% (forge traces are 87% smaller than vanilla verbose logs)
- compression_ratio ~ 1.096x (forge internal dedup achieves ~9.6% compression)
```

### Finding 2: Compression Ratio Discrepancy (LOW)

**Phase 2 baseline-report.json vs Phase 4 compaction-report.json**

- Phase 2: compression_ratio = 1.1793
- Phase 4: compression_ratio = 1.1959 (pre_compaction_baseline)
- Phase 5: Uses 1.1959x (from Phase 4 as "canonical source")
- Phase 2 docs/baseline-report.md: Reports "1.18" (rounded from 1.1793)
- Phase 4 docs/compaction-report.md: Reports "1.1959"

Both should be computed from the same 47-event OpenClaw ledger. The discrepancy (1.4% relative) suggests either:
(a) Different measurement code paths (baseline_measurement.py vs compaction_harness.py)
(b) Different serialization of the "original" for size comparison
(c) A rounding/truncation difference

Phase 5 acknowledges this: "Compression ratio sourced from pre_compaction_baseline (1.1959x) rather than baseline-report (1.1793x)." But the root cause is not explained.

**Impact:** Low. The two values are close and the choice of which to report is documented.

**Suggested fix:** Investigate whether the two measurement pipelines compute compression_ratio identically. If they use different methods, document both methods explicitly. If one is a bug, fix it.

### Finding 3: state.json Stale Position Data (INFORMATIONAL)

state.json records:
```json
"current_phase": "2",
"current_phase_name": "Integration and Baseline Establishment",
"status": "Executing Phase 2, Wave 1 complete",
"progress_percent": 28
```

But all 5 phases are complete (all 10 plans have SUMMARYs with "completed" status). The state.json was not updated after Phase 2. This is a process issue, not a research consistency issue.

**Impact:** None on research integrity. Process bookkeeping only.

---

## Summary Table

| Check Category | Checks Performed | Issues Found | Severity |
|---|---|---|---|
| Conventions self-test | 11 custom conventions | 1 (metric conflation in test value) | MEDIUM |
| Provides/consumes | 20 cross-phase transfers | 1 (compression ratio tension) | LOW |
| Convention compliance | 11 conventions x 5 phases | 0 additional (1 in self-test) | -- |
| Convention evolution | 9 changes (CC-001 to CC-010) | 0 | -- |
| Cross-phase error patterns | 6 patterns checked | 0 | -- |
| Numerical spot-checks | 6 concrete verifications | 0 (all match) | -- |
| End-to-end chains | 4 research chains | 0 broken | -- |
| Dimensional consistency | All metrics | 0 | -- |
| Narrative coherence | 4 alignment checks | 0 | -- |
| Statistical method consistency | 3 methods across phases | 0 | -- |
| Forbidden proxy tracking | 3 proxies across 5 phases | 0 | -- |

**Total issues: 3 (1 MEDIUM, 1 LOW, 1 INFORMATIONAL)**

---

## Recommendations

1. **Fix CONVENTIONS.md line 159** -- Replace the incorrect `compression_ratio >= 1.87` with the correct metric values for both `compression_ratio` (~1.096x) and `vs_vanilla_pct` (~-87%). This is the highest priority item as it is an error in the ground truth document.

2. **Investigate compression_ratio discrepancy** -- Determine why Phase 2 (1.1793) and Phase 4 (1.1959) report different compression ratios for the same underlying data. Document the root cause.

3. **Update state.json** -- Bring position data current (Phase 5 complete, progress 100%).

---

_Generated by gpd-consistency-checker, full milestone audit mode_
_Milestone: v1.0_
_Date: 2026-03-16_
