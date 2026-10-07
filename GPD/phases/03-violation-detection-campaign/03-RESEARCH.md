# Phase 3: Violation Detection Campaign - Research

**Researched:** 2026-03-16
**Domain:** Fault injection / differential detection / small-sample statistics / agent failure detection
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 is the primary experimental campaign of the Primordial project. It answers the central question: does forge instrumentation detect structural failures on real agent tasks that go undetected by uninstrumented and structured-logging baselines? The phase has two distinct workstreams: (1) a controlled fault injection campaign where all 9 fault types (D1-D9) are injected at least 10 times each to validate detection capability, and (2) a natural violation detection campaign where forge runs on real Zarathustra tasks long enough that naturally-occurring silent failures have opportunity to surface. The acceptance criterion is binary: at least one naturally-occurring violation must be detected (not an injected fault). If none surface, the result is reported honestly as a negative finding.

The recommended approach builds directly on Phase 2 infrastructure: the OpenClawAdapter (4 interception points), the three-tier measurement framework (baseline_measurement.py), and the task corpus (6 tasks: S1-S3 short, L1-L3 long). The fault injection framework extends the existing D1-D6 violations (which achieved 6/6 detection under MockLM) to D7-D9 (compaction data loss, context pressure corruption, timeout/interruption handling). Each injected fault is a targeted corruption at a specific interception point in the OpenClawAdapter pipeline. Detection rates are compared across all three tiers using bootstrap 95% CIs. False positive rate is measured on clean (uninjected) runs. The statistical framework is standard: bootstrap for small samples (N < 30), Clopper-Pearson exact binomial for proportions at boundary values.

**Primary recommendation:** Build a fault injector module that wraps OpenClawAdapter to inject D1-D9 faults at configurable rates and positions, then run the full 6-task corpus through all three tiers with and without injection. Use bootstrap CI on the detection rate difference (forge - uninstrumented) as the primary signal. For natural violations, prioritize long tasks (L1-L3) with >= 5 runs each to maximize exposure to genuine failures.

## Active Anchor References

| Anchor / Artifact | Type | Why It Matters Here | Required Action | Where It Must Reappear |
| --- | --- | --- | --- | --- |
| ref-mock-experiment (6/6 violations caught) | benchmark | Controlled-condition ceiling for detection rate. Phase 3 must compare real detection rates against this 100% ceiling. | Compare; report degradation from ceiling. | plan, execution, verification, final report |
| BASE-01 (uninstrumented baseline) | prior baseline | Floor measurement: 0 violations detected, 0.0 reachability. Differential detection = forge_detections - 0. | Use as comparison arm in differential analysis. | plan, execution, statistical analysis |
| BASE-02 (structured logging baseline) | prior baseline | Intermediate: schema violations detected but no structural violations. Isolates forge's differential value above generic validation. | Use as second comparison arm. | plan, execution, statistical analysis |
| D1-D6 (MockLM violation tests) | prior artifact | Existing 6 fault types with known detection behavior. D1=ForgeNullError, D2=ForgeRefError, D3-D6=ForgeChamberError. | Extend to D7-D9; replicate on real runtime. | plan, execution |
| OpenClawAdapter | carry-forward input | 4 interception points (per-turn, per-patch, cursor advancement, chamber lifecycle) are the fault injection sites. | Use as injection target; do not modify core adapter. | plan, execution |
| baseline_measurement.py | carry-forward input | Three-tier measurement framework with bootstrap CI, metric collection, result persistence. | Extend with fault injection orchestration and detection rate computation. | plan, execution |
| task-corpus.md | carry-forward input | 6 tasks (S1-S3 short, L1-L3 long) with workspace setup, success criteria, and statistical requirements. | Use as campaign task set; prioritize L1-L3 for natural violations. | plan, execution |
| CONVENTIONS.md #8 | contract constraint | Violation classification: structural only (illegal transitions, missing metadata). Distinguished from hallucination, fault, and semantic error. D1-D9 taxonomy is canonical. | Fault injection must target only structural violations per taxonomy. | plan, execution, reporting |

**Missing or weak anchors:**
- **VM access:** Phase 2 noted "VM access pending for full task corpus execution." If the VM is still unavailable, the campaign must run on local infrastructure with recorded/simulated ledger data, which degrades the "naturally-occurring" claim.
- **Natural violation frequency:** Unknown. The project-level research (SUMMARY.md) flagged this as an open question with MEDIUM priority. If the 6-task corpus produces zero natural violations across all runs, the campaign size may be insufficient. The backtracking trigger addresses this.

## Conventions

