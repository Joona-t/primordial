# Research Digest: v1.0 Typed Absence and Provenance Validation

Generated: 2026-03-16
Milestone: v1.0
Phases: 1-5

## Narrative Arc

This milestone investigated whether typed absence, explicit provenance, and recoverable compaction can prevent silent state loss in autonomous agents. The investigation began by formalizing the 8-state absence ontology into a complete, verified transition table (Phase 1), then integrated the forge tools into the OpenClaw agent runtime via post-hoc JSONL ledger analysis and established three-tier baselines — uninstrumented, structured-logging, and forge-instrumented — on real agent data (Phase 2). With the measurement infrastructure in place, a systematic fault injection campaign (D1-D9) quantified forge's differential detection capability at 44.4% aggregate with zero false positives, while honestly reporting zero naturally-occurring violations across 30 clean runs (Phase 3). Simulated LLM compaction revealed structural reachability degradation from 0.93 to 0.25 over 10-90% deletion, with the backtracking threshold crossed at 80% deletion (Phase 4). The final synthesis rendered honest RQ verdicts — PASS for ontology formalization, PARTIAL for violation detection (mechanism proven but no natural violations observed), and PARTIAL for compaction survival (structural resilience characterized but on simulated data only) — with all gaps, limitations, and forbidden proxy statuses prominently documented (Phase 5).

## Key Results

| Phase | Result | Value | Validity Range | Confidence |
| ----- | ------ | ----- | -------------- | ---------- |
| 1 | Transition table completeness | 64 entries (45 legal, 19 illegal) | All 8 absence states | Verified: 300K adversarial transitions, 0 violations |
| 1 | Mutation score | 99% adjusted (103/110 killed, 6 equivalent, 1 low-value) | forge_nulls.py | High: custom AST mutation testing |
| 2 | Forge adapter integration | 4 interception points, 53 tests, post-hoc JSONL primary | OpenClaw queue worker | 354 total tests passing |
| 2 | Uninstrumented baseline reachability | 0.0 | Real ledger data | Deterministic (CV=0%) |
| 2 | Forge-instrumented reachability | 1.0 | Real ledger data | Deterministic (CV=0%) |
| 2 | Forge trace compression | 1.18x ratio | Real ledger data | Deterministic |
| 3 | Aggregate detection rate (injected) | 44.4% [CI: 0.344-0.544] | D1-D9, 90+ injections | Bootstrap 95% CI |
| 3 | Natural violation count | 0/30 (CP upper bound 11.6%) | Clean runs on real data | Clopper-Pearson exact |
| 3 | False positive rate | 0.0% (0/30, CP upper bound 11.6%) | Clean runs | Clopper-Pearson exact |
| 3 | D1-D6 post-hoc vs MockLM | 3/6 (50%) vs 6/6 (100%) | Structural faults | Architectural gap identified |
| 4 | Pre-compaction reachability | 1.0 | All chambers | Matches MockLM ceiling |
| 4 | Structural reachability at 50% deletion | 0.821 | Simulated LLM compaction | Lower bound estimate |
| 4 | Backtracking threshold crossing | 80% deletion (reach=0.4375) | Simulated oldest-first | Monotonic degradation confirmed |
| 4 | Violation regression post-compaction | 4/4 (D1/D2/D5/D9 at 100%) | Post-deletion chambers | Deterministic |
| 5 | RQ1 verdict | PASS | Ontology formalization | All acceptance criteria met |
| 5 | RQ2 verdict | PARTIAL | Violation detection | Mechanism proven; zero natural violations blocks PASS |
| 5 | RQ3 verdict | PARTIAL | Compaction survival | Structural resilience characterized; simulated-only blocks PASS |

## Methods Employed

