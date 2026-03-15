# Roadmap: Primordial Computing -- Typed Absence and Provenance in Agentic Systems

## Overview

This roadmap validates whether typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents. The investigation moves from formalizing the 8-state absence ontology (controlled, no LLM), through instrumenting and baselining the Zarathustra/OpenClaw agent runtime, to measuring violation detection and compaction survival on real tasks, and finally synthesizing results against the MockLM ceiling. The critical path runs through all five phases sequentially; Phase 1 has no external dependencies and Phases 3-4 can partially overlap after Phase 2 completes.

## Contract Overview

| Contract Item | Kind | Advanced By Phase(s) | Status |
| --- | --- | --- | --- |
| claim-violation-detection | claim | Phase 3, Phase 5 | Planned |
| claim-compaction-survival | claim | Phase 4, Phase 5 | Planned |
| deliv-formal-ontology | deliverable | Phase 1 | Planned |
| deliv-baseline | deliverable | Phase 2 | Planned |
| deliv-violation-report | deliverable | Phase 3 | Planned |
| deliv-compaction-report | deliverable | Phase 4 | Planned |
| ref-mock-experiment | anchor | Phase 3, Phase 4, Phase 5 | Planned |
| test-real-violation | acceptance test | Phase 3, Phase 5 | Planned |
| test-compaction-provenance | acceptance test | Phase 4, Phase 5 | Planned |
| fp-synthetic-only | forbidden proxy | Phase 3 | Guard |
| fp-short-tasks | forbidden proxy | Phase 3, Phase 4 | Guard |
| fp-shallow-traces | forbidden proxy | Phase 4 | Guard |

## Phase Dependencies

| Phase | Depends On | Enables | Critical Path? |
| --- | --- | --- | :---: |
| 1 - Ontology Formalization | -- | 2 | Yes |
| 2 - Integration and Baselines | 1 | 3, 4 | Yes |
| 3 - Violation Detection | 2 | 4, 5 | Yes |
| 4 - Compaction Survival | 2, 3 | 5 | Yes |
| 5 - Cross-Reference and Synthesis | 3, 4 | -- | Yes |

**Critical path:** 1 -> 2 -> 3 -> 4 -> 5 (5 sequential phases)
**Partial overlap:** Phase 4 long-running tasks can begin once Phase 2 baselines are established and Phase 3 instrumented runtime is validated, but Phase 4 analysis requires Phase 3 results for differential comparison.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned research work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Ontology Formalization and Verification** - Formally specify and verify the 8-state absence ontology with complete transition rules and property-based tests
- [ ] **Phase 2: Integration and Baseline Establishment** - Instrument Zarathustra with forge tools and establish uninstrumented + structured-logging baselines on real tasks
- [ ] **Phase 3: Violation Detection Campaign** - Measure whether forge detects structural failures missed by uninstrumented and structured-logging baselines on real tasks
- [ ] **Phase 4: Compaction Survival Measurement** - Measure provenance chain survival through real context-window compaction with structural reachability analysis
- [ ] **Phase 5: Cross-Reference and Synthesis** - Integrate results across all phases, compare against MockLM ceiling, and assess all three research questions

## Phase Details

### Phase 1: Ontology Formalization and Verification

**Goal:** The 8-state absence ontology is formally specified with a complete, verified transition table, and the open ontology design questions are resolved with evidence
**Depends on:** Nothing (first phase, no LLM API calls needed)
**Requirements:** FORM-01, FORM-02, FORM-03
**Contract Coverage:**
- Advances: deliv-formal-ontology
- Deliverables: Formalized null ontology with 8 canonical absence states, legal/illegal transition table, validator rules, and example traces
- Anchor coverage: Existing forge_nulls.py validation logic as implementation anchor; 103 passing tests as regression anchor
- Forbidden proxies: None directly assigned; but the ontology must be complete enough that downstream phases can assign states unambiguously to real agent events
**Success Criteria** (what must be TRUE):

1. All 8 absence states (not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable, resolved) have formal definitions with mandatory metadata requirements
2. The complete legal/illegal transition table is specified -- every (source, target) pair is classified as legal, illegal, or conditional, with no ambiguous transitions
3. Hypothesis RuleBasedStateMachine generates 10K+ adversarial transition sequences without invariant violations
4. The open questions (timed_out/interrupted as distinct states; binary vs graded recoverability) are resolved with documented rationale
5. Mutation testing on forge_nulls.py achieves >85% mutation score, confirming test suite quality

**Backtracking trigger:** If Hypothesis discovers a legal transition path that violates an expected invariant, the transition table must be revised before proceeding to Phase 2.

**Plans:** 2 plans

Plans:

- [x] 01-01-PLAN.md -- Formalize ontology: resolve resolved/not_generated discrepancy, build 8x8 transition table with validate_transition(), resolve FORM-03 open questions
- [x] 01-02-PLAN.md -- Verify ontology: Hypothesis RuleBasedStateMachine (10K+ adversarial sequences), parametrized illegal transition tests, mutation testing (99% score)