| Choice | Convention | Alternatives | Source |
| --- | --- | --- | --- |
| Violation scope | Structural only (illegal transitions, missing metadata) | Semantic (wrong values), behavioral (goal drift) | CONVENTIONS.md #8 |
| Fault taxonomy | D1-D9 per CONVENTIONS.md #8 | MAST 14-mode taxonomy, AEGIS error classes | Phase 1 decision |
| Detection metric | detection_rate = violations_detected / total_violations, [0,1] | precision/recall, F1 | CONVENTIONS.md #7 |
| False positive metric | false_positive_rate = false_alarms / clean_runs, [0,1] | false discovery rate | CONVENTIONS.md #7 |
| CI method | Bootstrap 95% CI for N < 30; Clopper-Pearson exact binomial for proportions near 0 or 1 | Wald interval (poor coverage for small N) | METHODS.md |
| Compaction disambiguation | Always qualified: "forge trace compression" vs "LLM context-window compaction" | Unqualified "compaction" is forbidden | CONVENTIONS.md #6 |
| Injection count | >= 10 per fault type (D1-D9), total >= 90 injections | 5 per type (underpowered), 20 per type (expensive) | Phase 3 requirements |
| Runs per task | >= 3 per tier (from task-corpus.md); >= 5 for L1-L3 clean runs (for natural violation exposure) | Fixed at 3 (minimum per requirements) | Task corpus statistical requirements |

**CRITICAL: All equations and results below use these conventions. Detection rate is always structural-violation-only. False positive rate is measured on clean (uninjected) runs only.**

## Mathematical Framework

### Key Equations and Starting Points

| Equation | Name/Description | Source | Role in This Phase |
| --- | --- | --- | --- |
| `detection_rate = violations_detected / total_violations` | Per-tier detection rate | CONVENTIONS.md #7 | Primary metric for each baseline tier |
| `delta_detection = detection_forge - detection_uninstrumented` | Differential detection rate | New for Phase 3 | Primary signal: forge's value above no instrumentation |
| `delta_detection_structured = detection_forge - detection_structured` | Differential vs structured logging | New for Phase 3 | Secondary signal: forge's value above generic validation |
| `FPR = false_alarms / clean_runs` | False positive rate | CONVENTIONS.md #7 | Measured on uninjected runs; must be low for forge to be trustworthy |
| `CI_bootstrap = [percentile(2.5), percentile(97.5)]` of B=10000 resamples | Bootstrap 95% CI | baseline_measurement.py | Uncertainty quantification for all metrics |
| `CI_clopper_pearson = Beta(k, n-k+1).ppf(alpha/2), Beta(k+1, n-k).ppf(1-alpha/2)` | Exact binomial CI | scipy.stats.beta | For proportions at 0/n or n/n where bootstrap degenerates |

### Required Techniques

| Technique | What It Does | Where Applied | Standard Reference |
| --- | --- | --- | --- |
| Targeted fault injection | Corrupt specific forge artifacts at known interception points | D1-D9 injection into OpenClawAdapter pipeline | METHODS.md Method 3 |
| Differential testing (three-tier) | Compare detection across uninstrumented, structured logging, and forge | All campaign runs | METHODS.md Method 7 |
| Bootstrap resampling | Non-parametric CI for small-sample metrics | Detection rates, FPR, all per-task metrics | baseline_measurement.py bootstrap_ci() |
| Clopper-Pearson exact binomial | Exact CI for proportions at boundary (0/n or n/n) | When detection rate is 0.0 or 1.0 | scipy.stats (standard) |
| Positive/negative controls | Injected faults = positive control; clean runs = negative control | Campaign design | Standard experimental methodology |
| Run-level randomization | Randomize injection positions within runs to avoid ordering effects | Fault injection scheduling | Standard experimental design |

### Approximation Schemes

| Approximation | Small Parameter | Regime of Validity | Error Estimate | Alternatives if Invalid |
| --- | --- | --- | --- | --- |
| Bootstrap percentile CI | N >= 5 data points | N in [5, 30]; exchangeability assumed | Coverage probability ~93-97% for N=10 (slightly conservative) | Clopper-Pearson exact binomial for proportions; report exact counts for N < 5 |
| Clopper-Pearson exact | Any N, any proportion | All regimes; conservative (over-covers) | Guaranteed >= 95% coverage | N/A (this is the fallback) |
| Token count estimation (chars/4) | Token estimation error ~20-40% | Short-medium text | Off by up to 40% for code-heavy content | tiktoken for exact counts if available |

## Standard Approaches

### Approach 1: Targeted Fault Injection with Differential Comparison (RECOMMENDED)

**What:** Build a fault injector that wraps OpenClawAdapter to inject each of the 9 fault types (D1-D9) at specific interception points. Run the full task corpus through all three tiers. Compare detection rates across tiers. The injector is a transparent wrapper: it takes a normal adapter call, applies the fault, and passes the corrupted result to the adapter. The adapter's validation logic either catches or misses the fault.

**Why standard:** Targeted fault injection is the established method for measuring detection capability in testing and verification systems (SBQS 2024, ReliabilityBench 2025). It provides controlled positive signals that allow computing detection rates with known denominators. The three-tier comparison (uninstrumented, structured logging, forge) isolates forge's differential contribution.

