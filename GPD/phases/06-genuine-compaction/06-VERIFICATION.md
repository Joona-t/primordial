---
phase: 06-genuine-compaction
verified: 2026-03-28T08:30:00Z
status: gaps_found
score: 8/13 contract targets verified (code deliverables pass; data/claim targets blocked by dry-run)
consistency_score: 10/10 applicable checks passed
independently_confirmed: 7/10 checks independently confirmed
confidence: medium
gaps:
  - subject_kind: "claim"
    subject_id: "claim-compaction-survival"
    expectation: "Provenance chains survive real context-window compaction with measurable reachability"
    expected_check: "Live API data from genuine LLM compaction"
    status: failed
    category: "forbidden_proxy"
    reason: "All 6 trials ran in dry-run mode. Forbidden proxy fp-simulated-only is VIOLATED. No genuine LLM compaction data exists."
    computation_evidence: "Loaded pilot-results.jsonl: all 6 trials have mode='dry-run'. CompactionAnalysis.run_full_analysis() correctly produces PARTIAL verdict with LOW confidence."
    artifacts:
      - path: "data/compaction/genuine/pilot-results.jsonl"
        issue: "Contains only dry-run (synthetic midpoint-split) data, not genuine API data"
      - path: "docs/genuine-compaction-report.md"
        issue: "Report honestly labeled as dry-run but verdict is PARTIAL, not PASS"
    missing: ["Set ANTHROPIC_API_KEY and run: python3 tools/run_pilot_track_a.py"]
    severity: blocker
  - subject_kind: "claim"
    subject_id: "claim-instruction-effect"
    expectation: "Provenance-aware summarization instructions significantly improve artifact ID survival"
    expected_check: "Live Track C ablation with real LLM compaction comparing instruction variants"
    status: failed
    category: "forbidden_proxy"
    reason: "Dry-run synthetic compaction ignores instructions by design. Delta = 0.0 is expected in dry-run."
    computation_evidence: "analysis-results.json shows instruction delta = 0.0, p=1.0. This is correct for dry-run data but proves nothing about the hypothesis."
    artifacts:
      - path: "data/compaction/genuine/analysis-results.json"
        issue: "Instruction delta test on dry-run data is uninformative"
    missing: ["Run live Track C ablation with ANTHROPIC_API_KEY"]
    severity: blocker
  - subject_kind: "claim"
    subject_id: "claim-pipeline-valid"
    expectation: "Measurement pipeline produces valid, interpretable metrics on genuine LLM compaction events"
    expected_check: "At least one live API trial completing successfully"
    status: partial
    category: "convergence"
    reason: "Pipeline logic is validated end-to-end in dry-run. Code infrastructure is complete and tested (885 tests). But the claim requires live API validation."
    computation_evidence: "Ran CompactionAnalysis() on pilot data: correctly loads 6 trials, computes all metrics, produces PARTIAL verdict. Pipeline is functional."
    artifacts:
      - path: "tools/run_pilot_track_a.py"
        issue: "Runner code is complete but has never been executed in live mode"
    missing: ["Live API execution"]
    severity: significant
  - subject_kind: "claim"
    subject_id: "claim-pilot-magnitude"
    expectation: "Pilot data provides initial magnitude estimates for genuine LLM compaction metrics"
    expected_check: "Non-synthetic magnitude estimates from live API"
    status: failed
    category: "spot_check"
    reason: "Dry-run produces deterministic uniform data (survival=0.25 for all trials). This validates computation but provides zero information about genuine compaction magnitude."
    computation_evidence: "All 6 trials show identical metrics: structural_reachability=0.25, artifact_id_survival=0.25. Zero variance. This is the deterministic midpoint-split design, not measurement noise."
    artifacts:
      - path: "data/compaction/genuine/pilot-analysis.json"
        issue: "Aggregated stats are meaningless on deterministic synthetic data"
    missing: ["Live API pilot execution"]
    severity: blocker
  - subject_kind: "deliverable"
    subject_id: "deliv-analysis (naming)"
    expectation: "Contract specifies must_contain: compute_instruction_delta"
    expected_check: "Function name matches contract specification"
    status: partial
    category: "math_consistency"
    reason: "Function is named test_instruction_delta instead of compute_instruction_delta. Functionally equivalent but contract naming violated."
    computation_evidence: "grep confirms test_instruction_delta exists at line 330, compute_instruction_delta does not exist"
    artifacts:
      - path: "tools/compaction_analysis.py"
        issue: "Minor naming deviation from contract"
    missing: ["Either rename function or update contract"]
    severity: minor