- **Phase 1:** Exhaustive enumeration — built 8x8 transition table from 3 structural rules (initial/terminal/self)
- **Phase 1:** Property-based testing — Hypothesis RuleBasedStateMachine with 10K+ adversarial sequences
- **Phase 1:** Custom AST mutation testing — replaced mutmut (Python 3.14 incompatible); 99% adjusted score
- **Phase 2:** Post-hoc JSONL ledger analysis — non-invasive forge integration across VM boundary
- **Phase 2:** Three-tier baseline comparison — uninstrumented / structured-logging / forge-instrumented
- **Phase 2:** Bootstrap 95% CI — fixed seed (42) for reproducible small-sample statistical reporting
- **Phase 3:** Fault injection campaign — D1-D9 taxonomy, 90+ injections, deepcopy-based post-hoc mutation
- **Phase 3:** Clopper-Pearson exact binomial CI — boundary proportions (0/n, n/n)
- **Phase 4:** Simulated LLM compaction — oldest-first stage deletion at 9 fractions (0.1-0.9)
- **Phase 4:** Three-tier ref classification — resolved/degraded/broken with structural_reachability metric
- **Phase 4:** BFS reachability — stdlib-only provenance DAG traversal
- **Phase 5:** Programmatic synthesis — JSON aggregation across Phase 2-4 data files
- **Phase 5:** Criteria-matrix verdict rendering — pre-stated criteria evaluated against measured evidence

## Convention Evolution

| Phase | Convention | Description | Status |
| ----- | ---------- | ----------- | ------ |
| 1 | Absence State Ontology | 8 states: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable | Active |
| 1 | Absence Object Form | Canonical v1: {value: null, state: \<AbsenceState\>} | Active |
| 1 | State Transition Legality | 8x8 matrix, 64 entries (45 legal, 19 illegal) | Active |
| 1 | Provenance Reference Format | parent_id + source_refs (not W3C PROV) | Active |
| 1 | Artifact ID Format | Colon-separated hierarchical (artifact:..., chamber:...) | Active |
| 1 | Compaction Disambiguation | Forge compaction (lossless) vs LLM compaction (lossy); unqualified FORBIDDEN | Active |
| 1 | Metrics Definitions | reachability_fraction, compression_ratio, vs_vanilla_pct, detection rate, FPR | Active |
| 1 | Violation Classification | Structural only (D1-D9 taxonomy); NOT semantic | Active |
| 1 | Hash Integrity | SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True) | Active |
| 1 | Protocol Versioning | forge.internal.v1 (schemas), forge.trace.v1 (codec) | Active |

Convention changes: CC-001 (resolved→not_generated documentation fix), CC-002 (timed_out/interrupted NOT added), CC-003 (recoverability stays binary). All settled in Phase 1; no convention changes in Phases 2-5.

## Figures and Data Registry

| File | Phase | Description | Paper-ready? |
| ---- | ----- | ----------- | ------------ |
| docs/transition-table.md | 1 | Human-readable 8x8 transition table with design decisions | Yes |
| docs/mutation-results.json | 1 | Mutation testing results (110 mutants, 99% adjusted score) | No (raw data) |
| data/baselines/baseline-report.json | 2 | Three-tier baseline measurements with bootstrap CIs | No (machine-readable) |
| docs/baseline-report.md | 2 | Human-readable baseline comparison report | Yes |
| docs/task-corpus.md | 2 | Real-task corpus specification (6 tasks, 2 tiers) | Yes |
| data/campaign/campaign-report.json | 3 | D1-D9 injection campaign results with per-type detection rates | No (machine-readable) |
| data/campaign/clean-results.json | 3 | Clean campaign results (natural violation search) | No (machine-readable) |
| docs/violation-report.md | 3 | Violation report with anchor comparison and forbidden proxy audit | Yes |
| data/compaction/compaction-report.json | 4 | Simulated compaction campaign results at 9 deletion fractions | No (machine-readable) |
| docs/compaction-report.md | 4 | Compaction report with MockLM anchor comparison | Yes |
| data/synthesis/synthesis-report.json | 5 | 12-row side-by-side metrics table (JSON) | No (machine-readable) |
| data/synthesis/rq-verdicts.json | 5 | Machine-readable RQ verdicts with criteria evaluation | No (machine-readable) |