**Track record:** The MockLM experiment (scenario D) achieved 6/6 detection on D1-D6 under controlled conditions. Phase 3 extends this to D7-D9 and to real runtime conditions where nondeterminism may affect detection.

**Key steps:**

1. **Build fault injector module.** A `FaultInjector` class that wraps OpenClawAdapter method calls and applies specific corruptions:
   - D1 (null collapse): Replace typed absence output with bare `None` (strip `output_state` field)
   - D2 (broken provenance): Replace `source_refs` with refs to nonexistent artifact IDs
   - D3 (corrupted hashes): Modify artifact content after hash computation
   - D4 (fake source refs): Replace `source_refs` with refs that resolve but point to wrong artifacts
   - D5 (missing state label): Remove `output_state` field from absent outputs
   - D6 (illegal state transition): Force a transition that violates TRANSITION_TABLE (e.g., `deleted` -> `unknown`)
   - D7 (compaction data loss): During cursor advancement, silently drop some `task_ids_behind_cursor` entries
   - D8 (context pressure corruption): Truncate artifact output mid-content to simulate memory pressure corruption
   - D9 (timeout/interruption): Call `finalize_on_error()` with a simulated timeout, but continue registering artifacts afterward (violates seal semantics)

2. **Schedule injection campaign.** For each of the 9 fault types, inject at least 10 instances across the 6-task corpus. Randomize injection position within each run (early, middle, late) to avoid ordering effects. Total: >= 90 injections.

3. **Run three-tier comparison on each injected run.** For each injected run, process the same ledger data through uninstrumented (no detection), structured logging (schema validation only), and forge (full structural validation). Record which tier detects which fault.

4. **Run clean (uninjected) runs.** At least 10 clean runs per task (60 total minimum) through forge to measure false positive rate.

5. **Compute metrics.** Per-fault-type detection rate per tier. Overall detection rate per tier. Differential detection (forge - uninstrumented, forge - structured). False positive rate. All with bootstrap 95% CIs.

6. **Natural violation detection.** On the clean runs (step 4) and any additional long-task runs, examine forge's structural validation output for naturally-occurring violations. These are violations that were NOT injected but detected by forge's validation logic.

**Known difficulties at each step:**

- Step 1: D7-D9 require new injection logic not present in MockLM tests. D7 (compaction data loss) is the most subtle -- silently dropping refs may not be detected if the remaining refs still form a valid DAG.
- Step 2: 90 injections across 6 tasks means some tasks get injected more than others. Balance injection density to avoid task-specific artifacts.
- Step 3: The structured logging baseline (structured_logging_baseline.py) only does schema validation, not structural validation. It will miss most D1-D9 faults by design. This is expected and confirms forge's differential value.
- Step 4: 60 clean runs may be insufficient to observe natural violations if they are rare. If no natural violations appear, extend to 100+ runs on L1-L3 only before declaring negative result.
- Step 6: Natural violations may be ambiguous -- was it a genuine silent failure or a forge false positive? Every candidate must be manually reviewed.

### Approach 2: Extended Campaign on Long Tasks Only (FALLBACK)

**What:** If the standard 6-task campaign produces no natural violations, extend the campaign to focus exclusively on L1-L3 (long tasks) with 20+ runs each. Long tasks (128K+ tokens) are more likely to trigger context pressure, retry loops, and state management edge cases where natural violations can surface.

**When to switch:** After the primary campaign (60+ clean runs) produces zero natural violations.

**Tradeoffs:** More expensive (20+ runs per long task = 60+ additional LLM sessions). Narrows the task diversity. But maximizes exposure to the conditions where natural violations are most likely.

### Anti-Patterns to Avoid

- **Counting injected faults as natural violations.** The contract explicitly forbids fp-synthetic-only: at least one naturally-occurring violation must be detected, not just injected faults. Keep injected and natural detections in completely separate tallies.
- **Running only short tasks.** The contract forbids fp-short-tasks: campaign must include tasks long and complex enough that real failures have opportunity to surface. Short tasks (S1-S3) calibrate the baseline but are unlikely to produce natural violations.
- **Comparing forge against uninstrumented only.** Without the structured-logging intermediate tier, the result is trivially favorable to forge (Pitfall 5 from PITFALLS.md). Always report three-tier differential.
- **Treating zero natural violations as failure.** The backtracking trigger explicitly says: "If no naturally-occurring violations surface after the full campaign, honestly report as negative finding." This is a valid experimental outcome, not a failure of the methodology.

## Existing Results to Leverage

### Established Results (DO NOT RE-DERIVE)

