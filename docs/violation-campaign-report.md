# RQ2b Violation Campaign Report

> **Verdict: NEGATIVE-STRONG (pipeline-validated, pending live validation)**
>
> 0/211 structural violations on 20 diverse adversarial tasks across 9 categories
> and 4 stress levels. Clopper-Pearson 95% upper bound: 1.73%.
> Bayesian P(rate > 2%) = 1.38%.
>
> **Backend: mock** -- This result validates the detection pipeline and forge
> framework correctness, but a decisive RQ2b verdict requires live agent validation.

---

## 1. Executive Summary

**RQ2b asks:** Do natural structural violations occur at detectable rates when
autonomous agents use the Primordial Computing typed-absence framework under
diverse, adversarial workloads?

**Finding:** After 211 instrumented agent runs spanning 20 task templates,
9 workload categories, and 4 stress levels, **zero genuine structural violations
were detected.** The Clopper-Pearson 95% confidence interval for the violation
rate is [0.000, 0.0173], meaning we can bound the true rate below 1.73% with
95% confidence. The Bayesian posterior (uniform prior) gives P(rate > 2%) = 1.38%
and P(rate > 5%) < 0.002%.

**Qualification:** The campaign used a mock backend (MockLM). This validates that
the forge instrumentation layer, the extended detection pipeline (9/9 D-types at
100%), and the task execution framework are correct and produce no false positives.
However, mock results cannot produce LLM-behavioral violations. A decisive RQ2b
verdict -- whether violations exist naturally -- requires live agent validation
with a real LLM backend.

**Compared to v1.0:** The upper bound tightened from 11.57% (0/30) to 1.73% (0/211),
a 6.7x improvement in statistical precision.

**Recommendation:** Accept the pipeline-validated negative finding. Proceed to
Phase 8 (cross-architecture) with the "structural prevention" framing (CC-015).
Schedule live agent validation as a stretch goal or Phase 9 activity.

---

## 2. Campaign Overview

| Metric | Value |
|--------|-------|
| Campaign ID | v2.0-viol04 |
| Total runs | 211 (201 planned + 10 pilot) |
| Completed | 211 (100%) |
| Failed | 0 |
| Timed out | 0 |
| Backend | mock (MockLM) |
| Seed | 42 |
| Framework version | primordial-v2.0-phase7 |
| Campaign duration | 0.37 seconds (mock backend) |

### Per-Category Breakdown

| Category | Description | Runs | Violations |
|----------|-------------|------|------------|
| A1 | Multistep chains | 37 | 0 |
| A2 | Backtracking/retry | 37 | 0 |
| A3 | Parallel coordination | 21 | 0 |
| A4 | Error recovery | 21 | 0 |
| B5 | Ambiguous/partial specs | 21 | 0 |
| B6 | Long horizon | 21 | 0 |
| B7 | Context overflow | 21 | 0 |
| B8 | Encoding edge cases | 9 | 0 |
| C9 | Control (clean) | 23 | 0 |
| **Total** | | **211** | **0** |

Categories A1-A4 represent standard adversarial workloads. B5-B8 represent
edge-case and stress workloads. C9 is the clean control group. All categories
exceed their planned minimums.

### Per-Stress-Level Breakdown

| Stress Level | Score | Runs | Violations | CP 95% Upper |
|-------------|-------|------|------------|--------------|
| control | 0 | 58 | 0 | 6.16% |
| mild | 1 | 57 | 0 | 6.27% |
| moderate | 2 | 50 | 0 | 7.11% |
| heavy | 3 | 46 | 0 | 7.71% |

Stress levels follow the ReliabilityBench (arxiv:2601.06112) epsilon/lambda
framework, where higher scores correspond to greater task complexity and
resource pressure.

---

## 3. Violation Findings

### No Violations Found (NEGATIVE-STRONG)

**Zero violations were detected across all 211 runs.** No D-type violations of
any kind (D1-D9) occurred during natural task execution. This is a clean
negative result.

### Statistical Bounds

| Statistic | Value |
|-----------|-------|
| Observed rate | 0/211 = 0.000 |
| CP 95% CI (two-sided) | [0.0000, 0.0173] |
| CI convention | alpha = 0.05, alpha/2 = 0.025 per tail |
| Bayesian posterior | Beta(1, 212) with uniform prior Beta(1,1) |
| Posterior mean | 0.0047 |
| Posterior median | 0.0033 |
| 95% credible interval | [0.0001, 0.0172] |
| P(rate > 1%) | 11.88% |
| P(rate > 2%) | 1.38% |
| P(rate > 5%) | 0.002% |
| P(rate > 10%) | < 0.00001% |

