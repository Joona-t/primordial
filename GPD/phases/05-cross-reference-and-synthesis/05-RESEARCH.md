# Phase 5: Cross-Reference and Synthesis - Research

**Researched:** 2026-03-16
**Domain:** Empirical software research synthesis / experimental cross-reference / verdict assessment
**Confidence:** HIGH

## Summary

Phase 5 is a synthesis phase, not a discovery phase. All experimental data has been collected in Phases 1-4. The task is to aggregate heterogeneous quantitative results (detection rates, reachability fractions, compression ratios, mutation scores) into a coherent cross-reference report, render honest per-research-question verdicts, perform a retrospective forbidden proxy audit, evaluate the four stop/rethink conditions, and document every gap between real-agent results and the MockLM ceiling.

The primary challenge is not computational but methodological: synthesizing mixed evidence with heterogeneous metrics across four prior phases, where results range from strong confirmations (ontology verification: 0 violations in 300K transitions) through partial successes (injection detection: 44.4% aggregate, 4/9 types) to negative findings (natural violations: 0 detected) to incomplete evidence (compaction: simulated only, not genuine LLM compaction). The synthesis must not cherry-pick positive results or understate limitations. The project charter names three specific falsifiers and four stop/rethink conditions that must be evaluated against accumulated evidence.

The recommended approach is a structured narrative synthesis with quantitative side-by-side comparison tables. This is not a meta-analysis (there is no statistical pooling of homogeneous effect sizes); it is a single-project multi-phase cross-reference where each observable is measured once under controlled conditions. The synthesis script should load all machine-readable data from prior phases, compute the side-by-side table programmatically, and produce both JSON and Markdown outputs. The verdict rendering should use an explicit three-level framework (PASS / PARTIAL / FAIL) with stated criteria for each level applied to each research question.

**Primary recommendation:** Build a Python synthesis script that loads `campaign-report.json` and `compaction-report.json`, computes the side-by-side metrics table programmatically, and produces both machine-readable JSON and human-readable Markdown. Render RQ verdicts using the explicit criteria matrix documented below. Write the cross-reference report manually (not auto-generated) for gap analysis, limitation documentation, and stop/rethink evaluation.

## Active Anchor References

| Anchor / Artifact | Type | Why It Matters Here | Required Action | Where It Must Reappear |
| --- | --- | --- | --- | --- |
| ref-mock-experiment (100% provenance, 6/6 violations, 87% compression) | benchmark | The ceiling all real-agent results are measured against. Every gap must be explained. | compare (final) | Side-by-side table, gap analysis section, each RQ verdict |
| deliv-baseline (Phase 2 three-tier baselines) | prior artifact | Floor/intermediate baselines for differential comparison | read, cite | Side-by-side table (uninstrumented and structured columns) |
| deliv-violation-report (Phase 3 campaign data) | prior artifact | Detection rates, FPR, natural violation count, anchor comparison | read, aggregate | Detection rows in side-by-side table, RQ2 verdict |
| deliv-compaction-report (Phase 4 campaign data) | prior artifact | Structural reachability curve, backtracking threshold, violation regression | read, aggregate | Compaction rows in side-by-side table, RQ3 verdict |
| campaign-report.json | machine data | Per-type detection rates with CIs, three-tier comparison, forbidden proxy audit | load, compute | Synthesis script input |
| compaction-report.json | machine data | Deletion sweep results, pre-compaction baseline, violation regression | load, compute | Synthesis script input |
| Phase 1 ontology results | prior artifact | Transition table completeness, Hypothesis verification, mutation score | read, cite | RQ1 verdict |

**Missing or weak anchors:**
- **Genuine LLM compaction data:** Phase 4 used simulated (oldest-first deletion), not real LLM context-window compaction. The compaction-report.json explicitly flags this as a lower bound. The synthesis must surface this limitation prominently.
- **Natural violation data:** Phase 3 found 0 natural violations on 30 clean runs. The CP upper bound (11.6%) provides the constraint, but the absence of empirical natural violations means RQ2 cannot achieve a PASS verdict on the "naturally-occurring detection" criterion.
- **fp-short-tasks:** Phase 4 honestly reported this as "unresolved" (no 128K+ token tasks, no genuine compaction events). The synthesis must confirm this is an unresolved forbidden proxy.

## Conventions

