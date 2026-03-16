# Cross-Reference and Synthesis Report

**Project:** Primordial Computing -- Typed Absence and Provenance in Agentic Systems
**Date:** 2026-03-16
**Phase:** 05 Cross-Reference and Synthesis (Plan 02)

---

## 1. Executive Summary

**Research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?

This report synthesizes findings from a five-phase investigation: (1) ontology formalization and property-based verification, (2) integration with a real agent runtime (Zarathustra/OpenClaw) and three-tier baseline establishment, (3) fault injection campaign with violation detection measurement, (4) simulated LLM compaction survival measurement, and (5) programmatic cross-reference synthesis.

**Verdicts:**

- **RQ1 (Ontology Formalization): PASS** -- 8 states formalized with complete transition table, verified by 10K+ adversarial Hypothesis sequences with zero violations and 99% mutation score.
- **RQ2 (Violation Detection Reliability): PARTIAL** -- Mechanism validated on injected faults (4/9 types detected, differential +0.444, FPR = 0.0%). However, **zero naturally-occurring violations were detected** across 30 clean runs (Clopper-Pearson 95% upper bound: 11.6%). Mechanism works; practical value on this sample is undemonstrated.
- **RQ3 (Compaction Survival): PARTIAL** -- Structural resilience characterized via simulated LLM compaction (programmatic deletion). Structural reachability degrades from 0.932 at 10% deletion to 0.250 at 90% deletion. However, **only simulated LLM compaction was tested** -- genuine LLM context-window compaction remains unmeasured.

**Most important limitations:** (1) Zero natural violations detected. (2) Only simulated LLM compaction tested. (3) fp-short-tasks forbidden proxy unresolved (no 128K+ token sessions).

---

## 2. Side-by-Side Metrics Table (XREF-01)

The following table was generated programmatically by `tools/synthesis.py` from Phase 2-4 JSON data files. Every value (except MockLM ceiling anchors) was loaded from source JSON, not manually transcribed. Source traceability for each row is documented in `data/synthesis/side-by-side-table.md`.

| Observable | MockLM Ceiling | Uninstrumented Floor | Structured Logging | Forge Instrumented | Gap (Ceiling - Forge) | Differential (Forge - Floor) |
| --- | --- | --- | --- | --- | --- | --- |
| Violation detection (D1-D6 types) | 6/6 | 0/6 | 0/6 | 3/6 | 3 types | +3 types |
| Violation detection (all D1-D9) | N/A | 0/9 | 0/9 | 4/9 | N/A | +4 types |
| Aggregate injection detection rate | N/A | 0.0 | 0.0 | 0.444 [0.344, 0.544] | N/A | +0.444 |
| Natural violation count | N/A | 0 | 0 | **0** (CP UB: 11.6%) | N/A | 0 |
| False positive rate | N/A | N/A | N/A | 0.0 (CP UB: 11.6%) | N/A | N/A |
| Pre-compaction reachability | 1.0 | 0.0 | N/A | 1.0 | 0.0 | +1.0 |
| Structural reachability @ 50% simulated deletion | N/A | N/A | N/A | 0.821 | N/A | N/A |
| Structural reachability @ 80% simulated deletion | N/A | N/A | N/A | 0.438 | N/A | N/A |
| Backtracking threshold crossed | N/A | N/A | N/A | 80% deletion | N/A | N/A |
| Forge trace compression | 1.096x | N/A | N/A | 1.196x | 0.100x | N/A |
| Provenance depth | N/A | 0 | N/A | 21 | N/A | +21 |
| Violation regression post-simulated-compaction | N/A | N/A | N/A | 4/4 (100%) | N/A | N/A |

### Column Explanations

