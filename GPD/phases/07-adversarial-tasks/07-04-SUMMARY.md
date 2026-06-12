---
phase: 07-adversarial-tasks
plan: 04
depth: full
one-liner: "Statistical analysis of 211-run adversarial campaign yields NEGATIVE-STRONG RQ2b verdict (pipeline-validated): 0/211 violations, CP upper 1.73%, Bayesian P(rate>2%)=1.38%, CC-015 triggered"
subsystem: analysis
tags: [statistical-analysis, rq2b-verdict, clopper-pearson, bayesian, fisher-exact, dose-response, negative-finding, cc-015]

requires:
  - phase: 07-adversarial-tasks
    provides: [extended_validator.py with 9/9 D-type detection at 100% (Plan 01), 211-run campaign data in raw_violations.jsonl (Plan 03)]
provides:
  - ViolationAnalysis class with CP CIs, Bayesian posteriors, Fisher's exact tests, dose-response, v1.0/MockLM anchors, verdict logic (tools/violation_analysis.py)
  - 51-test suite verifying all statistical methods against scipy reference values (tools/test_violation_analysis.py)
  - Machine-readable analysis results (data/campaign/analysis_results.json)
  - Self-contained 10-section RQ2b report (docs/violation-campaign-report.md)
affects: [Phase 8 (cross-architecture) proceeds with prevention framing, RQ2b verdict qualified as pipeline-validated]

