# Milestones

## v1.0 Typed Absence and Provenance Validation (Shipped: 2026-03-16)

**Phases completed:** 5 phases, 12 plans, 0 tasks

**Key accomplishments:**
- Formalized 8-state absence ontology with complete 64-entry transition table, validate_transition() function, and resolved all FORM-03 design questions
- Adversarial property-based testing (10K+ Hypothesis sequences) and mutation testing (99% adjusted score) confirm transition table correctness and test suite quality
- Resolved Zarathustra as OpenClaw queue worker on separate VM; characterized semi-transparent state management with 4 feasible hook points, shifting adapter strategy from LLM compaction wrapping to JSONL ledger analysis
- Built OpenClaw adapter with 4 interception points (turns, patches, cursor advancement, chamber lifecycle) producing structurally valid chambers; 354 tests pass (301 existing + 53 new) with perfect provenance reachability
- Designed real-task corpus (3 short + 3 long coding tasks from Zarathustra workflows) and built three-tier measurement framework with bootstrap CIs
- Three-tier baseline measurement on real Zarathustra ledger data: uninstrumented floor confirmed, forge reachability 1.0, trace compression 1.18x, 6 cursor state loss events detected
- Built D1-D9 fault injection framework and campaign orchestrator; revealed 5 post-hoc validation gaps (D3/D4/D6/D7/D8) vs MockLM's 6/6 registration-time ceiling
- D1-D9 injection campaign detects 4/9 fault types (44.4%); zero natural violations on 30 clean runs (CP upper bound 11.6%); FPR = 0.0%; three-tier ordering confirmed for all 9 types
- Built compaction measurement harness with three-tier ref classification, BFS reachability, simulated LLM compaction, and violation regression; 49/49 tests pass
- Simulated LLM compaction campaign: structural reachability degrades from 0.93 to 0.25 over 10-90% deletion, backtracking threshold at 80%, violation regression passes, honest limitations documented
- Built programmatic synthesis pipeline: loads Phase 2-4 JSON data, computes 12-row side-by-side table with MockLM ceiling/gap/differential, all 4 consistency checks pass, 39 validation tests green
- Rendered honest RQ verdicts (PASS/PARTIAL/PARTIAL) against pre-stated criteria matrix with 0-natural-violation negative finding prominently surfaced, all gaps explained, fp-short-tasks honestly reported as unresolved, and stop/rethink evaluated (none triggered, compaction inconclusive)

---

## v2.0 The Forgetting Agent (Shipped: 2026-03-28)

**Phases completed:** 3 phases (6-8), 13 plans

**Key accomplishments:**
- Built complete genuine compaction measurement pipeline: summary parser, embedding similarity, experiment runner, Track A/C frameworks, statistical analysis (223 tests). RQ3b: PARTIAL (pipeline-validated, live API required)
- Extended forge detection from 4/9 to 9/9 D-types at 100% (90/90 injected faults), closing CC-009 gap from v1.0
- 211-run adversarial campaign across 20 tasks, 9 categories, 4 stress levels: 0 genuine violations (CP upper 1.73%, Bayesian P(rate>2%)=1.38%). RQ2b: NEGATIVE-STRONG. CC-015 triggered: reframe detection → structural prevention
- AG2 adapter validated (36 tests, reversibility=1.0, 0 null violations, 100% fault detection)
- LangGraph adapter validated (37 tests, reversibility=1.0, checkpointer transparency confirmed)
- 110-session cross-architecture campaign: 0 violations (CP combined upper 3.30%). All 321 sessions: CP upper 1.14%. RQ4: POSITIVE. CC-014 satisfied (3 architecture types)

**Verdicts:** RQ2b NEGATIVE-STRONG | RQ3b PARTIAL | RQ4 POSITIVE (all pipeline-validated, pending live validation)

---