| Choice | Convention | Alternatives | Source |
| --- | --- | --- | --- |
| Metric ranges | Dimensionless ratios in [0, 1] or non-negative integer counts | Percentages | SUMMARY.md, Phase 3/4 conventions |
| CI method | Clopper-Pearson for boundary (0/n, n/n); Bootstrap percentile (B=10000, seed=42) for interior | Normal approximation (rejected: small N) | Phase 3 Plan 01 |
| Compaction terminology | Always qualified: "forge trace compression" vs "LLM context-window compaction" vs "simulated LLM compaction" | Unqualified "compaction" (forbidden) | SUMMARY.md Convention #6 |
| Hash integrity | SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True) | MD5 (rejected: collision risk) | Phase 2-4 conventions |
| Verdict levels | PASS / PARTIAL / FAIL with stated criteria per RQ | Numeric scores, Likert scales | Chosen for this phase (justified below) |

**CRITICAL: All equations and results below use these conventions. All prior phase data uses compatible conventions (verified in Phase 3 and Phase 4 summaries).**

## Mathematical Framework

### Key Equations and Starting Points

| Equation | Name/Description | Source | Role in This Phase |
| --- | --- | --- | --- |
| `detection_rate = detected / total` | Per-type detection rate | Phase 3 | Populate violation detection rows in side-by-side table |
| `differential = rate_forge - rate_uninstrumented` | Differential detection | Phase 3 | Quantify forge's added value vs baseline |
| `structural_reachability = resolved_refs / total_refs` | Provenance structural reachability | Phase 4 | Populate compaction rows in side-by-side table |
| `compression_ratio = encoded_size / original_size` | Forge trace compression | Phase 2 | Populate compression rows |
| `Clopper-Pearson CI: Beta.ppf(alpha/2, k, n-k+1), Beta.ppf(1-alpha/2, k+1, n-k)` | Exact binomial CI | Phase 3 | CIs on boundary proportions (0/n, n/n) |
| `Bootstrap percentile CI: percentile(bootstrap_samples, [2.5, 97.5])` | Nonparametric CI | Phase 3 | CIs on interior proportions |

### Required Techniques

| Technique | What It Does | Where Applied | Standard Reference |
| --- | --- | --- | --- |
| Narrative synthesis | Integrates heterogeneous quantitative results without statistical pooling | Cross-reference report | Cochrane Handbook Ch. 12; PRISMA guidelines |
| Side-by-side comparison table | Aligns multiple treatment arms on same observables | Primary deliverable table | Standard experimental reporting |
| Verdict rendering with explicit criteria | Classifies each RQ as PASS/PARTIAL/FAIL against pre-stated thresholds | Per-RQ assessment section | JBI critical appraisal; GRADE framework adapted |
| Gap analysis | For each observable, computes gap = ceiling - measured and explains the gap | MockLM comparison section | Standard benchmarking practice |
| Retrospective forbidden proxy audit | Checks post-hoc whether experimental design constraints were honored | Forbidden proxy section | Clinical trial protocol deviation audits |

### Approximation Schemes

No approximation schemes are needed for this phase. All data is exact (counts, ratios) or already has CIs computed in prior phases. The synthesis aggregates existing results; it does not introduce new approximations.

## Standard Approaches

### Approach 1: Structured Narrative Synthesis with Programmatic Table Generation (RECOMMENDED)

**What:** Write a Python script that loads all machine-readable data from Phases 2-4, computes the side-by-side metrics table programmatically, and outputs both JSON (for future consumption) and Markdown (for the report). Write the qualitative sections (gap analysis, RQ verdicts, stop/rethink evaluation, forbidden proxy audit) as a manually authored Markdown report that references the programmatic table.

**Why standard:** Narrative synthesis is the established method for integrating heterogeneous experimental results where meta-analytic pooling is inappropriate (different metrics measure different constructs). Programmatic table generation ensures no transcription errors from prior phase data.

**Track record:** Used in Cochrane reviews with mixed outcomes, software engineering empirical evaluations (ACM SIGSOFT empirical standards), and multi-phase experimental campaigns.

**Key steps:**

1. Load machine-readable data: `campaign-report.json`, `compaction-report.json`, `baseline-report.json`
2. Compute the four-column side-by-side table: MockLM ceiling | Uninstrumented floor | Structured logging baseline | Forge-instrumented treatment
3. For each observable row, compute the gap = ceiling - measured and the differential = treatment - floor
4. Render RQ verdicts using the criteria matrix (see below)
5. Evaluate each stop/rethink condition against accumulated evidence
6. Perform retrospective forbidden proxy audit
7. Write human-readable cross-reference report with explicit limitations section
8. Output machine-readable synthesis JSON for potential future use

**Known difficulties at each step:**

- Step 1: Data files have slightly different structures (campaign-report.json has per-type breakdowns; compaction-report.json has per-deletion-fraction sweeps). The script must normalize to a common comparison format.
- Step 3: Some gaps cannot be computed numerically (e.g., "6/6 violation types detected" vs "3/6 types detected" is a count, not a rate). Handle both rate gaps and count gaps.
- Step 4: The verdict for RQ2 is the most complex because it has both a strong positive signal (differential detection on injected faults) and a negative finding (0 natural violations). The verdict criteria must distinguish mechanism validation from practical value.
- Step 6: fp-short-tasks is honestly "unresolved" from Phase 4. The audit must surface this without treating it as a protocol violation (it was honestly flagged during execution).