- **MockLM Ceiling:** Benchmark values from the controlled MockLM experiment (ref-mock-experiment: forge tools with 103 passing tests). Represents the best achievable performance under deterministic, controlled conditions. Source: `tools/experiment_results.json`.
- **Uninstrumented Floor:** Measurements on the same Zarathustra/OpenClaw agent runtime without any forge instrumentation. Represents what happens with no typed-absence or provenance tracking. Source: Phase 2 baselines (`data/baselines/baseline-report.json`).
- **Structured Logging:** Intermediate baseline -- standard structured logging without typed-absence enforcement. Source: Phase 2 baselines.
- **Forge Instrumented:** Real forge-instrumented measurements on OpenClaw ledger data. Source: Phase 3 (`data/campaign/campaign-report.json`) and Phase 4 (`data/compaction/compaction-report.json`).
- **Gap (Ceiling - Forge):** Where MockLM ceiling is applicable, the difference between ceiling and forge-instrumented values. Each gap is explained in Section 4.
- **Differential (Forge - Floor):** The added value of forge instrumentation compared to the uninstrumented baseline.

### Row Notes

- **D1-D6 detection:** MockLM catches all 6 types at registration time (live validation during `register_stage()`). Forge's post-hoc `validate_chamber()` catches 3/6 (D1, D2, D5). The gap of 3 types (D3, D4, D6) is an architectural difference, not a quality deficiency (see Section 4).
- **D1-D9 detection:** D7-D9 were not part of the original MockLM experiment. D9 (seal violation) is detected; D7 (trace data loss) and D8 (content corruption) are not, reflecting fundamental coverage limits of structural validation.
- **Natural violation count:** Zero natural violations on 30 clean runs is a **negative finding**. The Clopper-Pearson 95% upper bound of 11.6% means the true rate could be as high as ~12% or as low as zero. This finding is discussed prominently in Section 3 (RQ2).
- **Structural reachability rows:** These measure provenance survival under simulated LLM compaction (oldest-first programmatic deletion). "Simulated" means no genuine LLM context-window compaction was tested.
- **Forge trace compression:** MockLM compression (1.096x) was measured on controlled test data. Real forge compression on OpenClaw ledger (1.196x) uses different data structures with higher repetition. The gap (0.100x) reflects data composition differences.
- **Violation regression post-simulated-compaction:** D1/D2/D5/D9 remain detected at 100% after simulated LLM compaction, confirming detection is independent of compaction state.

### Consistency Checks (automated)

All four automated consistency checks pass:

1. **Three-tier ordering:** forge >= structured >= uninstrumented for detection rates (all 9 types), reachability, and provenance depth. PASS.
2. **Pre-compaction reachability match:** Phase 2 baseline (1.0) = Phase 4 pre-compaction (1.0) = MockLM ceiling (1.0). PASS.
3. **Detection rate sum:** sum(per_type detected) = 40 = aggregate detected. PASS.
4. **Detection rate arithmetic:** 40/90 = 0.4444 matches aggregate rate. PASS.

---

## 3. Per-RQ Assessment (XREF-02)

### RQ1: Can absence be formalized as a useful computational ontology?

**Verdict: PASS** [CONFIDENCE: HIGH]

#### Criteria (from RESEARCH.md verdict matrix)

| Criterion | Required for PASS | Met? | Evidence |
| --- | --- | --- | --- |
| 8 states formalized with complete transition table | Yes | Yes | 45 legal, 19 illegal, 64 total entries (Phase 1 Plan 01) |
| Hypothesis verification 10K+ sequences, 0 violations | Yes | Yes | 10K examples x 30 steps = ~300K transitions, 0 invariant violations (Phase 1 Plan 02) |
| Mutation score >= 85% | Yes | Yes | 99.0% adjusted (103/104 non-equivalent killed) (Phase 1 Plan 02) |
| Open questions resolved | Yes | Yes | CC-001 (resolved is REF state), CC-002 (timed_out/interrupted metadata), CC-003 (binary recoverability) (Phase 1 Plan 01) |

**MockLM anchor comparison:** The ontology formalized in Phase 1 is the foundation of the MockLM experiment's 6/6 violation detection (ref-mock-experiment, 100% provenance). The transition table and validate_transition() function verified here are the same components used in the MockLM benchmark.

