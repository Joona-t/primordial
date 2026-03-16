# Consistency Check: Phase 05 (Cross-Reference and Synthesis)

**Mode:** Rapid (post-phase check)
**Checked:** 2026-03-16
**Phase:** 05-cross-reference-and-synthesis (Plans 05-01 and 05-02)
**Checker:** gpd-consistency-checker

---

## Conventions Self-Test

All 18 canonical physics convention slots are N/A for this formal systems project. Custom conventions checked:

| Convention | Self-Test Result |
| --- | --- |
| #1 Absence State Ontology | N/A for Phase 5 (no ontology modifications) |
| #2 Absence Object Form | N/A for Phase 5 (no object creation) |
| #3 State Transition Legality | N/A for Phase 5 (no transitions executed) |
| #4 Provenance Reference Format | N/A for Phase 5 (no refs created) |
| #5 Artifact ID Format | N/A for Phase 5 (no artifacts created) |
| #6 Compaction Disambiguation | RELEVANT -- see compliance check below |
| #7 Metrics Definitions | RELEVANT -- see provides/consumes verification below |
| #8 Violation Classification | RELEVANT -- referenced in verdicts |
| #9 Unit System | PASS -- all metrics dimensionless |
| #10 Hash Integrity | N/A for Phase 5 (no hashing) |
| #11 Protocol Versioning | N/A for Phase 5 (no codec operations) |

**Self-test result:** PASS (no internal convention conflicts)

---

## Provides/Consumes Verification

Phase 5 is the terminal synthesis phase. It CONSUMES from Phases 1-4 and PROVIDES final verdicts.

### Verified Transfers (all values cross-checked against source JSON)

| Quantity | Producer | Consumer | Meaning Match | Value Match | Convention Match | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Aggregate detection rate (0.4444) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact float) | Yes | OK |
| Aggregate CI [0.344, 0.544] | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact) | Yes | OK |
| D1-D6 detected types (3/6) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (D1,D2,D5) | Yes | OK |
| D1-D9 detected types (4/9) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (D1,D2,D5,D9) | Yes | OK |
| Per-type sum = aggregate (40=40) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact) | Yes | OK |
| Natural violations (0) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (empty list = 0) | Yes | OK |
| FPR (0.0) | Phase 3 campaign-report.json | Phase 5 synthesis-report.json | Yes | Yes (0.0) | Yes | OK |
| FPR CP upper bound (11.6%) | Phase 3 campaign-report.json | Phase 5 rq-verdicts.json | Yes | Yes (0.1157 rounds to 11.6%) | Yes | OK |
| Pre-compaction reachability (1.0) | Phase 4 compaction-report.json | Phase 5 synthesis-report.json | Yes | Yes (1.0 exact) | Yes | OK |
| Phase 2 baseline reachability (1.0) | Phase 2 baseline-report.json | Phase 5 synthesis-report.json | Yes | Yes (1.0 exact) | Yes | OK |
| Three-way reachability match | Phase 2 + Phase 4 + MockLM | Phase 5 synthesis-report.json | Yes | Yes (all 1.0) | Yes | OK |
| Structural reach @ 50% (0.8214) | Phase 4 compaction-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact float) | Yes | OK |
| Structural reach @ 80% (0.4375) | Phase 4 compaction-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact float) | Yes | OK |
| Backtracking threshold (80%) | Phase 4 compaction-report.json | Phase 5 synthesis-report.json | Yes | Yes | Yes | OK |
| Compression ratio (1.1959x) | Phase 4 compaction-report.json | Phase 5 synthesis-report.json | Yes | Yes (exact) | Yes | OK |
| Provenance depth (21) | Phase 2 baseline-report.json | Phase 5 synthesis-report.json | Yes | Yes (21.0 mean) | Yes | OK |
| MockLM detection (6/6) | ref-mock-experiment | Phase 5 synthesis-report.json | Yes | Yes | Yes | OK |
| MockLM reachability (1.0) | ref-mock-experiment | Phase 5 synthesis-report.json | Yes | Yes | Yes | OK |
| MockLM compression (1.096x) | ref-mock-experiment | Phase 5 synthesis-report.json | Yes | Yes (avg of 3 scenarios) | Yes | OK |