### Phase 2: Integration and Baseline Establishment

**Goal:** Forge tools are integrated into Zarathustra/OpenClaw, the compaction mechanism is characterized, and uninstrumented + structured-logging baselines are measured on a real task set
**Depends on:** Phase 1 (formalized ontology ensures correct state assignment during instrumentation)
**Requirements:** INTG-01, INTG-02, BASE-01, BASE-02
**Contract Coverage:**
- Advances: deliv-baseline
- Deliverables: Uninstrumented Zarathustra baseline measurements (provenance metrics, failure detection metrics, compression metrics) on real mixed autonomous task set; structured-logging intermediate baseline on same task set; characterization of Zarathustra's compaction mechanism
- Anchor coverage: ref-mock-experiment (103 passing tests must still pass after integration); forge tools (forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py) as carry-forward inputs
- Forbidden proxies: fp-short-tasks applies -- task set must include tasks long enough to trigger real compaction (128K+ tokens)
**Success Criteria** (what must be TRUE):

1. Forge tools (forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py) are integrated into Zarathustra via adapter, and all 103 existing tests still pass
2. Zarathustra's compaction mechanism is characterized: transparent vs opaque, hook points identified, and forge's ability to attach meaningful source_refs is assessed
3. Uninstrumented Zarathustra baseline metrics (provenance, failure detection, compression) are measured on the real task set with reproducible results
4. Structured-logging intermediate baseline (OpenTelemetry spans or equivalent) is measured on the same task set
5. Task set includes at least some tasks long enough to trigger genuine context-window compaction (128K+ tokens of accumulated state)

**Backtracking trigger:** If Zarathustra's compaction is fully opaque (no hook points, no way to attach source_refs), the integration strategy must be redesigned -- possibly recording pre-compaction snapshots or intercepting at the prompt assembly layer. This may require revisiting the compaction survival measurement approach in Phase 4.

**Plans:** TBD

Plans:

- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Violation Detection Campaign

**Goal:** Forge instrumentation detects structural failures on real agent tasks that go undetected by uninstrumented and structured-logging baselines, with at least one naturally-occurring detection
**Depends on:** Phase 2 (baselines and instrumented runtime)
**Requirements:** BASE-03, VIOL-01, VIOL-02, VIOL-03
**Contract Coverage:**
- Advances: claim-violation-detection, deliv-violation-report, test-real-violation
- Deliverables: Violation report documenting naturally-occurring silent failures detected by forge on real Zarathustra tasks, with comparison against uninstrumented baseline; detection rates with bootstrap 95% CIs; false-positive rate on clean runs
- Anchor coverage: ref-mock-experiment (6/6 violations caught under controlled conditions -- compare real detection rate against this ceiling); BASE-01 and BASE-02 as prior baselines for differential comparison
- Forbidden proxies: fp-synthetic-only -- at least one naturally-occurring violation must be detected, not just injected faults; fp-short-tasks -- campaign must include tasks long and complex enough that real failures have opportunity to surface
**Success Criteria** (what must be TRUE):

1. Forge-instrumented Zarathustra runs complete on the same task set as the baselines, producing comparable measurement conditions
2. Differential detection is measured: forge-instrumented vs uninstrumented vs structured-logging, with bootstrap 95% CI on detection rate difference
3. All 9 fault types (D1-D9: null collapse, broken provenance, corrupted hashes, fake source refs, compaction faults, etc.) are injected at least 10 times each to validate the detection mechanism
4. At least 1 naturally-occurring (not injected) silent failure is detected by forge that was missed by the uninstrumented baseline -- this is the primary acceptance criterion per test-real-violation
5. False-positive rate is measured on clean (non-fault-injected) runs

**Backtracking trigger:** If no naturally-occurring violations surface after the full campaign, this is a negative finding that must be honestly reported. Before concluding, verify: (a) tasks were genuinely complex enough, (b) the campaign duration was sufficient, (c) forge's detection logic is not over-conservative. If the issue is task complexity, extend the campaign with longer/harder tasks before accepting a null result.

**Plans:** TBD

Plans:

- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Compaction Survival Measurement

**Goal:** Provenance reachability is measured after real context-window compaction events, gaps relative to the MockLM ceiling are explained, and violation detection remains functional post-compaction
**Depends on:** Phase 2 (compaction mechanism characterized), Phase 3 (instrumented runtime validated and violation detection mechanism confirmed)
**Requirements:** COMP-01, COMP-02, COMP-03
**Contract Coverage:**
- Advances: claim-compaction-survival, deliv-compaction-report, test-compaction-provenance
- Deliverables: Compaction report documenting provenance reachability after real context-window compaction, with MockLM cross-reference; structural reachability measurements via BFS/DFS on provenance DAG; trace compression ratio on real tasks vs MockLM anchor (87%)
- Anchor coverage: ref-mock-experiment (100% provenance reachability under controlled conditions -- measure degradation under real conditions; 87% compression ratio as compression benchmark)
- Forbidden proxies: fp-short-tasks -- tasks must exceed context window and trigger actual compaction events; fp-shallow-traces -- traces must have meaningful depth where pruning actually removes important provenance, not just trivial leaf nodes
**Success Criteria** (what must be TRUE):