**Limitations:** None material for RQ1. The formalization is complete and extensively verified. The one caveat is that the 8 states may need expansion if future phases discover agent lifecycle scenarios not representable by the current ontology plus metadata enrichment.

---

### RQ2: Do typed absence and provenance-preserving protocols detect structural failures missed by ordinary logging?

**Verdict: PARTIAL** [CONFIDENCE: HIGH]

#### Criteria (from RESEARCH.md verdict matrix)

| Criterion | Required for PASS | Met? | Evidence |
| --- | --- | --- | --- |
| >= 1 naturally-occurring violation detected | Yes (blocks PASS) | **No** | 0/30 clean runs (CP 95% upper bound: 11.6%) |
| Differential detection CI excludes zero | Yes | Yes | +0.444 [0.344, 0.544] (Phase 3 Plan 02) |
| FPR < 5% | Yes | Yes | 0.0% [0.000, 0.116] (Phase 3 Plan 02) |
| Three-tier ordering holds | Yes | Yes | Holds for all 9 fault types (Phase 3 Plan 02) |

#### The Positive Finding: Mechanism Validated

Forge's typed-absence enforcement detects structural violations when they occur. On injected faults:

- **4 of 9 fault types detected at 100%:** D1 (null collapse), D2 (provenance omission), D5 (metadata absence), D9 (seal violation).
- **Aggregate detection rate:** 40/90 = 44.4% [95% CI: 0.344, 0.544].
- **Differential detection:** +0.444 versus uninstrumented and structured logging baselines, with CI excluding zero.
- **False positive rate:** 0.0% (0/30 clean runs, CP upper bound 11.6%).
- **Three-tier ordering confirmed:** forge >= structured >= uninstrumented for all 9 fault types.

**MockLM anchor comparison:** MockLM ceiling detects 6/6 D1-D6 types at registration time (ref-mock-experiment). Real forge post-hoc validation detects 3/6 D1-D6 types. The gap of 3 types (D3 hash, D4 ref correctness, D6 transition legality) is architectural, not qualitative (see Section 4, per CC-009).

#### The Negative Finding: Zero Natural Violations

**This finding must be stated with equal prominence as the positive finding.**

Across 30 clean runs on real Zarathustra/OpenClaw ledger data, forge detected zero naturally-occurring structural violations. The Clopper-Pearson 95% upper bound on the natural violation rate is 11.6%. This means:

- The true natural violation rate could be anywhere from 0% to ~12% on this sample.
- The detection mechanism is validated on injected faults but its **practical value on naturally-occurring failures is undemonstrated on this sample**.
- This may indicate that: (a) structural violations are genuinely rare in coding/patching tasks, (b) post-hoc validation misses the types of violations that do occur naturally, or (c) the sample size of 30 runs is insufficient to observe rare events.

The 44.4% aggregate detection rate is **entirely on injected (synthetic) faults**. Zero of those detections are on naturally-occurring violations.

#### 5/9 Fault Types Undetectable Post-Hoc

5 of 9 fault types are not detected by post-hoc `validate_chamber()`:

- **D3 (hash tampering):** Post-hoc cannot re-verify hashes without the original data.
- **D4 (ref correctness):** Post-hoc checks ref existence but not content correctness.
- **D6 (illegal transition):** Post-hoc does not replay state transition sequences.
- **D7 (trace data loss):** Remaining refs form a valid DAG even after data removal. Fundamentally undetectable by structural validation alone (per CC-010).
- **D8 (content corruption):** Requires content integrity checks not present in structural validation.

**Verdict justification:** PARTIAL because: (1) the mechanism works -- differential detection on injected faults is statistically significant, (2) FPR is clean, (3) three-tier ordering holds. But PASS is blocked because zero naturally-occurring violations were detected and 5/9 types are architecturally undetectable post-hoc.

---