**Total: 18/18 verified, 0 mismatches.**

### Test-Value Verification (spot checks)

1. **Detection rate arithmetic:** 40 detected / 90 total = 0.44444... Phase 5 reports 0.4444444444444444. Source data has detected=40, total=90, rate=0.4444444444444444. EXACT MATCH.

2. **Gap computation (D1-D6):** MockLM ceiling 6/6 minus forge 3/6 = gap of 3 types. Phase 5 reports gap=3. MATCH.

3. **Gap computation (reachability):** 1.0 - 1.0 = 0.0. Phase 5 reports gap=0.0. MATCH.

4. **Gap computation (compression):** 1.1959 - 1.096 = 0.0999. Phase 5 reports gap=0.0999. MATCH.

5. **CP upper bound verification:** For 0 successes in 30 trials, Clopper-Pearson 95% upper = 1 - (0.025)^(1/30) = 0.1157. Phase 5 reports "11.6%". MATCH (correct rounding).

6. **Monotonicity check:** Structural reachability at deletion fractions 0.1 through 0.9: 0.932, 0.925, 0.917, 0.875, 0.821, 0.750, 0.550, 0.438, 0.250. Strictly decreasing. VERIFIED.

---

## Convention Compliance Matrix

| Convention | Introduced | Relevant to Phase 5? | Compliant? | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| #1 Absence State Ontology | Phase 1 | Indirectly (referenced in verdicts) | Yes | 8 states correctly cited in RQ1 verdict | -- |
| #2 Absence Object Form | Phase 1 | No | N/A | Phase 5 does not create/manipulate objects | -- |
| #3 State Transition Legality | Phase 1 | Indirectly (referenced in verdicts) | Yes | "64 entries, 45 legal, 19 illegal" correctly cited | -- |
| #4 Provenance Reference Format | Phase 1 | Indirectly (reachability metric) | Yes | reachability_fraction correctly defined via BFS on provenance DAG | -- |
| #5 Artifact ID Format | Phase 1 | No | N/A | Phase 5 does not create/validate artifact IDs | -- |
| #6 Compaction Disambiguation | Phase 1 | Yes | MINOR ISSUE | See finding below | Unqualified "compaction" in 2 observable names in side-by-side table |
| #7 Metrics Definitions | Phase 1 | Yes | Yes | All metrics match canonical formulas exactly | -- |
| #8 Violation Classification | Phase 1 | Yes | Yes | "Structural only" scope correctly maintained in verdicts | -- |
| #9 Unit System | Phase 1 | Yes | Yes | All quantities are dimensionless ratios or counts | -- |
| #10 Hash Integrity | Phase 1 | No | N/A | Phase 5 does not perform hashing | -- |
| #11 Protocol Versioning | Phase 1 | No | N/A | Phase 5 does not interact with codecs | -- |

---

## Findings

### Finding 1 (MINOR): Unqualified "compaction" in two observable names

**Convention:** #6 Compaction Disambiguation -- unqualified "compaction" is FORBIDDEN in all derivation and measurement files.

**Violation location:** `data/synthesis/side-by-side-table.md` (rows 15 and 21) and `data/synthesis/synthesis-report.json` (observable names in side_by_side_table array)

**Specific instances:**
- Row 6: "Pre-compaction reachability" -- unqualified
- Row 12: "Violation regression post-compaction" -- unqualified

**Cross-file inconsistency:** The cross-reference report (`docs/cross-reference-report.md`) correctly uses "Violation regression post-simulated-compaction" on line 42, but the side-by-side table and synthesis JSON use the shorter unqualified form.

**Impact:** LOW. The surrounding context makes clear these refer to simulated LLM compaction (Phase 4 results). No reader would confuse these with forge trace compression. However, Convention #6 is explicit: "Unqualified 'compaction' is FORBIDDEN in all derivation and measurement files."

**Suggested fix:** Rename observables to "Pre-simulated-compaction reachability" and "Violation regression post-simulated-compaction" in both `tools/synthesis.py` (the generator) and the output files.

### Finding 2 (INFORMATIONAL): Pre-existing CONVENTIONS.md imprecision