1. Tasks trigger genuine context-window compaction (128K+ tokens of accumulated state, with observed compaction events logged)
2. Structural provenance reachability is measured post-compaction via BFS/DFS on the provenance DAG -- each ref either resolves to its source artifact or is classified as broken, with exact reachability fraction reported
3. Trace compression ratio on real tasks is measured and compared against MockLM anchor (87%) -- degradation explained
4. Gaps between real-agent reachability and MockLM ceiling (100%) are enumerated and explained (which refs broke and why)
5. Violation detection (from Phase 3) remains functional after compaction events -- forge still catches violations in post-compaction traces

**Backtracking trigger:** If provenance chains break systematically under real compaction (reachability drops below 50% with no clear mitigation path), this triggers the stop/rethink condition: "Compaction grounding proves too brittle to preserve meaningful return paths." Report as a negative finding on RQ3 and assess whether partial mitigation (e.g., pre-compaction checkpointing) is viable before concluding.

**Plans:** TBD

Plans:

- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Cross-Reference and Synthesis

**Goal:** All measurement results are integrated, compared against the MockLM ceiling, and each research question is assessed with honest evaluation of what worked, what degraded, and what failed
**Depends on:** Phase 3 (violation detection results), Phase 4 (compaction survival results)
**Requirements:** XREF-01, XREF-02, XREF-03
**Contract Coverage:**
- Advances: claim-violation-detection (final assessment), claim-compaction-survival (final assessment), test-real-violation (final verdict), test-compaction-provenance (final verdict)
- Deliverables: Cross-reference report with side-by-side metrics table: MockLM ceiling vs uninstrumented Zarathustra floor vs instrumented Zarathustra treatment; per-RQ assessment (RQ1 ontology, RQ2 reliability, RQ3 compaction)
- Anchor coverage: ref-mock-experiment (100% provenance, 6/6 violations, 87% compression -- final comparison); all prior baselines (deliv-baseline) and measurement reports (deliv-violation-report, deliv-compaction-report)
- Forbidden proxies: All three forbidden proxies (fp-synthetic-only, fp-short-tasks, fp-shallow-traces) are retrospectively audited here -- synthesis must confirm they were avoided, or flag if they were not
**Success Criteria** (what must be TRUE):

1. Side-by-side metrics table comparing MockLM ceiling, uninstrumented Zarathustra, structured-logging baseline, and forge-instrumented Zarathustra is complete with all measured observables (violation detection count, provenance reachability fraction, compression ratio)
2. Each research question (RQ1: ontology formalization, RQ2: violation detection reliability, RQ3: compaction survival) is assessed against accumulated evidence with explicit pass/fail/partial verdict
3. Every gap between real-agent results and MockLM ceiling is documented with explanation (e.g., "reachability dropped from 100% to X% because compaction destroyed N refs of type Y")
4. The three stop/rethink conditions are evaluated: (a) did typed absence add complexity without measurable reliability gains? (b) did provenance chains fail under realistic workloads? (c) was compaction grounding too brittle?

**Backtracking trigger:** If synthesis reveals that forbidden proxies were not actually avoided (e.g., all tasks were short, all violations were synthetic), the relevant measurement phase must be re-run with corrected task design before synthesis can conclude.

**Plans:** TBD

Plans:

- [ ] 05-01: TBD

## Risk Register

| Phase | Top Risk | Probability | Impact | Mitigation |
| --- | --- | :---: | :---: | --- |
| 1 | 8-state ontology insufficient for real agent events | LOW | MEDIUM | Phase 1 resolves timed_out/interrupted question; Phase 2 data informs further expansion |
| 2 | Zarathustra compaction is opaque -- no hook points for forge | MEDIUM | HIGH | Backtrack trigger: redesign integration (pre-compaction snapshots, prompt-layer interception) |
| 3 | Naturally-occurring violations too rare to observe | MEDIUM | MEDIUM | Extend campaign with longer/harder tasks; report null result honestly if violations genuinely absent |
| 4 | Provenance breaks systematically under real compaction | HIGH | HIGH | Stop/rethink trigger per contract; assess partial mitigation before concluding negative |
| 5 | Forbidden proxies were inadvertently satisfied | LOW | HIGH | Retrospective audit in Phase 5; re-run affected measurement phase if needed |

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
| --- | --- | --- | --- |
| 1. Ontology Formalization | 2/2 | Complete | 2026-03-16 |
| 2. Integration and Baselines | 0/TBD | Not started | - |
| 3. Violation Detection | 0/TBD | Not started | - |
| 4. Compaction Survival | 0/TBD | Not started | - |
| 5. Cross-Reference and Synthesis | 0/TBD | Not started | - |