| Result | Exact Form | Source | How to Use |
| --- | --- | --- | --- |
| MockLM detection ceiling | 6/6 = 100% on D1-D6 | tools/experiment_results.json, scenario D_violations | Compare real detection rates against this ceiling; report gap |
| MockLM reachability ceiling | 1.0 (100%) all scenarios | tools/experiment_results.json, scenarios A/B/C | Anchor for reachability degradation measurement |
| Uninstrumented detection floor | 0/6 = 0% on D1-D6 | tools/experiment_results.json, scenario D_violations | Expected comparison arm result |
| Phase 2 forge baseline | reachability=1.0, compression_ratio=1.18, validation_errors=0 | data/baselines/baseline-report.json | Carry-forward baseline for comparison |
| Phase 2 uninstrumented baseline | reachability=0.0, violations_detected=0 | data/baselines/baseline-report.json | Carry-forward comparison arm |
| Phase 2 structured logging baseline | reachability=0.0, schema_violations=0 | data/baselines/baseline-report.json | Carry-forward intermediate comparison arm |
| TRANSITION_TABLE | 64 entries: 45 legal, 19 illegal | tools/forge_nulls.py | Use for D6 injection (illegal transitions) and validation |
| Bootstrap CI implementation | bootstrap_ci() with 10000 resamples, seed=42 | tools/baseline_measurement.py | Reuse directly for all CI computation |
| Fault types D1-D6 detection mechanisms | D1=ForgeNullError, D2=ForgeRefError, D3-D6=ForgeChamberError | experiment_results.json scenario D | Use same detection mechanism mapping for D7-D9 |

**Key insight:** D1-D6 already have known detection behavior under MockLM. Phase 3 replicates these on real runtime (where nondeterminism may affect detection) and adds D7-D9 (which are new). Do not re-test D1-D6 under MockLM -- that result is established. Only test D1-D9 on real runtime data.

### Useful Intermediate Results

| Result | What It Gives You | Source | Conditions |
| --- | --- | --- | --- |
| OpenClawAdapter interception points | 4 named injection sites (per-turn, per-patch, cursor advancement, chamber lifecycle) | tools/openclaw_adapter.py | Post-hoc JSONL analysis mode |
| Ledger event schema | Required fields: ts, kind, task_id; optional: ok, detail, meta | tools/structured_logging_baseline.py LEDGER_EVENT_SCHEMA | Validated by Phase 2 baseline runs |
| Task workspace template | Clean workspace setup per task-corpus.md | docs/task-corpus.md | Workspace template section |

### Relevant Prior Work

| Paper/Result | Authors | Year | Relevance | What to Extract |
| --- | --- | --- | --- | --- |
| AEGIS: Automated Error Generation and Attribution for Multi-Agent Systems | arXiv:2509.14295 | 2025 | Closest prior art for automated fault injection in agent systems. 14 MAST failure modes, 9533 trajectories. | Methodology for context-aware error injection; error classification scheme; validate that D1-D9 covers the structural subset of MAST modes. |
| Detecting Silent Failures in Multi-Agentic AI Trajectories | Pathak et al., arXiv:2511.04032 | 2025 | Directly relevant: anomaly detection in agent trajectories with 4275 labeled trajectories. XGBoost achieves 98% accuracy. | The definition of "silent failure" (drift, cycles, missing details) maps to what forge calls "structural violation." Use as framing reference. |
| Revisiting the Relationship Between Fault Detection, Test Adequacy Criteria, and Test Set Size | Just et al., ASE 2020 | 2020 | Foundational: controlling for test set size when measuring detection adequacy. | Methodology for separating test set size effect from adequacy criterion effect in detection rate comparisons. |
| ReliabilityBench | arXiv:2601.06112 | 2025 | Chaos engineering for agent systems. epsilon=0.2 perturbation causes 8.8% degradation. | Validate that D1-D9 perturbation magnitudes are comparable to realistic fault magnitudes. |

## Computational Tools

### Core Tools

| Tool | Version/Module | Purpose | Why Standard |
| --- | --- | --- | --- |
| Python | 3.11+ | All implementation | Matches existing forge tools |
| pytest | 8.x | Test runner for injection tests | Standard; matches existing 354-test suite |
| numpy | 1.26+ | Bootstrap resampling | Already used by baseline_measurement.py |
| scipy.stats | 1.11+ | Clopper-Pearson exact binomial CI via `beta.ppf()` | Standard for exact CIs on proportions; needed when bootstrap degenerates at 0/n or n/n |

### Supporting Tools

| Tool | Purpose | When to Use |
| --- | --- | --- |
| json (stdlib) | Result persistence and ledger parsing | All campaign data I/O |
| random (stdlib) | Injection position randomization (seeded) | Campaign scheduling |
| pathlib (stdlib) | Workspace management | Task workspace setup/teardown |
| collections.Counter | Fault type tallying | Campaign result aggregation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
| --- | --- | --- |
| Custom fault injector | AEGIS framework (arXiv:2509.14295) | AEGIS targets semantic/behavioral faults in multi-agent LLM systems; our faults are structural (missing fields, broken refs, illegal transitions). Custom injector is simpler and precisely targets D1-D9. |
| Bootstrap CI | Exact Fisher test for 2x2 tables | Fisher's handles detected/not x forge/uninstrumented but not continuous metrics. Bootstrap handles both. Use Fisher's as secondary check for the binary detection comparison. |
| scipy for Clopper-Pearson | Manual Beta quantile computation | scipy is cleaner and avoids reimplementation errors. If scipy unavailable, use the Wilson score interval as approximation. |