comparison_verdicts:
  - subject_kind: claim
    subject_id: "claim-compaction-survival"
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    verdict: inconclusive
    metric: "structural_reachability vs MockLM ceiling"
    threshold: "reachability > 0.5"
    notes: "Dry-run data only. Pipeline correctly computes gap=0.75 from MockLM ceiling but this is from synthetic midpoint-split."
  - subject_kind: claim
    subject_id: "claim-compaction-survival"
    reference_id: ref-knowledge-objects
    comparison_kind: baseline
    verdict: inconclusive
    metric: "artifact_id_survival vs 0.4"
    threshold: "survival > 0.4"
    notes: "Dry-run survival=0.25 is deterministic, not a genuine measurement."
  - subject_kind: claim
    subject_id: "claim-instruction-effect"
    reference_id: ref-knowledge-objects
    comparison_kind: hypothesis_test
    verdict: inconclusive
    metric: "provenance_aware_delta"
    threshold: "delta > 0 with Bonferroni-corrected p < 0.05"
    notes: "Delta=0.0 in dry-run by design."
suggested_contract_checks: []
---

# Phase 6 Verification: Genuine Compaction Experiments

**Phase goal:** Test whether forge provenance chains survive genuine LLM context-window compaction via Anthropic's compact_20260112 API. Establish Semantic Provenance Fidelity (SPF) metric. Render honest RQ3b verdict.

**Verification timestamp:** 2026-03-28T08:30:00Z
**Status:** gaps_found
**Confidence:** MEDIUM (pipeline validated computationally; claims blocked by dry-run-only execution)

**Re-verification:** No (initial verification)

---

## Contract Coverage