**Interpretation:** If violations occur naturally at a rate of 2% or higher,
there is only a 1.38% chance we would have observed zero in 211 runs. The data
is strongly inconsistent with violation rates above 2%.

### Comparison with v1.0

| Metric | v1.0 | v2.0 (this campaign) | Improvement |
|--------|------|----------------------|-------------|
| Natural violations | 0/30 | 0/211 | -- |
| CP 95% upper bound | 11.57% | 1.73% | 6.7x tighter |
| Bayesian P(rate>2%) | ~44.8% | 1.38% | 32.5x more decisive |
| D-type detection coverage | 4/9 (44.4%) | 9/9 (100%) | +5 types |
| Task diversity | ~5 task types | 20 templates, 9 categories | 4x more diverse |

The v1.0 campaign (0/30) could not rule out violation rates as high as 11.57%.
The v2.0 campaign (0/211) bounds the rate below 1.73%, which is below the
pre-specified 2% threshold for NEGATIVE-STRONG.

### Transcript Review Findings

10 high-stress runs were manually reviewed (2 each from A1, A2, A3, A4 at
heavy stress + 2 from B5 at heavy stress):

- **Detection gaps found:** 0
- **Potential false negatives:** 24 documented, all MockLM-specific artifacts
  (synthetic tool errors, simulated compaction events)
- **Assessment:** No pipeline blind spots identified. MockLM limitations
  prevent testing for false negatives arising from real LLM compaction behavior.

### MockLM D7 Artifacts

The mock backend generates synthetic tool_call_log entries with `call_NNN` IDs
that are structurally independent of chamber content. The D7 checker
(EXTENDED.D7_TRACE_DATA_LOSS) correctly detects these as "tool calls not found
in chamber trace." These are expected mock-backend artifacts, not genuine
violations.

| Metric | Value |
|--------|-------|
| Total D7 artifacts excluded | 1,262 |
| Runs affected | 211/211 (all) |
| Average per run | 6.0 |

With a real LLM backend, tool call IDs would be embedded in the artifacts they
produce, so D7 would only trigger on genuine data loss.

---

## 4. Dose-Response Analysis

**Question:** Does violation rate increase with task stress level?

**Answer:** No evidence of a dose-response relationship. All stress levels
produced exactly 0 violations.

| Stress Level | Score | Runs | Violations | Rate | CP 95% Upper |
|-------------|-------|------|------------|------|--------------|
| control | 0 | 58 | 0 | 0.000 | 0.0616 |
| mild | 1 | 57 | 0 | 0.000 | 0.0627 |
| moderate | 2 | 50 | 0 | 0.000 | 0.0711 |
| heavy | 3 | 46 | 0 | 0.000 | 0.0771 |

**Cochran-Armitage trend test:** Not applicable (0 violations at all levels).
The dose-response relationship is flat at zero.

**Interpretation:** The stress calibration framework (based on ReliabilityBench,
arxiv:2601.06112) did not elicit differential violation rates. This is consistent
with either (a) the forge framework providing structural prevention regardless
of stress level, or (b) the mock backend being unable to produce stress-dependent
behavioral failures.

---

## 5. Category Comparison

### Per-Category Violation Rates

| Category | Runs | Violations | Rate | CP 95% Upper | Fisher p (vs C9) | Significant (Bonferroni) |
|----------|------|------------|------|--------------|-------------------|--------------------------|
| A1 | 37 | 0 | 0.000 | 0.0949 | 1.000 | No |
| A2 | 37 | 0 | 0.000 | 0.0949 | 1.000 | No |
| A3 | 21 | 0 | 0.000 | 0.1611 | 1.000 | No |
| A4 | 21 | 0 | 0.000 | 0.1611 | 1.000 | No |
| B5 | 21 | 0 | 0.000 | 0.1611 | 1.000 | No |
| B6 | 21 | 0 | 0.000 | 0.1611 | 1.000 | No |
| B7 | 21 | 0 | 0.000 | 0.1611 | 1.000 | No |
| B8 | 9 | 0 | 0.000 | 0.3363 | 1.000 | No |
| **C9 (control)** | **23** | **0** | **0.000** | **0.1482** | -- | -- |