## Open Questions

1. Does run_queue.py use session-layer LLM compaction during task execution? (HIGH, affects adapter scope)
2. What is the queue file rotation/deletion policy in production? (MEDIUM, affects long-term source_ref resolvability)
3. Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH, extends structural to semantic)

## Dependency Graph

    Phase 1 "Ontology Formalization and Verification"
      provides: transition table, validate_transition(), FORM-03 decisions, mutation testing, Hypothesis verification
      requires: nothing (first phase)
    -> Phase 2 "Integration and Baseline Establishment"
      provides: OpenClaw adapter, three-tier baselines, measurement framework, structured logging baseline
      requires: formalized ontology (Phase 1)
    -> Phase 3 "Violation Detection Campaign"
      provides: D1-D9 detection rates, natural violation count, FPR, differential detection, violation report
      requires: baselines and instrumented runtime (Phase 2)
    -> Phase 4 "Compaction Survival Measurement"
      provides: reachability degradation curve, backtracking threshold, violation regression, compaction report
      requires: compaction characterization (Phase 2), instrumented runtime (Phase 3)
    -> Phase 5 "Cross-Reference and Synthesis"
      provides: side-by-side table, RQ verdicts, gap analysis, forbidden proxy audit, stop/rethink evaluation
      requires: violation results (Phase 3), compaction results (Phase 4)

## Mapping to Original Objectives

| Requirement | Status | Fulfilled by | Key Result |
| ----------- | ------ | ------------ | ---------- |
| FORM-01: Formally specify 8-state ontology | Complete | Phase 1 | 64-entry transition table, validate_transition() |
| FORM-02: Property-based testing (10K+ sequences) | Complete | Phase 1 | 300K transitions, 0 violations; 99% mutation score |
| FORM-03: Resolve ontology design questions | Complete | Phase 1 | timed_out/interrupted NOT added; recoverability binary |
| INTG-01: Instrument Zarathustra with forge | Complete | Phase 2 | OpenClaw adapter with 4 interception points |
| INTG-02: Characterize compaction mechanism | Complete | Phase 2 | Semi-transparent, 4 hook points, post-hoc JSONL strategy |
| BASE-01: Uninstrumented baseline | Complete | Phase 2 | reachability=0.0, deterministic metrics |
| BASE-02: Structured-logging baseline | Complete | Phase 2 | Intermediate tier, zero forge imports |
| BASE-03: Forge-instrumented baseline | Complete | Phase 3 | reachability=1.0, compression=1.18x |
| VIOL-01: Differential detection | Complete | Phase 3 | +0.444 (forge vs uninstrumented), CI excludes zero |
| VIOL-02: D1-D9 fault injection | Complete | Phase 3 | 90+ injections, 4/9 types detected |
| VIOL-03: Natural violation detection | **Partial** | Phase 3 | 0/30 (negative finding, CP upper bound 11.6%) |
| COMP-01: Real compaction (128K+ tokens) | **Partial** | Phase 4 | Simulated only, honestly documented |
| COMP-02: Structural reachability post-compaction | Complete | Phase 4 | 0.932→0.250 over 10-90% deletion |
| COMP-03: Compression ratio vs MockLM | Complete | Phase 4 | 1.18x forge vs 1.10x MockLM (slightly exceeds) |
| XREF-01: Compare all results vs MockLM | Complete | Phase 5 | 12-row side-by-side metrics table |
| XREF-02: Assess each RQ | Complete | Phase 5 | PASS / PARTIAL / PARTIAL |
| XREF-03: Document gaps from MockLM ceiling | Complete | Phase 5 | All gaps enumerated and explained |