### Approach 2: Pure Manual Report (FALLBACK)

**What:** Write the entire cross-reference report manually, copying numbers from prior phase summaries and reports.

**When to switch:** If the machine-readable data files are corrupted or missing.

**Tradeoffs:** Higher risk of transcription errors. Harder to update if prior phase data is corrected. But simpler to implement and more flexible for qualitative judgment.

### Anti-Patterns to Avoid

- **Cherry-picking positive results:** The synthesis must give equal weight to the negative finding (0 natural violations) as to the positive finding (44.4% injected detection rate). Quoting only the positive undermines scientific credibility.
- **Conflating simulated and genuine compaction:** Phase 4 results are from simulated LLM compaction (oldest-first deletion). The synthesis must never state "compaction survival was measured" without the qualifier "simulated." Genuine LLM compaction was not tested.
- **Inflating CIs as "uncertainty":** The CIs from Phases 3-4 are narrow because the measurements are deterministic on the same data (CV=0%). The real uncertainty is not in the measurement but in the generalizability (limited task corpus, limited trace diversity). The synthesis must distinguish measurement precision from external validity.
- **Treating PARTIAL as failure:** A PARTIAL verdict means the evidence supports the claim under restricted conditions. This is a scientifically valid and often the most honest outcome for empirical research.

## Existing Results to Leverage

### Established Results (DO NOT RE-DERIVE)

| Result | Exact Form | Source | How to Use |
| --- | --- | --- | --- |
| MockLM ceiling: detection | 6/6 violation types (D1-D6) at registration time | Phase 2/3, experiment_results.json | Column 1 of side-by-side table |
| MockLM ceiling: reachability | 1.0 (100%) | Phase 2, experiment_results.json | Column 1 of side-by-side table |
| MockLM ceiling: compression | 87% (1.096x encoded/original) | Phase 2, experiment_results.json | Column 1 of side-by-side table |
| Uninstrumented floor: detection | 0 (no validation at all) | Phase 2, baseline-report.json | Column 2 of side-by-side table |
| Uninstrumented floor: reachability | 0.0 (no provenance tracking) | Phase 2, baseline-report.json | Column 2 of side-by-side table |
| Structured logging: detection | 0 (no typed-absence checks) | Phase 2, baseline-report.json | Column 3 of side-by-side table |
| Forge detection: aggregate | 40/90 = 44.4% [CI: 0.344, 0.544] | Phase 3, campaign-report.json | Column 4 of side-by-side table |
| Forge detection: per-type | D1/D2/D5/D9 at 100%; D3/D4/D6/D7/D8 at 0% | Phase 3, campaign-report.json | Detailed detection breakdown |
| Natural violations | 0/30 (CP upper bound 11.6%) | Phase 3, campaign-report.json | RQ2 negative finding |
| FPR | 0/30 = 0.0% (CP upper bound 11.6%) | Phase 3, campaign-report.json | Precision assessment |
| Pre-compaction reachability | 1.0 (matches MockLM ceiling) | Phase 4, compaction-report.json | Pre-compaction baseline confirmation |
| Simulated compaction reachability curve | 0.932 (10%) to 0.250 (90%) | Phase 4, compaction-report.json | Compaction degradation profile |
| Backtracking threshold | Crossed at 80% deletion (structural_reachability = 0.438) | Phase 4, compaction-report.json | Stop/rethink evaluation |
| Violation regression | D1/D2/D5/D9 at 100% post-compaction | Phase 4, compaction-report.json | Detection independence from compaction |
| Ontology verification | 10K+ sequences, 300K transitions, 0 violations | Phase 1, 01-02-SUMMARY.md | RQ1 evidence |
| Mutation score | 99% (103/104 non-equivalent killed) | Phase 1, 01-02-SUMMARY.md | RQ1 test quality |
| Transition table | 45 legal, 19 illegal, 64 total | Phase 1, 01-01-SUMMARY.md | RQ1 completeness |

**Key insight:** All quantitative results exist in machine-readable JSON. The synthesis script should load them programmatically, not re-type them manually. This prevents transcription errors and makes the report updatable.

### Relevant Prior Work