| Contract ID | Kind | Status | Confidence | Evidence |
|---|---|---|---|---|
| claim-extraction | claim | VERIFIED | INDEPENDENTLY CONFIRMED | Summary parser tested: precision=1.0 on 3 artifact IDs, all 8 state labels extracted. See Test 6-8 below. |
| claim-fidelity | claim | VERIFIED | INDEPENDENTLY CONFIRMED | tier_classify returns "resolved" for identical text (sim=1.0), "broken" for unrelated (sim=0.0). See Test 8. |
| claim-runner | claim | VERIFIED | INDEPENDENTLY CONFIRMED | Dry-run produces valid JSONL with all metric fields in range. 30 tests pass. |
| claim-templates | claim | VERIFIED | INDEPENDENTLY CONFIRMED | All 3 templates produce 20 iterations with provenance depth >= 5. 33 tests pass. |
| claim-ablation | claim | VERIFIED | INDEPENDENTLY CONFIRMED | 9 conditions generated (3x3), Bonferroni correction applied. 57 tests pass. |
| claim-swebench-agent | claim | VERIFIED | INDEPENDENTLY CONFIRMED | 5-phase agent produces 6 artifacts, depth=5, chamber validates. 33 tests pass. |
| claim-pipeline-valid | claim | PARTIAL | STRUCTURALLY PRESENT | Pipeline logic validated in dry-run. Live API untested. |
| claim-pilot-magnitude | claim | FAILED | UNABLE TO VERIFY | Dry-run data is deterministic synthetic. No genuine magnitude information. |
| claim-compaction-survival | claim | BLOCKED | UNABLE TO VERIFY | Forbidden proxy fp-simulated-only VIOLATED. No live data. |
| claim-instruction-effect | claim | BLOCKED | UNABLE TO VERIFY | Dry-run ignores instructions. Delta=0.0 by design. |
| deliv-analysis | deliverable | VERIFIED | INDEPENDENTLY CONFIRMED | compaction_analysis.py contains CompactionAnalysis, test_reachability_hypothesis, cross_reference_anchors, render_verdict. Minor: test_instruction_delta instead of compute_instruction_delta. |
| deliv-report | deliverable | PARTIAL | STRUCTURALLY PRESENT | Report has all 10 required sections. Content is dry-run-labeled. |
| deliv-analysis-results | deliverable | PARTIAL | STRUCTURALLY PRESENT | JSON has all required keys. Values are from dry-run data. |

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| tools/summary_parser.py | Code: extraction functions | VERIFIED | 9.3KB, 5 functions, 37 tests |
| tools/test_summary_parser.py | Tests | VERIFIED | 18.3KB, 37 tests pass |
| tools/embedding_similarity.py | Code: similarity + tiers | VERIFIED | 12KB, EmbeddingSimilarity class, fallback working |
| tools/test_embedding_similarity.py | Tests | VERIFIED | 13.4KB, 30 pass + 4 skip |
| tools/genuine_compaction_runner.py | Code: experiment runner | VERIFIED | 29.2KB, GenuineCompactionRunner class |
| tools/test_genuine_compaction_runner.py | Tests | VERIFIED | 21.8KB, 30 tests pass |
| tools/task_templates.py | Code: 3 task templates | VERIFIED | 67.2KB, 3 template classes |
| tools/test_task_templates.py | Tests | VERIFIED | 16.8KB, 33 tests pass |
| tools/run_pilot_track_a.py | Code: pilot runner | VERIFIED | 30.8KB, complete pilot script |
| tools/track_c_ablation.py | Code: ablation framework | VERIFIED | 23.9KB, AblationRunner class |
| tools/test_track_c_ablation.py | Tests | VERIFIED | 16.8KB, 57 tests pass |
| tools/swebench_forge_agent.py | Code: forge agent | VERIFIED | 20.5KB, SWEBenchForgeAgent class |
| tools/test_swebench_forge_agent.py | Tests | VERIFIED | 15.9KB, 33 tests pass |
| tools/compaction_analysis.py | Code: analysis pipeline | VERIFIED | 65.4KB, full statistical pipeline |
| tools/test_compaction_analysis.py | Tests | VERIFIED | 32.7KB, 63 tests pass |
| data/compaction/genuine/pilot-results.jsonl | Data: pilot trials | PARTIAL | 6 lines, valid JSONL, but all dry-run mode |
| data/compaction/genuine/pilot-analysis.json | Data: aggregated stats | PARTIAL | Valid JSON, but stats are from synthetic data |
| data/compaction/genuine/analysis-results.json | Data: analysis output | PARTIAL | All required keys present, but values from dry-run |
| docs/pilot-report.md | Report: pilot results | PARTIAL | All sections present, clearly labeled dry-run |
| docs/genuine-compaction-report.md | Report: RQ3b verdict | PARTIAL | 10 sections present, verdict=PARTIAL, honestly labeled |

## Computational Verification Details

### Spot-Check Results (INDEPENDENTLY CONFIRMED)

| Expression / Component | Test Point | Computed | Expected | Match |
|---|---|---|---|---|
| bootstrap_ci([0.5]*100) | Constant data | (0.5000, 0.5000) | (0.5, 0.5) | PASS |
| bootstrap_ci(N(0.7,0.1), N=50) | Variable data | (0.6882, 0.7427) | Contains mean 0.7156 | PASS |
| clopper_pearson_ci(0, 10) | Boundary zero | (0.0000, 0.3085) | (0.0, ~0.31) | PASS |
| wilson_ci(3, 5) | Small sample | (0.2307, 0.8824) | Reasonable range | PASS |
| Bonferroni(0.02, n=3) | Correction | 0.06 | 0.06 | PASS |
| extract_artifact_ids(text) | 3 embedded IDs | 3 IDs extracted | 3 IDs | PASS |
| extract_state_labels(text) | 3 state labels | {not_generated:1, pruned_recoverable:1, unknown:1} | 3 labels | PASS |
| EmbeddingSimilarity identical | sim=1.0 | tier=resolved | resolved | PASS |
| EmbeddingSimilarity different | sim=0.0 | tier=broken | broken | PASS |
| CompactionAnalysis.run_full_analysis() | Full pipeline on dry-run | verdict=PARTIAL, confidence=LOW | PARTIAL | PASS |
| fp-simulated-only audit | All dry-run data | status=violated | violated | PASS |