### RQ3: Can history be compacted while preserving grounded return paths?

**Verdict: PARTIAL** [CONFIDENCE: MEDIUM]

#### Criteria (from RESEARCH.md verdict matrix)

| Criterion | Required for PASS | Met? | Evidence |
| --- | --- | --- | --- |
| Genuine LLM compaction measured | Yes (blocks PASS) | **No** | Only simulated LLM compaction (programmatic deletion) tested |
| Simulated compaction measured | Yes | Yes | 9 deletion fractions, 3 chambers (Phase 4 Plan 02) |
| Reachability characterized | Yes | Yes | 0.932 (10%) to 0.250 (90%), monotonic degradation |
| Lower bound above backtracking threshold at realistic fractions | Yes | Yes | At 70% deletion: structural reachability = 0.550 > 0.5 threshold |
| Violation detection maintained | Yes | Yes | D1/D2/D5/D9 at 100% post-simulated-compaction |

#### Simulated LLM Compaction Results

**All compaction results in this section are from simulated LLM compaction (programmatic oldest-first deletion), NOT genuine LLM context-window compaction.**

The simulated LLM compaction campaign measured structural reachability (resolved_refs / total_refs) across 9 deletion fractions on 3 Phase 2 chambers:

| Deletion Fraction | Structural Reachability | Above Threshold (0.5) |
| --- | --- | --- |
| 10% | 0.932 | Yes |
| 20% | 0.925 | Yes |
| 30% | 0.917 | Yes |
| 40% | 0.875 | Yes |
| 50% | 0.821 | Yes |
| 60% | 0.750 | Yes |
| 70% | 0.550 | Yes |
| 80% | 0.438 | **No** |
| 90% | 0.250 | **No** |

Key findings:

- **Pre-simulated-compaction reachability:** 1.0, exactly matching MockLM ceiling (ref-mock-experiment, reachability = 1.0) and Phase 2 baseline.
- **Monotonic degradation:** Structural reachability decreases monotonically with deletion fraction.
- **Backtracking threshold:** Crossed at 80% deletion (structural reachability = 0.438 < 0.5). At 70% deletion, structural reachability remains above threshold (0.550).
- **BFS reachability:** Stays at 1.0 at all deletion fractions. Expected for linear-chain DAGs: remaining sub-chain is self-contained. Structural reachability (from `classify_refs`) is the sensitive metric (per CC-013).
- **Violation regression:** D1/D2/D5/D9 all detected at 100% on non-compacted chambers, confirming detection independence from the simulated compaction state.

**MockLM anchor comparison:** Pre-simulated-compaction reachability matches MockLM ceiling exactly (gap = 0). Post-simulated-compaction gaps increase monotonically with deletion fraction.

**Simulated vs. genuine compaction argument:** Simulated LLM compaction (oldest-first deletion) provides a **lower bound** on genuine reachability. The argument is that intelligent LLM summarization would preserve more provenance-critical content than random deletion. This is plausible but **not empirically verified** -- genuine LLM compaction was not tested.

#### Limitations

1. **Only simulated LLM compaction tested.** Genuine LLM context-window compaction requires VM execution with real context pressure. Simulated results are analytical predictions, not empirical measurements of genuine compaction behavior.
2. **fp-short-tasks unresolved.** No 128K+ token sessions were tested. Simulated LLM compaction on deep traces (depth=21) partially addresses this, but does not substitute for genuine long-session pressure.
3. **3 chambers from same ledger.** All 3 chambers produce identical structural reachability values per deletion fraction (built from the same ledger data). CIs reflect measurement precision, not trace diversity.
4. **Degraded ref category empty.** Simulated LLM compaction is binary (delete or keep). The "degraded" tier (content partially present but semantically degraded) cannot be populated without genuine LLM compaction.

**Verdict justification:** PARTIAL because: (1) structural resilience is characterized with a complete degradation curve, (2) lower bound arguments suggest real performance would be higher, (3) backtracking threshold only crossed at 80% deletion, (4) violation detection maintained. But PASS is blocked because genuine LLM compaction was not measured and fp-short-tasks remains unresolved.