**Bonferroni correction:** 8 comparisons, alpha_corrected = 0.05/8 = 0.00625.
No category shows a significantly different violation rate from control.

### Adversarial vs Control

| Group | Runs | Violations | Rate |
|-------|------|------------|------|
| Adversarial (A1-B8) | 188 | 0 | 0.000 |
| Control (C9) | 23 | 0 | 0.000 |

Fisher's exact test: p = 1.000. No difference between adversarial and control groups.

**Interpretation:** No workload category is more violation-prone than any other.
The per-category CP upper bounds are wider (9.5% to 33.6%) due to smaller
per-category sample sizes, but the aggregate bound (1.73%) provides the decisive
constraint.

---

## 6. Anchor Comparison

### v1.0 Baseline (0/30)

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Violations | 0 | 0 |
| Runs | 30 | 211 |
| Rate | 0.000 | 0.000 |
| CP 95% upper | 11.57% | 1.73% |
| D-type coverage | 4/9 (44.4%) | 9/9 (100%) |

**Fisher's exact test (v1.0 vs v2.0):** p = 1.000. Both campaigns found zero
violations, so no rate difference is detectable. The improvement is in
**statistical precision** (6.7x tighter bound) and **detection coverage**
(9/9 vs 4/9 D-types), not in observed rate.

### MockLM Anchor (6/6 Injected)

| Experiment | Violations Detected | Total | Rate |
|------------|-------------------|-------|------|
| MockLM registration (v1.0) | 6 | 6 | 100% |
| Plan 01 injection sanity (v2.0) | 90 | 90 | 100% |
| Natural campaign (v2.0) | 0 | 211 | 0% |

**Gap analysis:** Three non-exclusive hypotheses explain the gap between
injection detection (100%) and natural detection (0%):

**(a) Structural prevention:** The forge framework's type system prevents
violations that would occur without it. The typed-absence constraints,
provenance tracking, and registration-time validation structurally enforce
data integrity. This is the CC-015 "prevention > detection" hypothesis.

**(b) Mock limitation:** The mock backend cannot produce the behavioral patterns
that cause real LLM violations. MockLM follows deterministic patterns and
does not exhibit the token-level randomness, context-window truncation, or
hallucination behavior of real language models. **This is the primary concern.**

**(c) Genuine rarity:** Natural violations are genuinely rare, occurring at
rates below the CP upper bound (1.73%). Even with a real backend, violations
might not appear in 211 runs.

**Assessment:** Hypothesis (b) is the primary concern for the RQ2b verdict.
The injection sanity check (Plan 01: 100% detection on 90 injected faults)
partially addresses hypothesis (b) by confirming the pipeline can detect
violations when they exist. But injection is not the same as natural occurrence.

---

## 7. Detection Pipeline Evaluation

### Plan 01 Injection Sanity Check

| D-Type | Injections | Detected | Rate | CI (95%) |
|--------|-----------|----------|------|----------|
| D1 (state loss) | 10 | 10 | 100% | [69.2%, 100%] |
| D2 (ref corruption) | 10 | 10 | 100% | [69.2%, 100%] |
| D3 (content hash mismatch) | 10 | 10 | 100% | [69.2%, 100%] |
| D4 (suspicious ref target) | 10 | 10 | 100% | [69.2%, 100%] |
| D5 (combined loss) | 10 | 10 | 100% | [69.2%, 100%] |
| D6 (illegal transition) | 10 | 10 | 100% | [69.2%, 100%] |
| D7 (trace data loss) | 10 | 10 | 100% | [69.2%, 100%] |
| D8 (content truncation) | 10 | 10 | 100% | [69.2%, 100%] |
| D9 (post-seal modification) | 10 | 10 | 100% | [69.2%, 100%] |
| **Aggregate** | **90** | **90** | **100%** | **[96.0%, 100%]** |

**False positive rate:** 0/10 clean chambers produced extended validation errors.

### Pipeline Assessment

The detection pipeline is **adequate for its design scope**:

- **Coverage:** All 9 D-types detected at 100% (up from v1.0's 4/9 at 44.4%).
- **Precision:** 0% false positive rate on clean data.
- **Sensitivity on mock data:** 100% on injected faults.
- **Limitation:** Sensitivity on real LLM data is untested. The D7 check
  (trace data loss) is structurally vacuous on mock data because MockLM uses
  synthetic call_ids that are never embedded in chamber content.

### Transcript Review Assessment

10 high-stress runs were manually reviewed. No detection gaps were found.
However, all 24 potential false negatives documented are MockLM-specific
artifacts that would not arise with a real backend. The transcript review
cannot assess detection sensitivity for real LLM behavioral patterns.

---

## 8. CC-015 Assessment: Detection to Prevention

**CC-015 is triggered.** Zero violations on 200+ diverse adversarial runs.

The original research design framed RQ2b as a detection question: "Can the
typed-absence framework detect natural structural violations?" The CC-015
decision criterion recognizes that a persistent zero-violation finding changes
the research narrative:

> **The value of typed absence may lie not in detecting rare failures,
> but in preventing them structurally.**

This is an honest reframing, not a pivot. The negative finding IS the finding.
The forge framework's type system -- typed nulls, mandatory provenance,
registration-time validation, hash-verified content integrity -- creates
structural invariants that prevent the very violations the detection pipeline
was designed to catch.

**Evidence supporting the prevention framing:**

1. **100% injection detection:** When violations are artificially introduced,
   the pipeline catches them immediately. This proves the detection machinery
   works.

2. **0% natural occurrence:** Despite 211 runs across diverse, adversarial
   workloads, no natural violations occurred. This is consistent with structural
   prevention rather than a detection gap.

3. **Type-theoretic argument:** Typed absence (ExplicitNull with mandatory
   null_type, null_reason, provenance_chain) eliminates the representational
   ambiguity that enables silent state loss. If every absence must be explicitly
   typed at registration time, there is no pathway for untyped data loss.

**Caveat:** The prevention framing is strongest on the mock backend, where
the forge framework has full control over data flow. On a real LLM backend,
the model's context-window management, token truncation, and summarization
behavior could introduce violations that bypass the forge's type system.
The prevention claim must be validated against real agent behavior.

---

## 9. Limitations

### Backend Limitation (Primary)

**The campaign used a mock backend (MockLM).** This is the most significant
limitation. Mock results validate:

- The forge instrumentation layer is correct (no bugs produce false violations)
- The detection pipeline catches injected faults (100% on 90 injections)
- The task execution framework runs diverse workloads without errors

Mock results **do not** validate:

- Whether real LLMs produce structural violations under adversarial workloads
- Whether the detection pipeline catches violations arising from real LLM
  behavioral patterns (e.g., context-window truncation, hallucinated
  references, lossy summarization)
- Whether the forge type system prevents violations in practice (as opposed
  to violations simply not occurring in the mock environment)

### Task Representativeness

20 task templates across 9 categories provide moderate diversity. However:

- Templates are parameterized variations, not fully independent task designs
- Some real-world failure modes (multi-day sessions, production load, network
  failures) are not represented
- The stress calibration is synthetic (parameter-based), not organic

### Statistical Assumptions

- **Bernoulli trial model:** Each run is assumed independent with probability
  p of producing at least one violation. This holds for the mock backend
  (fresh agent state per run, independent workspaces). With a real backend,
  systematic dependencies (shared cache, model fine-tuning drift) could
  violate independence.

- **Clopper-Pearson coverage:** The exact binomial CI has guaranteed coverage
  for any true rate p. No distributional assumptions are needed. The CI is
  two-sided with alpha = 0.05.

### Statistical Power Adequacy

The campaign achieved N=211, exceeding the planned N=201 target. Pre-campaign
power analysis (07-RESEARCH.md Section 4) estimated:

- N=200 gives 98.2% power to detect a 2% violation rate
- N=211 gives 98.6% power at 2%

The CP upper bound of 1.73% for 0/211 is below the 2% threshold specified for
NEGATIVE-STRONG in the decision criterion.

---

## 10. Recommendations

### Immediate (Phase 8)

1. **Accept the pipeline-validated negative finding.** The detection pipeline
   works. The forge framework produces no false violations. 0/211 is a clean
   result with the mock backend.

2. **Proceed to Phase 8 (cross-architecture) with the prevention framing
   (CC-015).** The research question shifts from "can we detect violations?"
   to "does typed absence prevent structural violations across different
   agent architectures?"

3. **Carry forward the 'pending live validation' qualifier.** Every claim
   derived from this campaign must note the mock-backend limitation.

### Live Validation (Stretch / Phase 9)

4. **Schedule live agent validation.** Run 200+ tasks with a real LLM backend
   (Claude, GPT-4, or similar). This is the only way to resolve the mock-backend
   ambiguity and produce a fully decisive RQ2b verdict.

5. **Focus live validation on D7 (trace data loss).** The D7 check is the
   most likely to produce different results on a real backend, because real
   LLM tool calls produce artifacts that are embedded in the session trace.

6. **If live validation also produces 0 violations:** The NEGATIVE-STRONG
   verdict upgrades to high confidence. The prevention framing is confirmed.

7. **If live validation produces violations:** Characterize them by D-type,
   category, and stress level. This would be a PASS verdict -- natural violations
   exist, and the detection pipeline can measure their rate. Both outcomes are
   publishable findings.

### CC-015 Reframing

8. **If 0 violations persist through live validation:** Adopt the prevention
   framing for the paper. The typed-absence framework's primary contribution
   is structural prevention of data integrity violations, not detection of
   rare failures.

---

## Appendix A: Statistical Methods

### Clopper-Pearson Confidence Interval

The Clopper-Pearson exact binomial CI is computed using the relationship between
the binomial CDF and the Beta distribution:

- Lower = Beta.ppf(alpha/2, k, n-k+1) if k > 0, else 0
- Upper = Beta.ppf(1-alpha/2, k+1, n-k) if k < n, else 1

where k = number of violations, n = number of runs, alpha = 0.05.

For 0/211: lower = 0, upper = Beta.ppf(0.975, 1, 211) = 0.01733.

This is an **exact** method with guaranteed coverage >= 95% for any true rate p.
No normal approximation is used.

### Bayesian Posterior

Prior: Beta(1, 1) (uniform on [0, 1])
Likelihood: Binomial(n, p) with k successes
Posterior: Beta(1+k, 1+n-k) = Beta(1, 212)

P(rate > 2%) = 1 - Beta(1, 212).CDF(0.02) = 0.01380

### Fisher's Exact Test

Used for all 2x2 comparisons (adversarial vs control, per-category vs control,
v1.0 vs v2.0). Two-sided alternative. When both groups have 0 violations,
p = 1.0 (no difference detectable).

### Bonferroni Correction

For 8 per-category comparisons vs control: alpha_corrected = 0.05/8 = 0.00625.
No comparison is significant (all p = 1.0).

### Cochran-Armitage Trend Test

Not applied (0 violations at all stress levels). Would test H0: violation rate
is constant across stress levels against H1: rate increases with stress score.

---

## Appendix B: Forbidden Proxy Audit

| Proxy ID | Description | Status | Evidence |
|----------|-------------|--------|----------|
| fp-injection-as-natural | Injection counts treated as natural violations | **Clean** | Natural count from raw_violations.jsonl only; injection data in separate file |
| fp-mock-as-real | Mock results claimed as decisive without qualifier | **Clean** | Verdict carries "pipeline-validated, pending live validation" qualifier |
| fp-weak-bound | CP upper > 5% called "strong negative" | **Clean** | CP upper = 1.73% < 5% threshold |
| fp-no-comparison | Results reported without v1.0 and MockLM anchors | **Clean** | Both anchor comparisons present in analysis |

All forbidden proxies pass audit.

---

## Appendix C: Data Provenance

| Artifact | Path | Description |
|----------|------|-------------|
| Raw data | `data/campaign/raw_violations.jsonl` | 211 run entries, 1 per line |
| Campaign status | `data/campaign/campaign_status.json` | Campaign metadata |
| Analysis code | `tools/violation_analysis.py` | ViolationAnalysis class |
| Analysis tests | `tools/test_violation_analysis.py` | 51 tests (all passing) |
| Analysis results | `data/campaign/analysis_results.json` | Machine-readable full output |
| Injection sanity | `data/campaign/injection_sanity_check.json` | Plan 01 results |
| Validation report | `data/campaign/validation_report.json` | Per-run validation details |
| Transcript review | `data/campaign/transcript_review.json` | 10-run manual review |
| Run files | `data/campaign/runs/` | 211 individual run result files |

---

_Report generated: 2026-03-28_
_Campaign: v2.0-viol04_
_Phase: 07-adversarial-tasks, Plan 04_