### Limiting Cases Re-Derived (INDEPENDENTLY CONFIRMED)

**Limit 1: Constant data -> zero-width CI**

The bootstrap CI on constant data [0.5]*100 should produce a degenerate interval (0.5, 0.5) because all bootstrap samples have the same mean. Verified: bootstrap_ci returns exactly (0.5000, 0.5000). This confirms the bootstrap correctly handles the degenerate case.

**Limit 2: Zero successes -> Clopper-Pearson lower = 0**

For 0 successes out of 10 trials, the exact binomial CI should have lower bound = 0.0 and upper bound = 1 - alpha^(1/n) = 1 - 0.025^(1/10) ~ 0.308. Verified: clopper_pearson_ci(0, 10) returns (0.0, 0.3085). The upper bound matches the expected exact binomial value.

**Limit 3: Dry-run -> PARTIAL verdict**

By design, the verdict renderer should always return PARTIAL for dry-run data regardless of metric values. This prevents false PASS/FAIL from synthetic data. Verified: run_full_analysis() on 6 dry-run trials returns rq3b_verdict='PARTIAL' with confidence_tag='LOW' for both claims.

**Limit 4: Identical text -> similarity = 1.0**

The embedding similarity fallback (Jaccard + weighted token overlap average) on identical text should return exactly 1.0. Verified: compute_similarity('hello world test', 'hello world test') = 1.0000.

### Cross-Checks Performed

| Result | Primary Method | Cross-Check Method | Agreement |
|---|---|---|---|
| 885 tests pass | Phase executor claim | Independent `pytest tools/ -q --tb=no` | CONFIRMED: 885 passed, 4 skipped |
| JSONL schema valid | SUMMARY claim | Independent json.loads() on all 6 lines | CONFIRMED: all required fields present |
| Metric ranges valid | SUMMARY claim | Independent assertion on ranges | CONFIRMED: all in [0,1] or >0 |
| Verdict = PARTIAL | SUMMARY claim | Independent run_full_analysis() | CONFIRMED: verdict=PARTIAL |
| fp-simulated-only violated | SUMMARY claim | Independent audit | CONFIRMED: status=violated |
| report sections | SUMMARY claim | Independent content search | CONFIRMED: 10/10 sections present |
| must_contain items | SUMMARY claim | Independent hasattr/import check | CONFIRMED: 13/14 present, 1 minor naming deviation |

### Dimensional Analysis Trace