---

## 4. Gap Analysis (XREF-03)

For each non-zero, non-N/A gap between the MockLM ceiling and forge-instrumented values in the side-by-side table:

### Gap 1: Violation Detection (D1-D6 Types) -- 6/6 vs 3/6

- **Gap:** 3 types undetected (D3, D4, D6)
- **Classification:** Architectural
- **Explanation:** MockLM catches D1-D6 at registration time during `register_stage()`, which performs live validation including hash verification (D3), ref correctness checks beyond existence (D4), and state transition legality enforcement (D6). Post-hoc `validate_chamber()` runs after the chamber is sealed and cannot re-verify hashes (D3), cannot check ref content correctness beyond whether the ref exists (D4), and does not replay the transition sequence to verify legality (D6). This is a real architectural difference between registration-time and post-hoc validation, not a quality deficiency in forge's implementation (per CC-009).
- **MockLM anchor value:** 6/6 (100%) at registration time (ref-mock-experiment)
- **Forge measured value:** 3/6 (50%) at post-hoc validation time

### Gap 2: Pre-Compaction Reachability -- 1.0 vs 1.0

- **Gap:** 0.0 (zero gap)
- **Classification:** Zero
- **Explanation:** Pre-simulated-compaction reachability matches MockLM ceiling exactly. The forge DAG structure achieves full provenance reachability before any simulated compaction, exactly as designed. Three-way match confirmed: Phase 2 baseline = Phase 4 pre-compaction = MockLM ceiling = 1.0.
- **MockLM anchor value:** 1.0 (ref-mock-experiment)
- **Forge measured value:** 1.0

### Gap 3: Forge Trace Compression -- 1.096x vs 1.196x

- **Gap:** 0.100x (forge achieves better compression on real data)
- **Classification:** Data composition difference
- **Explanation:** MockLM compression was measured on controlled test data with a specific data structure (1.096x encoded/original). Real forge compression on OpenClaw ledger data (1.196x) uses different data structures with higher repetition, yielding better compression. The forge trace compression algorithm is identical in both cases -- the gap reflects the input data, not the algorithm. Note: the gap direction means forge performs *better* on real data than on MockLM test data, which is favorable.
- **MockLM anchor value:** 1.096x (87% compression, ref-mock-experiment)
- **Forge measured value:** 1.196x

### Gap 4: Natural Violations -- 0

- **Gap:** N/A for MockLM comparison (MockLM did not test natural violations)
- **Classification:** Sample size and/or detection coverage limitation
- **Explanation:** 30 clean runs produced zero natural violations. The Clopper-Pearson 95% upper bound is 11.6%. The absence could be due to: (a) structural violations are rare in coding/patching workflows, (b) post-hoc validation misses the types that occur naturally (5/9 types undetectable), (c) 30 runs is too few to observe rare events. This is a negative finding, not a gap to "close" -- it is information about the system under test.

---

## 5. Forbidden Proxy Retrospective Audit

### fp-synthetic-only: AVOIDED (Phase 3)

- **Proxy definition:** Violation detection claim based entirely on injected fault detections with no acknowledgment that zero naturally-occurring violations were found.
- **Phase that addressed it:** Phase 3 (Violation Detection Campaign, Plan 02)
- **Status from Phase 3 SUMMARY contract_results:** `fp-synthetic-only: rejected` (avoided)
- **Evidence:** Natural violations were assessed independently in a separate clean campaign (30 runs). Zero natural violations were honestly reported as a **negative finding** with Clopper-Pearson upper bound. Injected and natural detections are strictly separated via `separate_injected_natural()`. The violation report (docs/violation-report.md) dedicates a full section to the natural violation assessment. The report does NOT conflate injected and natural detection rates.
- **Assessment:** AVOIDED. The proxy was not satisfied. Both positive (injected detection) and negative (zero natural) findings are prominently reported.