**Location:** `.gpd/CONVENTIONS.md` line 159

**Text:** "Trace compression vs vanilla = 87% reduction (compression_ratio >= 1.87)"

**Issue:** The parenthetical conflates two different metrics. The 87% is `vs_vanilla_pct` (forge output is 87% smaller than vanilla logger output). The `compression_ratio` (original/encoded within forge dedup) is ~1.096x on average across MockLM scenarios, NOT 1.87. The statement "compression_ratio >= 1.87" is numerically incorrect.

**Impact on Phase 5:** NONE. Phase 5 correctly uses compression_ratio = 1.096x for the MockLM ceiling in the side-by-side table, matching the actual experiment_results.json data. The synthesis script does not reference the erroneous CONVENTIONS.md parenthetical.

**Origin:** This is a Phase 1 conventions ledger error, not a Phase 5 error. Flagging for correction.

**Suggested fix:** Change CONVENTIONS.md line 159 to: "Trace compression vs vanilla = 87% reduction (vs_vanilla_pct ~ -87%); compression_ratio ~ 1.096x"

---

## Convention Evolution

No convention changes occurred in Phase 5. All Phase 1 conventions remain active and are correctly applied.

---

## Cross-Phase Error Pattern Checks

| Error Pattern | Checked? | Found? | Notes |
| --- | --- | --- | --- |
| Sign absorbed into definition | Yes | No | No sign conventions in this formal systems project |
| Normalization factor change | Yes | No | All metrics use consistent formulas throughout |
| Implicit assumption violated | Yes | No | RQ verdicts correctly flag limitations (simulated-only, zero naturals) |
| Coupling convention mismatch | N/A | -- | No coupling constants |
| Factor of 2pi error | N/A | -- | No Fourier transforms |
| Wick rotation sign | N/A | -- | No Wick rotations |
| Boundary condition mismatch | N/A | -- | No boundary conditions |
| Metric conflation (compression_ratio vs vs_vanilla_pct) | Yes | No | Phase 5 correctly uses compression_ratio for MockLM comparison, not vs_vanilla_pct |

---

## Narrative Coherence

**Problem-method alignment:** Yes. The research question asks about preventing silent state loss. The methods (ontology formalization, fault injection, compaction measurement) directly address this.

**Result-problem alignment:** Yes. Verdicts directly answer whether typed absence (RQ1), violation detection (RQ2), and compaction survival (RQ3) achieve their goals.

**Conclusion-evidence alignment:** Yes. PARTIAL verdicts are correctly justified by specific evidence gaps (zero natural violations, simulated-only compaction). PASS verdict for RQ1 is correctly justified by all 4 criteria being met.

**Negative findings surfaced:** Yes. Zero natural violations is prominently featured in executive summary, RQ2 verdict, and limitations. Not buried.

**Forbidden proxy audit honest:** Yes. fp-short-tasks reported as UNRESOLVED matching Phase 4 exactly. Not whitewashed.

**Open threads acknowledged:** Yes. Four open questions listed in 05-02-SUMMARY.md, all actionable.

---

## Summary

| Check Category | Checks | Passed | Issues |
| --- | --- | --- | --- |
| Provides/consumes value match | 18 | 18 | 0 |
| Test-value spot checks | 6 | 6 | 0 |
| Convention compliance | 11 | 10 | 1 minor |
| Convention evolution | 0 changes | N/A | 0 |
| Cross-phase error patterns | 8 | 8 | 0 |
| Narrative coherence | 5 | 5 | 0 |
| **Total** | **48** | **47** | **1 minor** |

**Overall assessment:** Phase 5 synthesis is consistent with all upstream phases. All 18 consumed values match source data exactly (programmatic loading eliminates transcription errors). One minor compaction terminology violation in observable names (2 instances of unqualified "compaction" in the side-by-side table, contradicting Convention #6). One informational finding about a pre-existing CONVENTIONS.md imprecision that Phase 5 correctly avoids.

---

_Consistency check by gpd-consistency-checker (rapid mode)_
_Phase: 05-cross-reference-and-synthesis_
_Completed: 2026-03-16_
