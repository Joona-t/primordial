# Research Digest: v2.0 The Forgetting Agent

Generated: 2026-03-28
Milestone: v2.0
Phases: 6-8

## Narrative Arc

v1.0 established that typed absence and provenance are formally sound (RQ1 PASS) but left three critical validation gaps: zero natural violations observed (RQ2 PARTIAL), compaction measured only via simulated deletion (RQ3 PARTIAL), and all testing confined to a single runtime (OpenClaw). v2.0 set out to close these gaps. Phase 6 built the complete measurement infrastructure for genuine LLM compaction — summary parser, embedding similarity module, experiment runner with compact_20260112 API integration, Track A pilot framework, Track C ablation with Bonferroni-corrected comparisons, and SWE-Bench forge agent scaffold — validating the full pipeline on dry-run data but unable to execute live due to missing API key. Phase 7 extended the forge detection pipeline from 4/9 to 9/9 D-types at 100% detection, designed a 20-template adversarial corpus across 9 categories, and executed a 211-run campaign that produced zero genuine violations (CP upper 1.73%), triggering CC-015: the negative finding IS the finding, reframing forge from detection to structural prevention. Phase 8 demonstrated cross-architecture transfer by building AG2 (message-passing) and LangGraph (graph-based) adapters, each validated with 30+ integration tests, then running a 110-session campaign with zero violations across both frameworks. The combined 321-session corpus yields a CP upper bound of 1.14%, satisfying CC-014 (multi-architecture requirement) and establishing RQ4: POSITIVE. All v2.0 verdicts are pipeline-validated on mock backends; live validation remains the key open task.

## Key Results

| Phase | Result | Value | Validity Range | Confidence |
|-------|--------|-------|----------------|------------|
| 6 | Compaction measurement pipeline | 5 tools, 223 tests, dry-run validated | Mock/dry-run only | Pipeline-validated |
| 6 | RQ3b verdict | PARTIAL (pipeline ready, live untested) | Dry-run data only | Low (no live data) |
| 7 | Extended D-type detection | 9/9 D-types at 100% (90/90 injections) | Injected faults, mock backend | High (statistical) |
| 7 | Adversarial campaign violations | 0/211 (CP upper 1.73%) | 20 tasks, 9 categories, 4 stress levels | High (CP bound) |
| 7 | RQ2b verdict | NEGATIVE-STRONG | Mock backend, pipeline-validated | Pipeline-validated |
| 7 | Bayesian violation rate | P(rate>2%) = 1.38% | Jeffreys prior | High |
| 8 | AG2 adapter metrics | reversibility=1.0, 0 violations, 36 tests | Mock AG2 framework | Pipeline-validated |
| 8 | LangGraph adapter metrics | reversibility=1.0, 0 violations, 37 tests | Mock LangGraph framework | Pipeline-validated |
| 8 | Cross-architecture campaign | 0/110 violations (CP upper 3.30%) | 55 AG2 + 55 LangGraph | Pipeline-validated |
| 8 | Combined corpus | 0/321 (CP upper 1.14%) | All architectures combined | Pipeline-validated |
| 8 | RQ4 verdict | POSITIVE | 3 architecture types | Pipeline-validated |

## Methods Employed

- **Phase 6:** Regex-based provenance extraction, three-tier ref classification (resolved/degraded/broken), combined Jaccard+weighted token overlap fallback for embedding similarity, compact_20260112 API integration with pause_after_compaction, dry-run pipeline validation, cost estimation, 9-condition ablation matrix with bootstrap permutation test and Bonferroni correction, 5-phase SWE-Bench forge agent loop
- **Phase 7:** Extended structural validator (D1-D9 canonical taxonomy), ReliabilityBench epsilon/lambda stress calibration, adversarial task template pattern with graduated difficulty tiers, 7-channel instrumented campaign execution, MockLM D7 artifact exclusion, Clopper-Pearson CIs, Bayesian posterior with Jeffreys prior, Fisher's exact tests, dose-response analysis, forbidden proxy audit
- **Phase 8:** Mock-framework-simulation pattern, BFS provenance reachability, fault injection testing, ForgeCheckpointSaver wrapping pattern, conditional edge absence detection, cross-architecture campaign with scenario diversity enforcement, anchor comparison matrix (MockLM, OpenClaw, AG2, LangGraph)

## Convention Evolution

All conventions established in v1.0 (Phase 1) carry forward unchanged. No formal convention changes in v2.0, but the following project-level decisions were recorded:

| Phase | Convention/Decision | Description | Status |
|-------|-------------------|-------------|--------|
| 7 | CC-017 | D4 detection requires 4 heuristics (self-ref, forward-ref, cross-type, gap) | Active |
| 7 | CC-018 | D7 detection requires external tool_call_log | Active |
| 7 | CC-019 | Empty strings are present output, wrapped to sentinel | Active |
| 7 | CC-015 triggered | Reframe detection → structural prevention | Active |
| 8 | CC-020 | Reversibility uses root-node reachability | Active |
| 8 | CC-021 | RQ4 POSITIVE (pipeline-validated) | Active |
| 8 | CC-014 satisfied | Multi-architecture requirement met (3 types) | Closed |