### fp-short-tasks: UNRESOLVED (Phase 4)

- **Proxy definition:** Compaction survival claim based on short tasks that never trigger genuine context-window compaction.
- **Phase that addressed it:** Phase 4 (Compaction Survival Measurement, Plan 02)
- **Status from Phase 4 SUMMARY contract_results:** `fp-short-tasks: unresolved` (partially addressed)
- **Evidence:** Simulated LLM compaction was tested on traces with depth=21 and 40 stages, which are structurally meaningful. Simulated LLM compaction at 70% deletion removes 28 stages. However, no genuine 128K+ token sessions were tested, and no genuine LLM context-window compaction events were measured. Phase 4 honestly reported this as "partially addressed" rather than claiming it was rejected or avoided.
- **Assessment:** UNRESOLVED. This proxy was partially addressed by simulated LLM compaction on deep traces, but not fully resolved because no genuine long-session compaction was tested. This is an honest limitation, not a protocol violation.

**Does fp-short-tasks trigger the ROADMAP backtracking condition?**

The ROADMAP states: "if synthesis reveals that forbidden proxies were not actually avoided...the relevant measurement phase must be re-run." However, fp-short-tasks was not hidden or discovered retrospectively -- it was honestly flagged during Phase 4 execution (CC-013), documented as "unresolved" in the Phase 4 SUMMARY, and the gap was disclosed with specific evidence. The simulated LLM compaction provides analytical lower bounds even without genuine compaction events.

**Recommendation:** Document fp-short-tasks as a known limitation for Milestone 2, not a backtracking trigger, because: (a) it was honestly reported during execution, (b) simulated LLM compaction provides analytical lower bounds, (c) the ROADMAP backtracking trigger is for proxies that were "not actually avoided" while being reported as avoided -- fp-short-tasks was reported as unresolved from the start. This is a researcher decision.

### fp-shallow-traces: AVOIDED (Phase 4)

- **Proxy definition:** Compaction survival claim based on shallow traces where nothing interesting gets pruned.
- **Phase that addressed it:** Phase 4 (Compaction Survival Measurement, Plan 02)
- **Status from Phase 4 SUMMARY contract_results:** `fp-shallow-traces: rejected` (avoided)
- **Evidence:** Phase 2 traces have depth=21 and 40 stages. Simulated LLM compaction at 70% deletion removes 28 of 40 stages -- structurally meaningful deletion. Even at 10% deletion, 4 stages are removed. The traces are deep enough that simulated compaction exercises meaningful provenance chain breakage.
- **Assessment:** AVOIDED. The proxy was not satisfied. Traces are deep and structurally meaningful.

---

## 6. Stop/Rethink Evaluation

The project charter names three falsifiers. Each is evaluated below against accumulated evidence.

### Falsifier (a): Typed absence adds complexity without measurable reliability gains

| Aspect | Evidence |
| --- | --- |
| Evidence FOR mechanism value | 4/9 fault types detected at 100% on injected faults. Differential detection +0.444, CI [0.344, 0.544] excludes zero. FPR = 0.0% (0/30, CP UB 11.6%). Three-tier ordering holds for all 9 types. Ontology formalization verified by 10K+ adversarial sequences with zero violations and 99% mutation score. |
| Evidence AGAINST mechanism value | Zero natural violations detected on 30 clean runs (CP UB 11.6%). 5/9 fault types undetectable by post-hoc validation. Task corpus limited to coding/patching workflows. |

**Verdict: NOT TRIGGERED**

The mechanism demonstrably works on injected faults: it detects structural violations with statistically significant differential and zero false positives. The complexity of typed absence (8 states, 64-entry transition table) has measurable reliability gains -- 4/9 fault types are caught that would be missed entirely without it. The absence of natural violations does not negate the mechanism; it indicates either that violations are rare in this task domain or that longer campaigns are needed.

### Falsifier (b): Provenance chains fail under realistic workloads