All metrics in this project are dimensionless (CONVENTIONS.md #7, #9). Verified:

| Metric | Definition | Range | Dimensionless | Status |
|---|---|---|---|---|
| structural_reachability | reachable/total | [0, 1] | Yes (count ratio) | CONSISTENT |
| artifact_id_survival | surviving/total IDs | [0, 1] | Yes (count ratio) | CONSISTENT |
| semantic_fidelity | similarity score | [0, 1] | Yes (correlation) | CONSISTENT |
| degraded_fraction | degraded/total refs | [0, 1] | Yes (count ratio) | CONSISTENT |
| compression_ratio | original/encoded size | [1, inf) | Yes (size ratio) | CONSISTENT |
| p_value | probability | [0, 1] | Yes | CONSISTENT |
| effect_size_d | (mean-threshold)/std | (-inf, inf) | Yes | CONSISTENT |

## Physics Consistency Summary

| Check | Status | Confidence | Notes |
|---|---|---|---|
| 5.1 Dimensional analysis | CONSISTENT | INDEPENDENTLY CONFIRMED | All metrics dimensionless as required. No physical units in project. |
| 5.2 Numerical spot-check | PASS | INDEPENDENTLY CONFIRMED | 11 spot-checks on statistical methods, extraction functions, and pipeline integration. All pass. |
| 5.3 Limiting cases | PASS | INDEPENDENTLY CONFIRMED | 4 limiting cases re-derived: constant data CI, zero-success CP, dry-run verdict, identical text similarity. |
| 5.4 Cross-check | PASS | INDEPENDENTLY CONFIRMED | Test count (885), JSONL schema, metric ranges, verdict, forbidden proxy audit all independently confirmed. |
| 5.5 Intermediate spot-check | PASS | INDEPENDENTLY CONFIRMED | bootstrap_ci, clopper_pearson_ci, wilson_ci all produce expected outputs on known inputs. |
| 5.8 Math consistency | PASS | INDEPENDENTLY CONFIRMED | Bonferroni correction verified: min(raw_p * n, 1.0). CI methods produce expected interval widths. |
| 5.9 Convergence | N/A | N/A | No iterative numerical computations. All metrics are direct ratio computations. |
| 5.10 Literature agreement | PASS | STRUCTURALLY PRESENT | MockLM anchor (1.0), Knowledge Objects (0.4 threshold), v1.0 simulated (0.82 at 50%) all present in analysis. Comparisons are correct on dry-run data. |
| 5.11 Plausibility | PASS | INDEPENDENTLY CONFIRMED | All metrics in valid ranges. dry-run survival=0.25 is consistent with midpoint-split design (5/20 IDs). |
| 5.12 Statistical rigor | PASS | INDEPENDENTLY CONFIRMED | Three CI methods (bootstrap, CP, Wilson) with auto-selection. Bonferroni for multiple comparisons. Scipy RuntimeWarning on constant data is expected and documented. |

**Overall physics assessment:** SOUND for code infrastructure. INCOMPLETE for experimental claims (no live data).

## Forbidden Proxy Audit

| Proxy ID | Contract Source | Status | Evidence | Why It Matters |
|---|---|---|---|---|
| fp-simulated-only | Plan 05 | **VIOLATED** | All 6 trials mode='dry-run'. No ANTHROPIC_API_KEY. | The entire purpose of Phase 6 is genuine compaction. Simulated data was v1.0. |
| fp-cherry-picked | Plan 05 | REJECTED | All 3 categories, both provenance settings reported. | Scientific integrity requires reporting all conditions. |
| fp-short-tasks | Plan 05 | REJECTED | 6/6 trials triggered compaction events (synthetic). Task templates designed for 80K threshold. | Compaction survival is untested if compaction never fires. |
| fp-trivial-extraction | Plan 01 | REJECTED | Test corpus includes messy text, near-misses, duplicates, unicode. | Extraction must handle real LLM output, not clean input. |
| fp-hardcoded-thresholds | Plan 01 | UNRESOLVED | Thresholds (0.7, 0.9) validated on synthetic calibration only. | calibrate_thresholds() exists for post-Track-A recalibration. |
| fp-single-condition | Plan 04 | REJECTED | 9 conditions generated (3x3 matrix). | Ablation must test all variants, not just one. |
| fp-no-provenance | Plan 04 | REJECTED | Forge instrumentation integral. Zero chamber validation errors. | Agent must track provenance, not just run tasks. |
| fp-shallow-traces | Plan 02 | REJECTED | Depth >= 5 after 10 iterations, >= 3 after 5. | Trivial traces don't stress compaction. |

## Comparison Verdict Ledger

| Subject ID | Comparison Kind | Verdict | Threshold | Notes |
|---|---|---|---|---|
| claim-extraction | baseline (MockLM) | pass | precision=1.0, recall>=0.95 | Parser extends MockLM-era minimal regex. |
| claim-fidelity | baseline (Knowledge Objects) | pass | tier classification accuracy | Token overlap fallback correctly classifies extremes. |
| claim-runner | baseline (MockLM) | pass | survival_rate=1.0 for uncompacted | Dry-run pipeline validated against ceiling. |
| claim-templates | existence (MockLM) | pass | depth>=5, prompts>200 chars | All forbidden proxies rejected. |
| claim-ablation | baseline (MockLM) | pass | 9 conditions, valid metrics | Dry-run ablation framework validated. |
| claim-swebench-agent | existence (MockLM) | pass | depth>=5, zero errors | Agent produces valid forge chambers. |
| claim-compaction-survival | baseline (MockLM) | **inconclusive** | reachability>0.5 | Dry-run data only. |
| claim-compaction-survival | baseline (Knowledge Objects) | **inconclusive** | survival>0.4 | Dry-run data only. |
| claim-instruction-effect | hypothesis_test | **inconclusive** | delta>0, Bonferroni p<0.05 | Dry-run ignores instructions. |

## Discrepancies Found

| Severity | Location | Computation Evidence | Root Cause | Suggested Fix |
|---|---|---|---|---|
| BLOCKER | All data files | mode='dry-run' in all 6 JSONL entries | ANTHROPIC_API_KEY not available | Set API key and run live pilot |
| minor | compaction_analysis.py | Function named test_instruction_delta | Naming deviation from contract (compute_instruction_delta) | Rename function or update contract |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| COMP-04: Genuine LLM compaction | BLOCKED | Pipeline built and tested. Live execution requires API key. |
| SPF-01: Semantic Provenance Fidelity | PARTIAL | SPF metric defined (embedding_similarity.py). Baseline measurement requires live data. |

## Anti-Patterns Found

| Category | Severity | Location | Impact |
|---|---|---|---|
| scipy RuntimeWarning | INFO | compaction_analysis.py (constant data) | Expected: constant dry-run data causes precision loss in t-test. Not a bug. |

No physics anti-patterns, stubs, or placeholders detected. All code is substantive and tested.

## Expert Verification Required

None for code infrastructure. When live API data is available:
- Verify compact_20260112 API integration works as documented
- Verify boundary capture correctly identifies compaction events
- Validate tier classification thresholds against genuine LLM compaction data

## Confidence Assessment

**Overall: MEDIUM**

The code infrastructure is thorough and well-tested (885 tests, 0 failures). All statistical methods are independently verified to produce correct results on known inputs. The analysis pipeline correctly handles dry-run data by producing PARTIAL verdicts with LOW confidence. The forbidden proxy fp-simulated-only is honestly flagged as VIOLATED.

However, confidence cannot be HIGH because:
1. The central experimental claim (provenance chains survive genuine LLM compaction) is entirely untested
2. All comparison verdicts against anchor benchmarks are INCONCLUSIVE
3. The phase's primary forbidden proxy (fp-simulated-only) is VIOLATED
4. No live API interaction has occurred

The pipeline is ready for live execution. The single remaining blocker is provisioning ANTHROPIC_API_KEY.

## Gaps Summary

**Root cause: Missing ANTHROPIC_API_KEY environment variable**

All 4 gaps (claim-compaction-survival, claim-instruction-effect, claim-pipeline-valid, claim-pilot-magnitude) share the same root cause: the experiment runner could not make live API calls because ANTHROPIC_API_KEY was not set.

The code infrastructure is complete:
- 8 code deliverables, all tested (283 tests in Phase 6 alone, 885 total regression)
- 5 data/report deliverables, all structurally valid but containing synthetic data
- Statistical methods independently verified (bootstrap CI, Clopper-Pearson, Wilson, Bonferroni)
- Three-anchor comparison framework operational
- Forbidden proxy audit automated and correctly flags VIOLATED status

The honest phase status is: **infrastructure COMPLETE, experimental claims BLOCKED by environment gate.**

To close all gaps: `export ANTHROPIC_API_KEY=<key> && python3 tools/run_pilot_track_a.py`

---

*Verified by: GPD Phase Verifier*
*Profile: review | Autonomy: balanced | Research mode: balanced*
*Computational oracle: 11 executed spot-checks with actual output*