### Computational Feasibility

| Computation | Estimated Cost | Bottleneck | Mitigation |
| --- | --- | --- | --- |
| Fault injection (90 injections across 6 tasks) | < 1 minute local compute | Building injection harness | Injections are data transformations, not LLM calls |
| Clean campaign runs (60+ runs x 3 tiers) | 60-120 minutes if using recorded ledger data; 3-6 hours if live LLM | LLM API latency for live runs | Use recorded ledger data from Phase 2 for injected runs; live LLM only for natural violation campaign |
| Bootstrap CI computation | < 1 second per metric | None | Negligible |
| Campaign result aggregation | < 10 seconds | None | Negligible |
| Natural violation campaign (20+ long-task runs) | 2-5 hours LLM time | LLM API latency; session length for L1-L3 | Prioritize L1-L3 only; batch overnight if needed |

**Installation / Setup:**
```bash
# scipy is needed for Clopper-Pearson exact binomial CI
pip install scipy  # or: uv add scipy
# All other dependencies (numpy, pytest) already installed from Phase 2
```

## Validation Strategies

### Internal Consistency Checks

| Check | What It Validates | How to Perform | Expected Result |
| --- | --- | --- | --- |
| Injection verification | Each injected fault actually corrupts the intended field | Assert that the injected artifact fails validation before running detection | 100% of injections must produce a structurally invalid artifact |
| Detection ceiling | Forge detects all injected faults (positive control) | Run D1-D6 injected data through forge adapter | Detection rate >= 6/6 (matching MockLM ceiling) |
| Structured logging floor | Structured logging misses structural faults (expected negative) | Run D1-D6 injected data through structured logging | Detection rate < forge detection rate for structural violations |
| Clean run consistency | Multiple clean runs of same task produce consistent results | Compare forge validation output across 3+ clean runs of same task | Zero validation errors on all clean runs (or consistent set of errors) |
| Bootstrap CI coverage | CI computation is correct | Verify on known distribution: generate 1000 samples of size 20 from Binomial(20, 0.7); check 95% CI covers 0.7 >= 95% of the time | Coverage >= 93% (lower bound for percentile bootstrap) |

### Known Limits and Benchmarks

| Limit | Parameter Regime | Known Result | Source |
| --- | --- | --- | --- |
| MockLM ceiling | Controlled, deterministic | 6/6 = 100% detection on D1-D6 | experiment_results.json |
| Uninstrumented floor | No validation | 0/6 = 0% detection | experiment_results.json |
| Phase 2 forge baseline | Real ledger data, 47 events | 0 validation errors on clean data | baseline-report.json |
| Phase 2 structured logging baseline | Real ledger data, 47 events | 0 schema violations on clean data | baseline-report.json |

### Numerical Validation

| Test | Method | Tolerance | Reference Value |
| --- | --- | --- | --- |
| Bootstrap CI on known proportion | Generate Binomial(N, p) samples, verify CI coverage | Coverage >= 93% | Theoretical 95% (percentile bootstrap slightly under-covers) |
| Clopper-Pearson vs bootstrap at boundaries | Compare CIs at 0/n and n/n | Clopper-Pearson interval must be wider (more conservative) | Standard property of exact vs approximate CI |
| Detection rate sanity | forge_detections >= structured_detections >= uninstrumented_detections per fault type | Strict ordering for injected faults | Expected from three-tier design |

### Red Flags During Computation

- **If forge detects fewer injected faults than MockLM ceiling (< 6/6 on D1-D6):** Investigate whether the real runtime introduces conditions that mask the injected fault (e.g., nondeterministic output overwrites the corrupted field). This would be a genuine finding about the MockLM-to-real-LLM validity gap (Pitfall 1).
- **If structured logging detects MORE structural violations than forge:** Something is fundamentally wrong with the measurement. Structured logging has no structural validation logic; it should detect fewer structural violations by construction.
- **If false positive rate > 5% on clean runs:** Forge's validation is too aggressive for real runtime data. Investigate which validation checks are triggering on legitimate data and whether the validation rules need calibration.
- **If all 90 injections are detected with 100% rate:** Suspiciously clean result. Verify that the injection is actually corrupting the data (check that uninstrumented tier genuinely misses the fault). If uninstrumented also detects some, the "fault" may be too obvious (e.g., causing a Python exception rather than a silent failure).
- **If no natural violations appear after 60+ clean runs:** This is the expected difficult case. Do not manufacture violations. Extend to 100+ long-task runs before declaring negative result. If still none, report honestly.

## Common Pitfalls

### Pitfall 1: Conflating Injected and Natural Violations