| Aspect | Evidence |
| --- | --- |
| Evidence FOR provenance survival | Pre-simulated-compaction reachability = 1.0 (matches MockLM ceiling). Structural reachability stays above backtracking threshold (0.5) through 70% simulated deletion. Forge trace compression achieves 1.196x (better than MockLM on real data). Violation detection maintained post-simulated-compaction. |
| Evidence AGAINST provenance survival | Only simulated LLM compaction tested (not genuine). At 80% simulated deletion, reachability drops below threshold (0.438). fp-short-tasks unresolved (no 128K+ sessions). |

**Verdict: NOT TRIGGERED** (but based on simulated evidence only)

Under simulated LLM compaction, provenance chains survive with meaningful structural reachability up to 70% deletion. Pre-simulated-compaction provenance is perfect (reachability = 1.0). The simulated results are lower bounds -- genuine LLM compaction is expected to preserve more content than random deletion. However, this verdict rests on simulated evidence; genuine testing under real context pressure is needed for definitive confirmation.

### Falsifier (c): Compaction grounding too brittle for meaningful return paths

| Aspect | Evidence |
| --- | --- |
| Evidence FOR brittleness | Structural reachability drops below the 0.5 backtracking threshold at 80% simulated deletion (0.438). At 90% deletion, only 0.250 structural reachability remains. |
| Evidence AGAINST brittleness | Simulated deletion is a lower bound; genuine LLM compaction may preserve more provenance-critical content via intelligent summarization. Linear-chain DAGs are inherently resilient (BFS reachability stays 1.0 at all deletion fractions). Backtracking threshold is only crossed at extreme deletion (80%+). At moderate simulated compaction (50%), structural reachability is still 0.821. |

**Verdict: INCONCLUSIVE**

The evidence shows that a threshold exists -- at some level of context loss, provenance chains become too degraded for meaningful return paths. Under simulated LLM compaction, this threshold is at 80% deletion. Under genuine LLM compaction, the threshold may be higher (better) because intelligent summarization preserves more than deletion. But without genuine testing, we cannot determine where the real threshold lies. The verdict is INCONCLUSIVE rather than TRIGGERED because: (1) the simulated threshold (80%) is high, suggesting meaningful resilience, (2) the lower-bound argument is plausible, and (3) no genuine compaction data contradicts the argument.

---

## 7. Limitations

The following limitations must be considered when interpreting the results of this investigation. They are listed in order of impact on the research conclusions.

1. **Zero naturally-occurring violations detected.** Across 30 clean runs on real Zarathustra/OpenClaw ledger data, forge detected zero structural violations. The Clopper-Pearson 95% upper bound is 11.6%. This means the violation detection mechanism's practical value on naturally-occurring failures remains undemonstrated on this sample. The 44.4% aggregate detection rate is entirely on injected (synthetic) faults.

2. **Only simulated LLM compaction tested.** Phase 4 used programmatic oldest-first deletion to simulate LLM context-window compaction. Genuine LLM compaction (where an LLM summarizes and prunes context) was not tested. The simulated results are analytical lower bounds, not empirical measurements of real compaction behavior.

3. **fp-short-tasks unresolved.** No 128K+ token sessions were tested. The simulated LLM compaction on deep traces (depth=21) partially addresses this, but does not substitute for genuine long-session context pressure.

4. **5/9 fault types undetectable by post-hoc validation.** D3 (hash tampering), D4 (ref correctness), D6 (illegal transition), D7 (trace data loss), and D8 (content corruption) are not caught by `validate_chamber()`. D7 may be fundamentally undetectable by structural validation alone (remaining refs form a valid DAG). D3, D4, and D6 could potentially be caught by extending `validate_chamber()`.

5. **Small sample from a single source.** 30 clean runs and 3 chambers, all derived from the same OpenClaw ledger sample. The narrow CIs on deterministic measurements reflect measurement precision, not trace diversity. Different ledger samples or task types might yield different results.