See `.gpd/CONVENTIONS.md` for the full formal convention ledger (unchanged from v1.0).

## Figures and Data Registry

| File | Phase | Description | Paper-ready? |
|------|-------|-------------|--------------|
| data/campaign/injection_sanity_check.json | 7 | D1-D9 injection sanity check results (90/90) | Yes |
| data/campaign/corpus_manifest.json | 7 | 20-template adversarial corpus manifest | Yes |
| data/campaign/runs/ (211 files) | 7 | Full campaign run data with 7-channel instrumentation | Yes |
| data/campaign/raw_violations.jsonl | 7 | Per-run violation extraction (211 entries) | Yes |
| data/campaign/analysis_results.json | 7 | RQ2b statistical analysis (CP, Bayesian, Fisher's) | Yes |
| data/campaign/validation_report.json | 7 | Per-category/stress/dtype breakdown | Yes |
| docs/violation-campaign-report.md | 7 | Self-contained 10-section RQ2b report | Yes |
| data/compaction/genuine/pilot-results.jsonl | 6 | Track A pilot dry-run results (6 trials) | No (dry-run) |
| data/compaction/genuine/pilot-analysis.json | 6 | Pilot analysis with anchor comparisons | No (dry-run) |
| data/compaction/genuine/analysis-results.json | 6 | Full RQ3b analysis (dry-run data) | No (dry-run) |
| docs/genuine-compaction-report.md | 6 | RQ3b report with PARTIAL verdict | No (dry-run) |
| docs/pilot-report.md | 6 | Track A pilot report | No (dry-run) |
| data/xarch/ag2_campaign.jsonl | 8 | 55-session AG2 campaign results | Yes |
| data/xarch/langgraph_campaign.jsonl | 8 | 55-session LangGraph campaign results | Yes |
| data/xarch/analysis_results.json | 8 | RQ4 cross-architecture analysis | Yes |
| data/xarch/coverage_gaps.json | 8 | Per-framework coverage gap documentation | Yes |
| docs/cross-architecture-report.md | 8 | Self-contained 9-section RQ4 report | Yes |

## Open Questions

1. Does run_queue.py use session-layer LLM compaction during task execution? (HIGH — from v1.0)
2. What is the queue file rotation/deletion policy in production? (MEDIUM — from v1.0)
3. Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured on live data? (HIGH — SPF-01)
4. Does the mock-backend qualification hold when moving to live API calls? (HIGH — all v2.0 verdicts pending)
5. Can forge overhead be kept below 20% of baseline task completion time in production? (MEDIUM — RQ5)

## Dependency Graph

```
Phase 6 "Genuine Compaction Experiments"
  requires: Phase 1 (ontology, forge_nulls.py), Phase 4 (compaction-report.json)
  provides: summary_parser.py, embedding_similarity.py, GenuineCompactionRunner,
            task_templates.py, track_c_ablation.py, swebench_forge_agent.py,
            compaction_analysis.py, RQ3b PARTIAL verdict

Phase 7 "Adversarial Task Design and Natural Violation Campaign"
  requires: Phase 1 (ontology), Phase 3 (violation detection infrastructure)
  provides: extended_validator.py (9/9 D-types), adversarial_corpus.py (20 templates),
            campaign_runner.py, violation_analysis.py, 211-run dataset,
            RQ2b NEGATIVE-STRONG verdict, CC-015 trigger

Phase 8 "Cross-Architecture Generalization"
  requires: Phase 7 (extended validator, campaign baseline)
  provides: ag2_integration_harness.py, langgraph_integration_harness.py,
            xarch_campaign_runner.py, xarch_analysis.py, 110-session dataset,
            RQ4 POSITIVE verdict, CC-014 satisfied
```

Note: Phase 6 is independent of Phases 7-8. Phase 8 depends on Phase 7 outputs.

## Mapping to Original Objectives

| Requirement | Status | Fulfilled by | Key Result |
|-------------|--------|-------------|------------|
| COMP-04: Genuine LLM compaction | Partial | Phase 6 | Pipeline built and dry-run validated; live API untested |
| VIOL-04: Natural violation detection (200+ runs, 3+ categories) | Complete | Phase 7 | 0/211 violations, CP upper 1.73% (NEGATIVE-STRONG) |
| XARCH-01: Cross-architecture adapters (2+ frameworks) | Complete | Phase 8 | AG2 + LangGraph, 0/110 violations (RQ4 POSITIVE) |
| SPF-01: Semantic Provenance Fidelity metric | Partial | Phase 6 | Metric defined, module built, no live measurements |
| PAPER-01: Workshop paper submission | Deferred | — | Not attempted in v2.0 |