**What goes wrong:** The campaign detects 90+ violations (all injected) and reports "forge detects violations that uninstrumented misses." This is true but trivially true -- the injected faults were designed to be detectable by forge.
**Why it happens:** Injected faults are easy to count; natural violations are hard to find. The temptation is to report the aggregate number.
**How to avoid:** Maintain completely separate tallies: `injected_detections` and `natural_detections`. The acceptance criterion (at least 1 natural violation) is evaluated ONLY on `natural_detections`. Report both, but frame them differently: injected detections validate the detection mechanism; natural detections validate the practical value.
**Warning signs:** The report does not distinguish injected from natural. The natural detection count is zero but the report claims "forge detected N violations."
**Recovery:** Re-analyze all detections. Flag each as injected (known fault type, known injection point) or natural (no corresponding injection record).

### Pitfall 2: Short Tasks Producing No Natural Violations

**What goes wrong:** The campaign runs S1-S3 (short tasks) as heavily as L1-L3 but counts them equally for natural violation probability. Short tasks are single-step operations that rarely trigger state management failures.
**Why it happens:** Task-corpus.md has equal-weight tasks (3 short + 3 long). Equal run allocation is natural but wrong for this phase.
**How to avoid:** Allocate >= 60% of natural-violation clean runs to L1-L3 (long tasks). Short tasks serve as the clean baseline for FPR measurement. Long tasks serve as the natural violation exposure.
**Warning signs:** All clean runs are on short tasks. The report claims "no natural violations in N runs" but N is mostly short-task runs.
**Recovery:** Run additional long-task-only campaign. Do not count short-task runs toward the natural violation exposure budget.

### Pitfall 3: Bootstrap CI Degeneracy at Boundary Proportions

**What goes wrong:** The detection rate is 0/10 or 10/10 (all-or-nothing). Bootstrap resampling from a sample of all-zeros or all-ones produces a degenerate CI of [0.0, 0.0] or [1.0, 1.0], which is falsely precise.
**Why it happens:** Bootstrap percentile method assumes the sample captures the distribution's variability. A sample of identical values has zero variability.
**How to avoid:** For proportions at 0/n or n/n, use Clopper-Pearson exact binomial CI instead of bootstrap. Clopper-Pearson at 0/10 gives [0.0, 0.308] (95% CI), which honestly reflects the uncertainty.
**Warning signs:** CI width is exactly 0.0. The report claims "detection rate = 0.0 [0.0, 0.0]" -- this conceals real uncertainty.
**Recovery:** Replace bootstrap CI with Clopper-Pearson for all boundary proportions. Report both the point estimate and the CI.

### Pitfall 4: Forge Validation Errors on Legitimate Data

**What goes wrong:** Forge's structural validation (validate_chamber, validate_transition) flags real agent output as invalid when it is actually a legitimate but unexpected pattern. This inflates the false positive rate and undermines trust in natural violation detections.
**Why it happens:** The validation rules were designed against MockLM output (deterministic, well-structured). Real LLM output may have valid patterns not covered by the validation schema (e.g., a novel absence pattern, an unusual source_ref structure).
**How to avoid:** Run a calibration phase: process 5+ clean runs through forge and manually review every validation error. If any are false positives, tighten the validation rules or document the legitimate pattern. Only then begin the formal campaign.
**Warning signs:** Validation error count is high on clean runs (> 2-3 per run). Errors are on the same check for every run.
**Recovery:** Add the legitimate pattern to the validation rules. Re-run the campaign. Document the calibration adjustment.

## Level of Rigor

**Required for this phase:** Controlled experimental measurement with honest statistical reporting.

**Justification:** This is the primary experimental signal of the project. The detection rate comparison is the central claim. It must be measured with proper controls (positive and negative), honest uncertainty quantification (bootstrap CI), and explicit separation of injected vs natural violations.

**What this means concretely:**

- All detection rates must be reported with 95% CIs (bootstrap for N >= 5; Clopper-Pearson for boundary proportions or N < 5).
- Injected and natural violations must be tallied separately and never aggregated in the headline claim.
- Every candidate natural violation must be manually reviewed and documented with the specific validation check that triggered it.
- If no natural violations are found, the result is reported as a negative finding with a bound on what detection rate would be consistent with zero observations (Clopper-Pearson upper bound on 0/N).
- False positive rate must be measured on >= 30 clean runs (across all tasks) to provide a meaningful denominator.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| Manual fault injection in unit tests | Automated fault injection frameworks (AEGIS, ReliabilityBench) | 2025 | Systematic injection is now expected; ad-hoc injection is insufficient for reproducibility |
| Normal-distribution CIs for detection rates | Bootstrap/exact CIs for small samples | Well-established; increasingly adopted in agent evaluation | Wald intervals at N < 30 have poor coverage; bootstrap/exact are required |
| Binary detect/miss per fault | Per-fault-type detection rate with CI | 2025 (AEGIS, Pathak et al.) | Aggregate detection rate obscures which fault types are missed; per-type reporting is expected |
| Single baseline comparison | Three-tier differential (uninstrumented, structured, specialized) | 2025 (Langfuse, Braintrust patterns) | Two-tier comparison is a straw-man; intermediate baseline isolates specific tool value |