6. **Task corpus limited to coding/patching workflows.** All traces come from Zarathustra/OpenClaw performing code-related tasks (patch propose/validate/apply). Structural violation rates may differ in other task domains (web browsing, data analysis, multi-agent coordination).

---

## 8. Future Work

1. **Extended clean campaign.** Run 59+ clean runs at 0 violations to reduce the Clopper-Pearson 95% upper bound below 5%. This would tighten the constraint on the natural violation rate and either confirm rarity or eventually surface a naturally-occurring violation.

2. **Genuine LLM compaction testing.** Execute forge-instrumented tasks on a VM with real context-window pressure (128K+ tokens, Claude's `compact_20260112` model). Measure genuine structural reachability and populate the "degraded" ref tier.

3. **Close D3/D4/D6 post-hoc gap.** Extend `validate_chamber()` to add: hash re-verification for D3, ref content correctness checks for D4, state transition legality replay for D6. This could bring D1-D6 post-hoc detection from 3/6 to 6/6, matching the MockLM ceiling.

4. **Diverse trace sources.** Test with different ledger data, different task types (beyond coding/patching), and different agent runtimes to assess generalizability.

5. **Milestone 2 scoping.** Based on these results: (a) genuine compaction testing is the highest priority, (b) extended clean campaign is the second priority, (c) D3/D4/D6 gap closure is the third priority. Milestone 2 should be scoped to address these in order.

---

## 9. Contract Completion Status

### Milestone 1 Claims

| Claim | Status | Evidence |
| --- | --- | --- |
| claim-violation-detection | **PARTIAL** | Mechanism validated on injected faults (4/9 types, differential +0.444, FPR = 0.0%). Natural violations negative (0/30, CP UB 11.6%). |
| claim-compaction-survival | **PARTIAL** | Simulated LLM compaction measured (9 fractions, 3 chambers). Structural reachability characterized. Genuine LLM compaction pending. |

### Acceptance Tests

| Test | Status | Evidence |
| --- | --- | --- |
| test-real-violation | **FAILED** (negative finding) | 0 natural violations on 30 clean runs. Honestly reported with CP bound. |
| test-compaction-provenance | **PASSED** | Simulated LLM compaction measured with degradation curve, gaps explained, violation regression confirmed. |
| test-differential-detection | **PASSED** | +0.444, CI [0.344, 0.544] excludes zero. |
| test-fpr-acceptable | **PASSED** | 0.0% [0.000, 0.116], below 5% threshold. |

### Deliverables

| Deliverable | Status | Path |
| --- | --- | --- |
| Formalized null ontology | Produced | tools/forge_nulls.py (TRANSITION_TABLE, validate_transition) |
| Violation report with baseline comparison | Produced | docs/violation-report.md, data/campaign/campaign-report.json |
| Compaction report with MockLM cross-reference | Produced | docs/compaction-report.md, data/compaction/compaction-report.json |
| Cross-reference synthesis report | Produced | docs/cross-reference-report.md (this document) |
| Machine-readable verdicts | Produced | data/synthesis/rq-verdicts.json |

### Forbidden Proxy Audit Summary

| Proxy | Status | Phase |
| --- | --- | --- |
| fp-synthetic-only | AVOIDED | Phase 3 |
| fp-short-tasks | **UNRESOLVED** | Phase 4 |
| fp-shallow-traces | AVOIDED | Phase 4 |

### Stop/Rethink Summary

| Falsifier | Verdict |
| --- | --- |
| Complexity without gains | NOT TRIGGERED |
| Provenance fails under load | NOT TRIGGERED (simulated only) |
| Compaction too brittle | INCONCLUSIVE |

---

_Generated: 2026-03-16_
_Phase: 05-cross-reference-and-synthesis, Plan: 02_
_Source data: data/synthesis/synthesis-report.json, data/campaign/campaign-report.json, data/compaction/compaction-report.json, data/baselines/baseline-report.json_
