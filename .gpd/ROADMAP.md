# Roadmap: Primordial Computing -- Typed Absence and Provenance in Agentic Systems

## Milestones

- **v1.0 Typed Absence and Provenance Validation** -- Phases 1-5 (completed 2026-03-16)
- **v2.0 The Forgetting Agent** -- Phases 6-8 (started 2026-03-27)

## Phases

### v2.0 The Forgetting Agent (Phases 6-8) -- IN PROGRESS

- [ ] Phase 6: Genuine Compaction Experiments (RQ3b) -- COMP-04, SPF-01
  **Goal:** Test whether forge provenance chains survive genuine LLM context-window compaction via Anthropic's compact_20260112 API. Establish Semantic Provenance Fidelity (SPF) metric. Render honest RQ3b verdict.
  **Plans:** 5 plans
  Plans:
  - [ ] 06-01-PLAN.md -- Build measurement tools (summary parser, embedding similarity)
  - [ ] 06-02-PLAN.md -- Build experiment runner + Track A task templates
  - [ ] 06-03-PLAN.md -- Execute pilot Track A (N=6) + go/no-go analysis
  - [ ] 06-04-PLAN.md -- Build Track C ablation framework + SWE-Bench forge agent
  - [ ] 06-05-PLAN.md -- Statistical analysis pipeline + comprehensive report
- [ ] Phase 7: Adversarial Task Design and Natural Violation Campaign (RQ2b) -- VIOL-04
  **Goal:** Design a task corpus that stresses the failure modes typed absence should catch. Run 200+ instrumented agent sessions across diverse task categories. Either find natural violations or tighten the upper bound to <= 2%.
  **Plans:** 4 plans
  Plans:
  - [ ] 07-01-PLAN.md -- Extend detection pipeline to full D1-D9 coverage + injection sanity check
  - [ ] 07-02-PLAN.md -- Build adversarial task corpus (20 templates, 9 categories) + campaign runner
  - [ ] 07-03-PLAN.md -- Execute 201-run campaign with 7-channel instrumentation + violation extraction
  - [ ] 07-04-PLAN.md -- Statistical analysis (rates, CIs, dose-response, category comparison) + RQ2b verdict
- [ ] Phase 8: Cross-Architecture Generalization (RQ4) -- XARCH-01

**Goal:** Close the three validation gaps from v1.0. Demonstrate real problems on real workloads at real scale.

<details>
<summary>v1.0 Typed Absence and Provenance Validation (Phases 1-5) -- COMPLETED 2026-03-16</summary>

- [x] Phase 1: Ontology Formalization and Verification (2/2 plans) -- completed 2026-03-16
- [x] Phase 2: Integration and Baseline Establishment (4/4 plans) -- completed 2026-03-16
- [x] Phase 3: Violation Detection Campaign (2/2 plans) -- completed 2026-03-16
- [x] Phase 4: Compaction Survival Measurement (2/2 plans) -- completed 2026-03-16
- [x] Phase 5: Cross-Reference and Synthesis (2/2 plans) -- completed 2026-03-16

**Results:** RQ1 PASS, RQ2 PARTIAL (0 natural violations), RQ3 PARTIAL (simulated compaction only)

See `.gpd/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

## Progress

| Milestone | Phases | Plans | Status | Completed |
| --- | --- | --- | --- | --- |
| v1.0 Typed Absence and Provenance Validation | 5 | 12 | Complete | 2026-03-16 |
| v2.0 The Forgetting Agent | 3 | 5 | In Progress | -- |