**Superseded approaches to avoid:**

- **Wald confidence intervals for proportions:** Use bootstrap or Clopper-Pearson instead. Wald intervals at small N can produce impossible values (< 0 or > 1) and have poor coverage.
- **Aggregate detection rate without per-type breakdown:** Report both aggregate and per-fault-type rates. Aggregate masks which fault types are hardest to detect.

## Open Questions

1. **Will any natural violations occur in the campaign?**
   - What we know: MockLM produced 0 natural violations (by design -- it is deterministic). Phase 2 baseline runs on real ledger data produced 0 validation errors. Natural violations require nondeterministic LLM behavior under context pressure.
   - What is unclear: How frequent are structural violations in real Zarathustra workflows? The SUMMARY.md flagged this as MEDIUM priority with "blocks_phase: none."
   - Impact on this phase: This is the primary acceptance criterion. If no natural violations surface, the phase honestly reports a negative finding.
   - Recommendation: Maximize exposure by running L1-L3 tasks (128K+ tokens) at least 5 times each. If still zero, extend to 10-20 runs. If still zero after 60+ long-task runs, declare negative result and analyze why.

2. **Are D7-D9 detectable by forge's current validation logic?**
   - What we know: D1-D6 are detected by existing validation (ForgeNullError, ForgeRefError, ForgeChamberError). D7-D9 were defined in the taxonomy but not yet implemented or tested.
   - What is unclear: D7 (compaction data loss via silently dropped cursor refs) may not trigger existing validation if the remaining refs still form a valid DAG. D8 (context pressure corruption) manifests as truncated output, which may or may not be caught by null discipline. D9 (post-seal registration) should be caught by ForgeChamberError.
   - Impact on this phase: If D7-D9 are not detected, the detection rate on the full D1-D9 taxonomy will be < 100%, which is an interesting finding about forge's coverage gaps.
   - Recommendation: Implement D7-D9 injection, test on MockLM first (positive control), then on real data. If D7 is not detected, this identifies a gap in forge's validation: silent provenance degradation.

3. **What is the appropriate campaign size for statistical power?**
   - What we know: 10 injections per fault type x 9 types = 90 total injections. For natural violations, 3 runs per task x 6 tasks = 18 clean runs minimum.
   - What is unclear: Whether 18 clean runs is sufficient to detect a natural violation with probability > 50%, assuming natural violation rate is unknown.
   - Impact on this phase: Underpowered campaign = inability to detect natural violations even if they exist at low frequency.
   - Recommendation: Use 5 runs per task for clean campaign (30 total); allocate additional runs to L1-L3 up to 60+ total clean runs. If natural violation rate is p, the probability of observing at least one in N runs is 1 - (1-p)^N. For p=0.05, N=30 gives P(detect) = 0.79; N=60 gives P(detect) = 0.95. For p=0.01, need N=300 (infeasible). Report the detection power curve.

## Alternative Approaches if Primary Fails

| If This Fails | Because Of | Switch To | Cost of Switching |
| --- | --- | --- | --- |
| No natural violations in 60 clean runs | Natural violations too rare at p < 0.02 | Extended long-task campaign (20+ runs on L1-L3 only) | 40-100 additional LLM sessions (4-10 hours) |
| D7-D9 not detected by forge validation | Validation logic does not cover compaction data loss or corruption patterns | Add targeted validation checks for D7-D9 (new validate_* functions) | 1-2 hours development; re-run injection campaign |
| False positive rate too high (> 5%) | Forge validation too strict for real LLM output | Calibration phase: review false positives, adjust validation thresholds | 2-4 hours analysis and code adjustment; re-run clean campaign |
| VM unavailable for live LLM runs | Infrastructure dependency | Run campaign on recorded ledger data with synthetic task extensions | Weakens "naturally-occurring" claim but provides structural detection data |

**Decision criteria:** Abandon primary approach if 100+ clean runs on long tasks produce zero natural violations AND the false positive rate is < 1% (confirming forge validation is neither too loose nor too strict -- it simply is not encountering structural violations in this task domain). This would be a valid negative finding: typed absence catches structural violations that DO NOT naturally occur in coding/patching agent tasks.

## Caveats and Alternatives

### Self-Critique

1. **Assumption that may be wrong:** I assume that 128K+ token long tasks will trigger state management edge cases that produce structural violations. This may not be true if the OpenClaw queue worker's state management is well-implemented and the failure modes are semantic (wrong values) rather than structural (missing/null values).

2. **Alternative approach dismissed too quickly:** The AEGIS framework (arXiv:2509.14295) uses LLM-based adaptive manipulation to inject context-aware errors. This is more sophisticated than our D1-D9 targeted injection. However, AEGIS targets semantic/behavioral failures (14 MAST modes) while our taxonomy targets structural failures (D1-D9). The overlap is partial, and using AEGIS would expand scope beyond the structural violation focus of this project. Still, AEGIS's injection methodology (taking successful trajectories and applying controlled modifications) could inform how D7-D9 injections are designed.