methods:
  added: [NaN-safe Fisher's exact serialization for both-zero contingency tables]
  patterns: [forbidden-proxy audit as contract enforcement, CC-015 trigger evaluation for research narrative reframing]

key-files:
  created:
    - tools/violation_analysis.py
    - tools/test_violation_analysis.py
    - data/campaign/analysis_results.json
    - docs/violation-campaign-report.md
  modified: []

key-decisions:
  - "Two-sided 95% CP CI convention used throughout (alpha=0.05, alpha/2=0.025 per tail). The plan referenced 0.01489 as CP upper for 0/200, which is the one-sided value; the two-sided value is 0.01828. All results use the two-sided convention consistently."
  - "Fisher's exact odds_ratio returns NaN when both groups have 0 events. Serialized as null in JSON for standards compliance."
  - "CC-015 triggered: recommend reframe from detection to prevention. The negative finding IS the finding."

patterns-established:
  - "Forbidden proxy audit pattern: contract-specified forbidden proxies checked programmatically and reported in analysis results and SUMMARY"
  - "Mock-backend qualification pattern: all verdicts from mock data carry 'pipeline-validated, pending live validation' qualifier"

conventions:
  - "violation_classification = structural only (CONVENTIONS.md #8)"
  - "statistical_conventions = Clopper-Pearson exact 95% CI (two-sided), Beta(1,1) uniform prior, Fisher's exact two-sided, Bonferroni correction for 8 comparisons"
  - "all_metrics_dimensionless = True"
  - "compaction_disambiguation = forge compaction (lossless) vs LLM compaction (lossy)"

plan_contract_ref: "GPD/phases/07-adversarial-tasks/07-04-PLAN.md#/contract"
contract_results:
  claims:
    claim-rq2b-verdict:
      status: passed
      summary: "RQ2b verdict: NEGATIVE-STRONG (pipeline-validated, pending live validation). 0/211 violations, CP 95% upper bound 1.73% (below 2% threshold), Bayesian P(rate>2%) = 1.38% (below 5% threshold). N=211 exceeds 200 minimum. Mock backend qualification applied per fp-mock-as-real."
      linked_ids: [deliv-analysis, deliv-report, test-verdict-decisive, test-statistical-rigor, ref-v1-baseline, ref-mock-experiment, ref-power-analysis]
    claim-dose-response:
      status: passed
      summary: "Dose-response analysis completed: 0 violations at all 4 stress levels (control/mild/moderate/heavy). Cochran-Armitage trend test not applicable (flat at zero). No evidence of stress-intensity driving violations."
      linked_ids: [deliv-analysis, test-dose-response, ref-reliabilitybench]
    claim-category-comparison:
      status: passed
      summary: "Per-category violation rates computed with CP CIs for all 9 categories. Fisher's exact for each adversarial category vs C9 control: all p=1.0. Bonferroni correction applied (8 comparisons, alpha=0.00625). No category significantly different from control."
      linked_ids: [deliv-analysis, deliv-report, test-category-analysis]
  deliverables:
    deliv-analysis:
      status: produced
      path: "tools/violation_analysis.py"
      summary: "ViolationAnalysis class with all required methods: aggregate/per-category/per-dtype rates, adversarial-vs-control Fisher's exact, per-category-vs-control with Bonferroni, dose-response with Cochran-Armitage, v1.0 comparison, MockLM comparison, verdict rendering, forbidden proxy audit, full analysis runner."
      linked_ids: [claim-rq2b-verdict, claim-dose-response, claim-category-comparison]
    deliv-analysis-tests:
      status: produced
      path: "tools/test_violation_analysis.py"
      summary: "51 tests: 14 CP CI tests (10 parametrized + 4 special cases), 5 Bayesian posterior tests, 4 Fisher's exact tests, 6 verdict logic tests (all 4 branches + statistical basis), 3 edge case tests, 2 forbidden proxy audit tests, 2 dose-response tests, 15 integration tests on real campaign data. All passing."
      linked_ids: [test-statistical-rigor]
    deliv-analysis-results:
      status: produced
      path: "data/campaign/analysis_results.json"
      summary: "Machine-readable JSON with all required fields: campaign_summary, aggregate (rate+CI+posterior), per_category, per_dtype, per_stress_level, comparisons (adversarial_vs_control, per_category_vs_control, dose_response), anchors (v1_comparison, mock_comparison), verdict, forbidden_proxy_audit, cc015_trigger, cc015_assessment."
      linked_ids: [claim-rq2b-verdict, test-verdict-decisive]
    deliv-report:
      status: produced
      path: "docs/violation-campaign-report.md"
      summary: "10-section self-contained report: executive summary, campaign overview, violation findings (negative), dose-response, category comparison, anchor comparison, detection pipeline evaluation, CC-015 assessment, limitations, recommendations. Plus 3 appendices (statistical methods, forbidden proxy audit, data provenance)."
      linked_ids: [claim-rq2b-verdict, claim-category-comparison]
  acceptance_tests:
    test-verdict-decisive:
      status: passed
      summary: "Verdict is NEGATIVE-STRONG with N=211 >= 200. CP upper 1.73% <= 2%. Bayesian P(rate>2%) = 1.38% < 5%. Mock-backend qualifier present. Not INCONCLUSIVE."
      linked_ids: [claim-rq2b-verdict, deliv-analysis-results, deliv-report]
    test-statistical-rigor:
      status: passed
      summary: "(1) CP CI uses exact binomial via scipy.stats.beta.ppf (not normal approximation) -- verified to 6 decimal places on 10 test cases. (2) Bayesian posterior uses Beta(1, 212) with uniform prior -- verified against scipy. (3) All p-values two-sided. (4) Bonferroni correction applied for 8 category comparisons (alpha=0.00625). 51/51 tests pass."
      linked_ids: [deliv-analysis, deliv-analysis-tests]
    test-dose-response:
      status: passed
      summary: "Dose-response analysis completed at all 4 stress levels. Trend test not applicable (0 violations). Reported as 'flat at zero' per specification. Tested with synthetic data showing increasing violations to verify Cochran-Armitage implementation."
      linked_ids: [claim-dose-response, deliv-analysis-results]
    test-category-analysis:
      status: passed
      summary: "Per-category rates computed with CP CIs for all 9 categories. Fisher's exact for 8 adversarial-vs-control comparisons with Bonferroni correction. All p=1.0. No significant differences. B8 has widest per-category CI (33.6% upper) due to smallest sample (n=9)."
      linked_ids: [claim-category-comparison, deliv-analysis-results, deliv-report]
  references:
    ref-v1-baseline:
      status: completed
      completed_actions: [compare, cite]
      missing_actions: []
      summary: "v1.0: 0/30, CP upper 11.57%. v2.0: 0/211, CP upper 1.73%. Improvement: 6.7x tighter bound. Fisher's exact p=1.0 (both zero). Detection coverage: 4/9 -> 9/9. Cited in report Section 3 and Section 6."
    ref-mock-experiment:
      status: completed
      completed_actions: [compare, cite]
      missing_actions: []
      summary: "MockLM: 6/6 at registration (100%). Plan 01: 90/90 across 9 D-types (100%). Natural: 0/211 (0%). Gap analysis: 3 hypotheses (prevention, mock limitation, genuine rarity). Cited in report Section 6."
    ref-power-analysis:
      status: completed
      completed_actions: [compare, use]
      missing_actions: []
      summary: "07-RESEARCH.md: N=200 gives 98.2% power at 2%. Achieved N=211 (98.6% power). CP upper 1.73% < planned 1.83% for 0/200 (two-sided). Statistical adequacy confirmed."
    ref-reliabilitybench:
      status: completed
      completed_actions: [cite]
      missing_actions: []
      summary: "Stress calibration framework (arxiv:2601.06112) cited in dose-response analysis. Control/mild/moderate/heavy scoring system used."
  forbidden_proxies:
    fp-injection-as-natural:
      status: rejected
      notes: "Natural violation count computed solely from raw_violations.jsonl. Injection sanity (Plan 01) in separate file. Programmatic audit confirms clean."
    fp-mock-as-real:
      status: rejected
      notes: "Verdict carries 'pipeline-validated, pending live validation' qualifier. Backend=mock documented prominently in report executive summary."
    fp-weak-bound:
      status: rejected
      notes: "CP upper 1.73% < 5% threshold. NEGATIVE-STRONG claim is valid."
    fp-no-comparison:
      status: rejected
      notes: "v1.0 baseline and MockLM anchor comparisons both present in analysis and report."
  uncertainty_markers:
    weakest_anchors: ["Mock backend: violations can only arise from forge instrumentation bugs, not real LLM behavior. RQ2b verdict qualified as pipeline-validated only."]
    unvalidated_assumptions: ["Bernoulli independence assumption untested on real LLM (systematic dependencies possible with shared model state)"]
    competing_explanations: ["0 natural violations: (a) prevention by type system, (b) mock cannot produce LLM violations, (c) genuinely rare. Cannot distinguish without live validation."]
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-rq2b-verdict
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-v1-baseline
    comparison_kind: prior_work
    metric: "CP_upper_bound"
    threshold: "< 11.57% (v1.0 bound)"
    verdict: pass
    recommended_action: "Bound improved from 11.57% to 1.73%. 6.7x tighter."
    notes: "Both mock-backend. v2.0 has 7x more runs and 9/9 D-type coverage vs 4/9."
  - subject_id: claim-rq2b-verdict
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-power-analysis
    comparison_kind: baseline
    metric: "total_runs"
    threshold: ">= 200"
    verdict: pass
    recommended_action: "Statistical adequacy confirmed. Proceed to report."
    notes: "211 >= 200. Power = 98.6% at 2% rate."
  - subject_id: claim-rq2b-verdict
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    metric: "detection_rate_aggregate"
    threshold: ">= 90% per-type detection"
    verdict: pass
    recommended_action: "Pipeline functional. 0 natural violations is valid finding."
    notes: "100% injection detection + 0 natural violations = pipeline works, violations absent on mock."

duration: 25min
completed: 2026-03-28
---

# Plan 04: Statistical Analysis and RQ2b Verdict

**Statistical analysis of 211-run adversarial campaign yields NEGATIVE-STRONG RQ2b verdict (pipeline-validated): 0/211 violations, CP upper 1.73%, Bayesian P(rate>2%)=1.38%, CC-015 triggered**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2 completed
- **Tests:** 51/51 passing
- **Files created:** 4 (analysis code, tests, results JSON, report)

## Key Results

### RQ2b Verdict

**NEGATIVE-STRONG (pipeline-validated, pending live validation)**

| Metric | Value | [CONFIDENCE: MEDIUM] |
|--------|-------|---------------------|
| Natural violations | 0/211 | Mock backend only |
| CP 95% upper bound (two-sided) | 1.73% | Verified against scipy.stats.beta.ppf |
| Bayesian P(rate > 2%) | 1.38% | Beta(1,212) with uniform prior |
| Bayesian P(rate > 5%) | 0.002% | |
| Posterior mean | 0.47% | |

**Confidence rationale:** MEDIUM because mock backend cannot produce LLM-behavioral violations. Statistical methods are verified to 6 decimal places (HIGH statistical confidence), but the underlying data source is mock (MEDIUM ecological validity).

### Anchor Comparisons

| Anchor | v1.0 | v2.0 | Improvement |
|--------|------|------|-------------|
| CP upper bound | 11.57% (0/30) | 1.73% (0/211) | 6.7x tighter |
| D-type detection | 4/9 (44.4%) | 9/9 (100%) | Full coverage |
| Task diversity | ~5 types | 20 templates / 9 categories | 4x |
| MockLM injection | 6/6 (100%) | 90/90 (100%) | Same ceiling |

### Dose-Response

Flat at zero across all stress levels. Cochran-Armitage trend test not applicable.

### Category Comparison

All 9 categories at 0% violation rate. Fisher's exact p=1.0 for all 8 adversarial-vs-control comparisons (Bonferroni corrected).

### CC-015

**Triggered.** Recommend reframing from "violation detection" to "structural violation prevention." The negative finding is the finding.

## Task Commits

1. **Task 1: Statistical analysis** - `ae755c2` (compute)
2. **Task 2: RQ2b report** - `75e8c49` (document)

## Deviations

### Auto-fixed Issues

**1. [Rule 1 - Bug fix] Test helper _make_jsonl**
- **Issue:** Initial test helper iterated over file handle `f` instead of `runs` parameter, causing `io.UnsupportedOperation: not readable` on write-mode file.
- **Fix:** Removed stale iteration loop, iterate over `runs` directly.
- **Verification:** 51/51 tests pass after fix.

**2. [Rule 1 - Bug fix] NaN serialization in Fisher's exact**
- **Issue:** Fisher's exact returns `NaN` odds_ratio when both groups have 0 events. `NaN` is not valid JSON.
- **Fix:** Detect NaN via `math.isnan()` and serialize as `null`.
- **Verification:** `analysis_results.json` validated to contain no NaN values.

**3. [Rule 4 - Missing component] CP CI convention clarification**
- **Issue:** Plan referenced CP upper for 0/200 as 0.01489 (one-sided value). The plan itself specifies "TWO-SIDED 95% CI" convention.
- **Fix:** Used two-sided convention throughout. Documented the distinction in the report Appendix A.
- **Verification:** All values verified against `scipy.stats.beta.ppf(0.975, ...)` to 6 decimal places.

## Artifacts

| File | Description |
|------|-------------|
| `tools/violation_analysis.py` | ViolationAnalysis class with all statistical methods |
| `tools/test_violation_analysis.py` | 51-test suite verified against scipy references |
| `data/campaign/analysis_results.json` | Machine-readable full analysis output |
| `docs/violation-campaign-report.md` | Self-contained 10-section RQ2b report |

## Self-Check: PASSED

- [x] `tools/violation_analysis.py` exists
- [x] `tools/test_violation_analysis.py` exists
- [x] `data/campaign/analysis_results.json` exists (valid JSON, no NaN)
- [x] `docs/violation-campaign-report.md` exists (10 sections + 3 appendices)
- [x] Checkpoint `ae755c2` exists in git log
- [x] Checkpoint `75e8c49` exists in git log
- [x] 51/51 tests pass
- [x] CP CI for 0/211 verified: 0.01733 matches scipy reference
- [x] CP CI for 0/30 verified: 0.11570 matches v1.0 reported value
- [x] Bayesian P(rate>2%) verified: 0.01380 matches Beta(1,212) CDF
- [x] Fisher's exact returns p=1.0 for both-zero case
- [x] Verdict is NEGATIVE-STRONG with pipeline-validated qualifier
- [x] All 4 forbidden proxies clean
- [x] CC-015 trigger evaluated (true)
- [x] v1.0 baseline comparison present (6.7x improvement)
- [x] MockLM anchor comparison present (100% injection vs 0% natural)
- [x] Report is self-contained (all 10 sections have substantive content)

---

_Phase: 07-adversarial-tasks_
_Completed: 2026-03-28_