| Paper/Result | Authors | Year | Relevance | What to Extract |
| --- | --- | --- | --- | --- |
| Cochrane Handbook Ch. 12 | Cochrane Collaboration | 2023 | Standard methodology for narrative synthesis of heterogeneous results | Structure for integrating mixed evidence without statistical pooling |
| GRADE framework | Guyatt et al. | 2008-present | Framework for rating quality of evidence and strength of recommendations | Adapted verdict-rendering methodology |
| ACM SIGSOFT Empirical Standards | ACM | 2025 | Standards for reporting empirical software engineering results | Honest limitation reporting requirements |
| Guidelines for Empirical Studies with LLMs | arXiv:2508.15503 | 2025 | Reporting standards for LLM-involved experiments | Baseline requirements, limitation documentation |

## Computational Tools

### Core Tools

| Tool | Version/Module | Purpose | Why Standard |
| --- | --- | --- | --- |
| Python 3.11+ | stdlib json, pathlib | Load machine-readable data from prior phases | Same stack as all prior phases |
| Python 3.11+ | stdlib statistics | Compute summary statistics if needed | No external dependencies |

### Supporting Tools

| Tool | Purpose | When to Use |
| --- | --- | --- |
| Existing bootstrap_ci from fault_injector.py | Compute any new CIs if needed | Only if synthesis requires new statistical computations (unlikely) |
| Existing clopper_pearson_ci from fault_injector.py | Boundary CIs | Only if synthesis requires new boundary CIs (unlikely) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
| --- | --- | --- |
| Custom synthesis script | Manual table construction | Manual is error-prone but requires no coding; script is reliable but adds implementation effort |
| JSON output | CSV output | JSON preserves nested structure (CIs, per-type breakdowns); CSV is flatter but more portable |

### Computational Feasibility

| Computation | Estimated Cost | Bottleneck | Mitigation |
| --- | --- | --- | --- |
| Load and aggregate JSON data | < 1 second | None | Data files are < 100KB total |
| Compute side-by-side table | < 1 second | None | All values are simple ratios/counts |
| Write Markdown report | 15-30 min agent time | Report quality, not computation | Clear template structure |

**Installation / Setup:**

No additional packages needed. All tools are already available from prior phases (Python stdlib + existing statistical functions in `fault_injector.py`).

## Validation Strategies

### Internal Consistency Checks

| Check | What It Validates | How to Perform | Expected Result |
| --- | --- | --- | --- |
| Side-by-side table completeness | All observables have values for all four columns | Script asserts no None/missing values in final table | All cells populated (with "N/A" for non-applicable, not blank) |
| Pre-compaction reachability match | Phase 2 baseline = Phase 4 pre-compaction = MockLM ceiling for reachability | Compare three values: all should be 1.0 | Exact match (1.0 = 1.0 = 1.0) |
| Detection rate consistency | Phase 3 aggregate matches sum of per-type rates | 40/90 = sum(D1...D9 detected) / sum(D1...D9 total) | Exact match |
| Forbidden proxy audit consistency | Each proxy status matches the status reported in the phase that addressed it | Cross-reference fp-* status in Phase 3 and Phase 4 summaries | fp-synthetic-only: rejected (Phase 3), fp-short-tasks: unresolved (Phase 4), fp-shallow-traces: rejected (Phase 4) |
| Three-tier ordering invariant | forge >= structured >= uninstrumented for all observables | Verify in side-by-side table | Ordering holds (established in Phase 3 for all 9 types) |

### Known Limits and Benchmarks

| Limit | Parameter Regime | Known Result | Source |
| --- | --- | --- | --- |
| MockLM ceiling (upper bound) | Deterministic, controlled | 100% reachability, 6/6 detection, 87% compression | experiment_results.json |
| Uninstrumented floor (lower bound) | No validation | 0% reachability, 0 detection, N/A compression | Phase 2 baselines |
| Simulated compaction lower bound | Oldest-first deletion | structural_reachability >= real LLM compaction | Phase 4 argument (plausible but not empirically verified) |

### Numerical Validation

| Test | Method | Tolerance | Reference Value |
| --- | --- | --- | --- |
| Aggregate detection rate | 40/90 | Exact | 0.4444... |
| Pre-compaction reachability | Direct comparison | Exact | 1.0 |
| FPR | 0/30 | Exact | 0.0 |

### Red Flags During Computation

- If any value in the side-by-side table does not match the source data file, the transcription/loading has a bug. Stop and debug.
- If the three-tier ordering is violated for any observable, a prior phase result was incorrectly recorded. Trace back to the source.
- If the forbidden proxy audit reveals a proxy that was satisfied (not rejected), the backtracking trigger fires: the relevant measurement phase must be re-run before synthesis can conclude.

## Common Pitfalls

### Pitfall 1: Overclaiming on Injected Faults

