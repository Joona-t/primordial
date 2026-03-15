# Requirements: Primordial Computing — Typed Absence and Provenance in Agentic Systems

**Defined:** 2025-03-15
**Core Research Question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?

## Primary Requirements

### Formalization

- [x] **FORM-01**: Formally specify the 8-state absence ontology (not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable) with complete legal/illegal transition table (64 entries: 45 legal, 19 illegal) and companion metadata requirements
- [x] **FORM-02**: Implement property-based testing of state machine invariants using Hypothesis RuleBasedStateMachine — 10K adversarial sequences, 300K transitions, 0 invariant violations; 99% mutation score
- [x] **FORM-03**: Resolve open ontology questions: timed_out/interrupted NOT added (metadata sufficient); recoverability stays binary (Phase 4 concern)

### Integration

- [ ] **INTG-01**: Instrument Zarathustra/OpenClaw with forge tools (forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py) via integration adapter
- [ ] **INTG-02**: Characterize Zarathustra's compaction mechanism — transparency, hook points, whether forge can attach meaningful source_refs

### Baselines

- [ ] **BASE-01**: Establish uninstrumented Zarathustra baseline on real mixed autonomous task set — measure provenance metrics, failure detection, compression
- [ ] **BASE-02**: Establish structured-logging intermediate baseline (OpenTelemetry spans or equivalent) on same task set
- [ ] **BASE-03**: Run forge-instrumented Zarathustra on same task set — the treatment condition

### Violation Detection

- [ ] **VIOL-01**: Measure differential violation detection: forge-instrumented vs uninstrumented vs structured-logging baselines
- [ ] **VIOL-02**: Execute targeted fault injection with domain-specific taxonomy (D1-D9: null collapse, broken provenance, corrupted hashes, fake source refs, etc.)
- [ ] **VIOL-03**: Run campaign on tasks long and complex enough that at least one naturally-occurring silent failure has opportunity to surface

### Compaction Survival

- [ ] **COMP-01**: Run tasks long enough to trigger real context-window compaction (128K+ token tasks)
- [ ] **COMP-02**: Measure structural provenance reachability post-compaction (can refs resolve to source artifacts?)
- [ ] **COMP-03**: Measure trace compression ratio on real tasks — compare against MockLM anchor (87%)

### Cross-Reference

- [ ] **XREF-01**: Compare all real-agent results against MockLM anchor (100% provenance, 6/6 violations, 87% compression)
- [ ] **XREF-02**: Assess each research question (RQ1 ontology, RQ2 reliability, RQ3 compaction) against accumulated evidence
- [ ] **XREF-03**: Document where real-agent results degrade from MockLM ceiling and explain the gaps

## Follow-up Requirements

### Extended Analysis

- **EXTD-01**: TLA+ formal specification of the absence state machine
- **EXTD-02**: Mutation testing of forge core modules with mutmut
- **EXTD-03**: Define and measure semantic reachability (content fidelity behind refs after compaction)
- **EXTD-04**: Port forge protocols to at least one additional runtime (RQ4 generality)
- **EXTD-05**: Paper-style writeup of results

## Out of Scope

| Topic | Reason |
| ----- | ------ |
| General semantic truth in AI | Typed absence addresses structural, not semantic correctness |
| Full epistemology of model outputs | Beyond project scope — requires different methods |
| Third-party runtime generality | RQ4 deferred to future milestone |
| Paper writing | System validation first; paper is future milestone |
| Semantic reachability metric | Needs more definition; structural only for this milestone |

## Accuracy and Validation Criteria

| Requirement | Accuracy Target | Validation Method |
| ----------- | --------------- | ----------------- |
| FORM-01 | Complete transition table with no ambiguous transitions | Hypothesis stateful testing generates 10K+ random sequences without invariant violations |
| FORM-02 | All property tests pass | Hypothesis with min 10K examples per property |
| BASE-01 | Reproducible baseline metrics | Bootstrap CIs on provenance/detection/compression metrics |
| VIOL-01 | Statistically significant differential | Bootstrap 95% CI on detection rate difference between conditions |
| VIOL-02 | All D1-D9 fault types injected | Each fault type injected at least 10 times |
| COMP-01 | Real compaction triggered | Tasks must exceed context window and trigger actual compaction events |
| COMP-02 | Structural reachability measured with exact BFS/DFS | Binary: each ref either resolves or doesn't |
| XREF-01 | Direct numerical comparison | Side-by-side metrics table with MockLM anchor |

## Contract Coverage

| Requirement | Decisive Output / Deliverable | Anchor / Benchmark | Prior Inputs / Baselines | False Progress To Reject |
| ----------- | ----------------------------- | ------------------ | ------------------------ | ------------------------ |
| VIOL-01 | deliv-violation-report | ref-mock-experiment | BASE-01, BASE-02 | Synthetic-only fault detection |
| VIOL-03 | At least 1 natural violation | ref-mock-experiment | BASE-01 | No naturally-occurring detections |
| COMP-02 | deliv-compaction-report | MockLM 100% provenance | BASE-01 | Short tasks that never trigger compaction |
| COMP-03 | Compression ratio measurement | MockLM 87% compression | — | Shallow traces where nothing pruned |

## Traceability

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| FORM-01 | Phase 1 | Complete |
| FORM-02 | Phase 1 | Complete |
| FORM-03 | Phase 1 | Complete |
| INTG-01 | Phase 2 | Pending |
| INTG-02 | Phase 2 | Pending |
| BASE-01 | Phase 2 | Pending |
| BASE-02 | Phase 2 | Pending |
| BASE-03 | Phase 3 | Pending |
| VIOL-01 | Phase 3 | Pending |
| VIOL-02 | Phase 3 | Pending |
| VIOL-03 | Phase 3 | Pending |
| COMP-01 | Phase 4 | Pending |
| COMP-02 | Phase 4 | Pending |
| COMP-03 | Phase 4 | Pending |
| XREF-01 | Phase 5 | Pending |
| XREF-02 | Phase 5 | Pending |
| XREF-03 | Phase 5 | Pending |

**Coverage:**

- Primary requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---

_Requirements defined: 2025-03-15_
_Last updated: 2025-03-15 after roadmap creation (traceability confirmed)_