3. **Understated limitation:** The differential detection comparison (forge vs uninstrumented) is inherently favorable to forge because uninstrumented has zero validation by construction. The more meaningful comparison is forge vs structured logging, but structured logging also has zero structural validation by construction. The honest framing is: "forge adds structural violation detection that no generic observability tool provides, because structural violations require domain-specific validation rules."

4. **Simpler method overlooked:** Rather than running a full statistical campaign, a simpler approach would be to manually inspect 10-20 long-task runs and catalog every failure mode observed, then check which ones forge would have caught. This "audit" approach requires less infrastructure but provides qualitative rather than quantitative evidence. It may be a useful complement to the statistical campaign but cannot replace it for the quantitative claims in the contract.

5. **Specialist disagreement:** A software testing researcher might argue that 10 injections per fault type is too few for meaningful per-type detection rates (N=10 gives wide CIs). The response: we report per-type rates with CIs, and the aggregate rate across all 90 injections has a larger denominator. The per-type breakdown identifies coverage gaps even if individual per-type CIs are wide.

## Sources

### Primary (HIGH confidence)

- [Hypothesis PBT Empirical Study, OOPSLA 2025](https://2025.splashcon.org/details/OOPSLA/102/An-Empirical-Evaluation-of-Property-Based-Testing-in-Python) -- Validates PBT methodology used in Phase 1; Phase 3 builds on the test infrastructure
- [Mutation Testing Tools for Python, SBQS 2024](https://dl.acm.org/doi/10.1145/3701625.3701659) -- Benchmarks for mutation testing adequacy that inform test suite quality for Phase 3
- MockLM experiment results (tools/experiment_results.json) -- 6/6 detection ceiling on D1-D6
- Phase 2 baseline data (data/baselines/baseline-report.json) -- Three-tier baseline metrics
- [Revisiting the Relationship Between Fault Detection, Test Adequacy Criteria, and Test Set Size, ASE 2020](https://homes.cs.washington.edu/~rjust/publ/mutants_faults_revisited_ase_2020.pdf) -- Foundational methodology for separating test size from adequacy criterion effects

### Secondary (MEDIUM confidence)

- [AEGIS: Automated Error Generation and Attribution for Multi-Agent Systems, arXiv:2509.14295](https://arxiv.org/abs/2509.14295) -- Closest prior art for automated fault injection in agent systems; 9533 trajectories with MAST taxonomy
- [Detecting Silent Failures in Multi-Agentic AI Trajectories, arXiv:2511.04032](https://arxiv.org/abs/2511.04032) -- Silent failure detection with XGBoost achieving 98% accuracy on 4275 trajectories
- [ReliabilityBench, arXiv:2601.06112](https://arxiv.org/pdf/2601.06112) -- Chaos engineering for agent systems; perturbation analysis
- [Smooth bootstrap-based confidence intervals for binomial proportions, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4789773/) -- Improved bootstrap CI for small-sample proportions
- [Bootstrap Confidence Intervals, Penn State](https://online.stat.psu.edu/stat200/book/export/html/429) -- Standard reference for percentile bootstrap methodology
- [Fault Injection Evaluation with Statistical Analysis, IACR 2025](https://eprint.iacr.org/2025/1287.pdf) -- Statistical methods for fault injection campaign evaluation

### Tertiary (LOW confidence)

- [AgenTracer: Failure Attribution in LLM Agentic Systems, OpenReview](https://openreview.net/pdf/4ad6b1217a99a5f8e7a76d23157ebf94d0e328d6.pdf) -- Multi-granular failure attribution; relevant framing but targets different failure types
- [Automating LLM Drift Detection, DevJournal 2026](https://earezki.com/ai-news/2026-03-12-we-built-a-service-that-catches-llm-drift-before-your-users-do/) -- Drift detection signals; tangentially relevant to natural violation detection

## Metadata

**Confidence breakdown:**

- Mathematical framework: HIGH -- Bootstrap CI, Clopper-Pearson, detection rate formulas are standard statistics applied to well-defined metrics.
- Standard approaches: HIGH -- Targeted fault injection with differential comparison is the established method. Three-tier design addresses the straw-man baseline pitfall.
- Computational tools: HIGH -- numpy, scipy, pytest are mature. The campaign is computationally lightweight; bottleneck is LLM API time.
- Validation strategies: MEDIUM-HIGH -- Positive controls (injected faults) and negative controls (clean runs) are solid. The natural violation detection strategy is sound but outcome-uncertain.
- Natural violation probability: LOW -- Unknown whether structural violations naturally occur in coding/patching tasks at detectable frequency. This is the central experimental uncertainty.

**Research date:** 2026-03-16
**Valid until:** Results are stable (experimental methodology does not expire). Tool versions (numpy, scipy) should be checked if project pauses > 6 months.