**What goes wrong:** Reporting "forge detects 44.4% of violations" without distinguishing that ALL detections are on injected (synthetic) faults and ZERO are on naturally-occurring violations.
**Why it happens:** Aggregate metrics conflate injected and natural detections. The 44.4% rate sounds impressive without the context that it is entirely synthetic.
**How to avoid:** Always report injected and natural detection separately. The synthesis must prominently state: "Mechanism validated on injected faults; practical value on naturally-occurring failures undemonstrated on this sample."
**Warning signs:** The executive summary mentions detection rate without mentioning zero natural violations.
**Recovery:** Add a limitations section that explicitly states the negative finding.

### Pitfall 2: Presenting Simulated Compaction as Genuine

**What goes wrong:** Stating "provenance survives compaction" when only simulated (oldest-first deletion) compaction was tested, not genuine LLM context-window compaction.
**Why it happens:** Phase 4 produced concrete reachability numbers; it is tempting to present them as definitive rather than as lower bounds.
**How to avoid:** Every compaction result must be qualified with "simulated LLM compaction (programmatic deletion)." The synthesis must explicitly state that genuine LLM compaction was not tested and that the simulated results are a lower bound.
**Warning signs:** The word "compaction" appears without a qualifier.
**Recovery:** Global search-and-replace to add qualifiers.

### Pitfall 3: Ignoring the Unresolved Forbidden Proxy

**What goes wrong:** Treating fp-short-tasks as "rejected" when Phase 4 honestly reported it as "unresolved" (no 128K+ token tasks, no genuine compaction events).
**Why it happens:** Desire for a clean forbidden-proxy audit. The other two proxies were cleanly rejected.
**How to avoid:** Report fp-short-tasks status exactly as Phase 4 reported it: "unresolved -- partially addressed by simulated compaction on deep traces (depth=21), but no genuine 128K+ token sessions." Evaluate whether this triggers the backtracking condition.
**Warning signs:** The forbidden proxy audit section shows all three as "rejected" or "avoided."
**Recovery:** Change fp-short-tasks to "unresolved" and document the implication.

### Pitfall 4: Treating the D1-D6 Post-Hoc Gap as a Bug

**What goes wrong:** Framing the 3/6 D1-D6 detection rate (vs MockLM's 6/6) as a deficiency rather than an architectural finding.
**Why it happens:** 3/6 looks worse than 6/6.
**How to avoid:** Explain the gap: MockLM catches faults at registration time (during register_stage()); post-hoc validate_chamber() cannot re-verify hashes (D3), ref correctness beyond existence (D4), or transition legality (D6). This is an architectural difference, not a quality deficiency. The gap is documented and explained.
**Warning signs:** The gap analysis says "detection degraded" without explaining the architectural reason.
**Recovery:** Add the architectural explanation from Phase 3 summaries.

### Pitfall 5: Computing Aggregate Verdicts Without Criteria

**What goes wrong:** Rendering "PARTIAL" or "PASS" on a research question without stating what criteria define each level.
**Why it happens:** Verdict rendering without explicit thresholds is subjective.
**How to avoid:** Define the criteria matrix BEFORE rendering verdicts. See the "RQ Verdict Criteria Matrix" below.
**Warning signs:** A verdict is stated without a justification that references specific measured values and thresholds.
**Recovery:** Add the criteria matrix and re-evaluate each verdict against it.

## RQ Verdict Criteria Matrix

This matrix defines what PASS, PARTIAL, and FAIL mean for each research question. The planner must embed these criteria in the plan so the executor applies them consistently.

### RQ1: Ontology Formalization

| Verdict | Criteria |
| --- | --- |
| PASS | 8 states formalized with complete transition table; Hypothesis verification (10K+ sequences, 0 violations); mutation score >= 85%; open questions resolved with documented rationale |
| PARTIAL | States formalized but some transitions ambiguous; verification passes but with reduced coverage; mutation score < 85% but > 70% |
| FAIL | Transition table incomplete or inconsistent; Hypothesis finds invariant violations; mutation score < 70% |

### RQ2: Violation Detection Reliability

| Verdict | Criteria |
| --- | --- |
| PASS | >= 1 naturally-occurring violation detected; differential detection CI excludes zero; FPR < 5%; three-tier ordering holds |
| PARTIAL | Mechanism validated on injected faults (differential CI excludes zero, FPR < 5%, three-tier ordering holds) BUT zero natural violations detected -- mechanism works, practical value undemonstrated |
| FAIL | Differential detection CI includes zero; OR FPR >= 5%; OR three-tier ordering violated |

### RQ3: Compaction Survival

| Verdict | Criteria |
| --- | --- |
| PASS | Genuine LLM compaction measured; reachability > 0.5 post-compaction; gaps explained; violation detection maintained |
| PARTIAL | Simulated compaction measured (not genuine LLM); reachability characterized with degradation curve; lower bound above backtracking threshold at realistic deletion fractions; violation detection maintained |
| FAIL | Reachability drops below 0.5 with no mitigation path; OR violation detection breaks post-compaction; OR backtracking condition triggered |

## Level of Rigor

**Required for this phase:** Controlled tabulation with honest qualitative assessment

**Justification:** This is a synthesis phase. The rigor requirement is on accurate data aggregation (no transcription errors), honest verdict rendering (no cherry-picking), and complete limitation documentation (no gaps swept under the rug). It is not a derivation phase requiring formal proofs or a numerical phase requiring convergence analysis.

**What this means concretely:**

- Every number in the cross-reference report must trace back to a specific JSON field in a specific data file
- Every verdict must reference the criteria matrix and cite specific measured values
- Every gap must have an explanation (not just "degraded from ceiling")
- Every limitation must be stated in the report body, not hidden in footnotes
- The forbidden proxy audit must use the exact status from the phase that addressed each proxy

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| Single baseline comparison | Three-tier differential comparison (floor, intermediate, treatment) | Project design (Phase 2) | Already implemented; synthesis just reports it |
| Confidence intervals via normal approximation | Clopper-Pearson exact for boundary; Bootstrap for interior | Phase 3 Plan 01 | Already implemented; synthesis uses existing CIs |
| Binary pass/fail verdicts | Three-level PASS/PARTIAL/FAIL with explicit criteria | This phase (new) | Prevents oversimplification of mixed evidence |

**Superseded approaches to avoid:**

- **Unqualified aggregate statistics:** Reporting "44.4% detection rate" without distinguishing injected from natural. Superseded by separated reporting (Phase 3 established this convention).
- **Unqualified "compaction survival":** Claiming compaction was measured when only simulated. Superseded by "simulated LLM compaction" qualification (Phase 4 established this).

## Open Questions

1. **Does fp-short-tasks trigger the backtracking condition?**
   - What we know: Phase 4 reported fp-short-tasks as "unresolved" (no 128K+ token tasks). The synthesis must evaluate whether this is a protocol violation requiring re-run.
   - What is unclear: The ROADMAP backtracking trigger says "if synthesis reveals that forbidden proxies were not actually avoided...the relevant measurement phase must be re-run." But fp-short-tasks was honestly flagged during Phase 4, not hidden. The question is whether an honestly-reported unresolved proxy requires backtracking or can be documented as a known limitation.
   - Impact on this phase: If backtracking is required, Phase 4 cannot be synthesized until re-run with longer tasks. If it can be documented as a limitation, synthesis proceeds with the caveat.
   - Recommendation: Document fp-short-tasks as a known limitation, not a backtracking trigger, because: (a) it was honestly reported during execution (not discovered retrospectively), (b) the simulated compaction provides analytical lower bounds even without genuine compaction events, (c) the ROADMAP backtracking trigger is for proxies that were "not actually avoided" -- fp-short-tasks was partially addressed (deep traces, simulated compaction) and the gap was disclosed. Flag for user decision if needed.

2. **How to handle the RQ2 PARTIAL verdict given 0 natural violations?**
   - What we know: The mechanism works on injected faults (44.4% aggregate, differential CI excludes zero). Zero natural violations on 30 clean runs (CP upper bound 11.6%).
   - What is unclear: Whether the user considers "mechanism validated but practical value undemonstrated" an acceptable outcome or whether it requires further investigation.
   - Impact on this phase: The verdict is clearly PARTIAL by the criteria matrix. The question is how to frame this honestly without either overclaiming or being unduly negative.
   - Recommendation: State PARTIAL clearly. Frame it as: "Forge's typed-absence enforcement detects structural violations when they occur. On this sample, structural violations did not occur naturally. This may indicate that structural violations are rare in coding/patching tasks, or that post-hoc validation misses the types that do occur."

3. **Should the synthesis recommend extending the campaign?**
   - What we know: 30 clean runs is a moderate sample. CP 95% upper bound on natural violation rate is 11.6%. More runs would tighten this bound.
   - What is unclear: Whether the user wants to extend or accept the current results.
   - Impact on this phase: Does not block synthesis but affects the "future work" section.
   - Recommendation: Document in "future work" that 59+ clean runs at 0 violations would reduce the CP upper bound below 5%.

## Alternative Approaches if Primary Fails

| If This Fails | Because Of | Switch To | Cost of Switching |
| --- | --- | --- | --- |
| Synthesis script fails to load data | Corrupted JSON files | Manual report (Approach 2) | Low -- copy numbers from SUMMARY.md files |
| Verdict criteria do not cover a result | Unexpected evidence pattern | Extend criteria matrix with new level | Low -- add criteria and re-evaluate |
| Forbidden proxy audit triggers backtracking | fp-short-tasks requires re-run | Pause synthesis, re-run Phase 4 with longer tasks | High -- requires VM execution and LLM API calls |

**Decision criteria:** If the backtracking trigger fires, the user must decide whether to re-run Phase 4 or accept the limitation. The synthesis should present the decision clearly rather than making it unilaterally.

## Data Inventory for Synthesis

The following files contain all the data the synthesis script needs. The planner should reference these paths explicitly in task descriptions.

### Machine-Readable Data

| File | Content | Key Fields |
| --- | --- | --- |
| `data/campaign/campaign-report.json` | Phase 3 aggregate metrics | `injection_summary.detection_rates.per_type`, `clean_summary`, `anchor_comparison`, `forbidden_proxy_audit` |
| `data/campaign/injection-results.json` | Phase 3 per-injection records | 90 injection records with per-injection detection status |
| `data/campaign/clean-results.json` | Phase 3 clean run results | 30 clean run validation outputs |
| `data/compaction/compaction-report.json` | Phase 4 aggregate metrics | `pre_compaction_baseline`, `deletion_sweep`, `violation_regression`, `anchor_comparison` |
| `data/compaction/simulated-compaction-results.json` | Phase 4 raw campaign data | Per-chamber per-fraction raw measurements |
| `data/baselines/baseline-report.json` | Phase 2 baseline metrics | Three-tier baseline values for all observables |

### Human-Readable Reports

| File | Content | Role in Synthesis |
| --- | --- | --- |
| `docs/violation-report.md` | Phase 3 human-readable report | Reference for gap analysis language |
| `docs/compaction-report.md` | Phase 4 human-readable report | Reference for limitation language |
| `docs/baseline-report.md` | Phase 2 human-readable report | Reference for baseline descriptions |

### Phase Summaries

| File | Key Data |
| --- | --- |
| `GPD/phases/01-ontology-formalization-and-verification/01-01-SUMMARY.md` | Transition table completeness, resolved/not_generated decision |
| `GPD/phases/01-ontology-formalization-and-verification/01-02-SUMMARY.md` | Hypothesis 10K+ sequences, mutation score 99% |
| `GPD/phases/03-violation-detection-campaign/03-02-SUMMARY.md` | Detection rates, FPR, natural violations, anchor comparison |
| `GPD/phases/04-compaction-survival-measurement/04-02-SUMMARY.md` | Reachability curve, backtracking threshold, violation regression |

## Side-by-Side Table Template

The planner should instruct the executor to produce a table with this structure:

| Observable | MockLM Ceiling | Uninstrumented Floor | Structured Logging | Forge Instrumented | Gap (Ceiling - Forge) | Differential (Forge - Floor) |
| --- | --- | --- | --- | --- | --- | --- |
| Violation detection (D1-D6 types) | 6/6 (registration) | 0/6 | 0/6 | 3/6 (post-hoc) | 3 types | +3 types |
| Violation detection (all D1-D9) | N/A | 0/9 | 0/9 | 4/9 | N/A | +4 types |
| Aggregate injection detection rate | N/A | 0.0 | 0.0 | 0.444 [0.344, 0.544] | N/A | +0.444 |
| Natural violation count | N/A | 0 | 0 | 0 (CP UB: 11.6%) | N/A | 0 |
| False positive rate | N/A | N/A | N/A | 0.0 (CP UB: 11.6%) | N/A | N/A |
| Pre-compaction reachability | 1.0 | 0.0 | N/A | 1.0 | 0 | +1.0 |
| Structural reachability @ 50% simulated deletion | N/A | N/A | N/A | 0.821 | N/A | N/A |
| Structural reachability @ 80% simulated deletion | N/A | N/A | N/A | 0.438 | N/A | N/A |
| Backtracking threshold crossed | N/A | N/A | N/A | 80% deletion | N/A | N/A |
| Forge trace compression | 1.096x (87%) | N/A | N/A | 1.196x | -0.1x | N/A |
| Provenance depth | N/A | 0 | N/A | 21 | N/A | +21 |
| Violation regression post-compaction | N/A | N/A | N/A | 4/4 (100%) | N/A | N/A |

Note: "N/A" means the observable is not applicable to that column (e.g., uninstrumented has no compaction measurement). This is a template; the actual script should populate from data files.

## Stop/Rethink Evaluation Framework

The project charter names three falsifiers. The synthesis must evaluate each:

| Falsifier | Evidence For | Evidence Against | Verdict |
| --- | --- | --- | --- |
| (a) Typed absence adds complexity without measurable reliability gains | Mechanism validated: 4/9 types detected, differential +0.444 with CI excluding zero; FPR = 0.0% | Zero natural violations detected; 5/9 types undetectable by post-hoc validation | NOT TRIGGERED -- mechanism demonstrably works, even if practical value on this sample is undemonstrated |
| (b) Provenance chains fail under realistic workloads | Simulated compaction shows degradation (0.932 to 0.250); backtracking threshold crossed at 80% deletion | Pre-compaction reachability = 1.0; simulated results are lower bounds; genuine compaction not tested; linear chain DAGs are inherently resilient | NOT TRIGGERED -- provenance survives simulated compaction up to 70% deletion; genuine test pending |
| (c) Compaction grounding too brittle | Structural reachability drops below 0.5 at 80% deletion | This is simulated deletion (lower bound); genuine LLM compaction expected higher; no genuine compaction data | INCONCLUSIVE -- simulated results suggest the threshold exists but genuine testing is needed |

## Sources

### Primary (HIGH confidence)

- [Cochrane Handbook for Systematic Reviews, Chapter 12: Synthesizing and presenting findings](https://training.cochrane.org/handbook/current/chapter-12) - Standard methodology for narrative synthesis
- [JBI Critical Appraisal Tools](https://jbi.global/critical-appraisal-tools) - Assessment framework adapted for verdict rendering
- [Guidelines for Empirical Studies in Software Engineering involving LLMs, arXiv:2508.15503](https://arxiv.org/abs/2508.15503) - 2025 reporting standards for LLM-involved experiments
- [Benchmarking as Empirical Standard in Software Engineering Research](https://dl.acm.org/doi/10.1145/3463274.3463361) - ACM EASE 2021, ceiling/floor baseline comparison methodology
- All Phase 1-4 summaries and data files (local data, machine-readable)
- MockLM experiment_results.json (local benchmark anchor)

### Secondary (MEDIUM confidence)

- [Research Integrity in Guidelines and Evidence Synthesis (RIGID)](https://www.thelancet.com/journals/eclinm/article/PIIS2589-5370(24)00296-7/fulltext) - eClinicalMedicine 2024, research integrity assessment framework
- [Mixed Methods Research Systematic Methodological Reviews](https://journals.sagepub.com/doi/10.1177/15586898241302592) - SAGE 2025, mixed methods synthesis methodology
- [Retrospective audit to analyze protocol deviations](https://journals.lww.com/picp/fulltext/9900/a_retrospective_audit_to_analyze_protocol.102.aspx) - Adapted methodology for forbidden proxy audit

### Tertiary (LOW confidence)

- GRADE framework general principles (adapted for non-clinical context; the specific clinical recommendations are not directly applicable)

## Metadata

**Confidence breakdown:**

- Mathematical framework: HIGH - All computations are simple aggregation of existing data; no new statistical methods needed
- Standard approaches: HIGH - Narrative synthesis with programmatic table generation is well-established for this type of multi-phase experimental report
- Computational tools: HIGH - Only Python stdlib needed; all statistical functions already exist from prior phases
- Validation strategies: HIGH - All consistency checks are straightforward cross-references against known values

**Research date:** 2026-03-16
**Valid until:** Indefinite (synthesis methodology does not expire; the underlying data may be supplemented by future phases)

## Caveats and Alternatives

### Self-Critique

1. **What assumption am I making that might be wrong?** I assume the fp-short-tasks unresolved status does not trigger backtracking. If the user interprets the ROADMAP strictly, backtracking may be required before synthesis can conclude. The planner should surface this decision point early.

2. **What alternative approach did I dismiss too quickly?** I dismissed formal meta-analytic methods (effect size pooling, forest plots). These would be appropriate if we had multiple independent replications of the same experiment, but we have a single experimental campaign with heterogeneous observables. Narrative synthesis is correct here.

3. **What limitation of my recommended method am I understating?** The verdict criteria matrix is defined in this research document, not pre-registered before the experiment. In a strict experimental methodology, criteria should be pre-registered. However, the project charter's success criteria and falsifiers serve a similar role. The criteria matrix here operationalizes those pre-existing contract terms.

4. **Is there a simpler method I overlooked?** One could skip the synthesis script entirely and write a pure prose report. This would be faster but more error-prone and harder to update. The script adds ~30 minutes of implementation time for a significant reduction in transcription error risk.

5. **Would a specialist disagree with my recommendation?** A meta-analysis specialist might argue that some form of quantitative synthesis is possible (e.g., computing a summary effect size for detection rates across fault types). This would be technically feasible but misleading: the fault types are not independent replications of the same experiment -- they test fundamentally different failure modes (D1 = null collapse vs D3 = hash corruption). Pooling them hides the critical finding that detection is bimodal (100% for 4 types, 0% for 5 types).
