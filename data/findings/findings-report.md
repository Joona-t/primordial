# Research Findings Ledger

**Generated:** 2026-03-27T04:47:41.463930+00:00
**Total findings:** 13

## Summary

| Metric | Value |
|--------|-------|
| Total findings | 13 |
| Positive | 6 |
| Negative | 1 |
| Category: architecture | 1 |
| Category: baseline | 2 |
| Category: compaction | 2 |
| Category: methodology | 4 |
| Category: negative | 1 |
| Category: ontology | 1 |
| Category: publication | 1 |
| Category: violation | 1 |

## Phase 0 (3 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0011 | methodology | Novelty confirmed: no prior work combines typed absence + provenance + compaction | positive | high |
| F-0012 | methodology | Current state: ~1/3 of PhD thesis, researcher capable of PhD-level work | partial | high |
| F-0013 | publication | Publication windows: NeurIPS (5wk), ICSE 2027 (3mo), AAAI 2027 (4mo) | neutral | high |

### F-0011: Novelty confirmed: no prior work combines typed absence + provenance + compaction

**Category:** methodology | **Verdict:** positive | **Confidence:** high
**Timestamp:** 2026-03-27T04:47:41.462626+00:00

Three independent literature surveys across 60+ papers confirm: no prior work integrates typed absence ontology, structural provenance enforcement, and recoverable compaction in a single framework for agent runtimes. Components have precedent individually; integration is the novel contribution.

**Evidence:**
```json
{
  "papers_surveyed": 60,
  "closest_competitors": [
    "PROV-AGENT (captures, doesn't enforce)",
    "AgentSpec (guards actions, not data)",
    "Knowledge Objects (measures loss, doesn't prevent)",
    "Kumiho (formal memory, not structural integrity)",
    "FAME (statistical, not structural protocol)"
  ],
  "novelty_type": "integration"
}
```

**Tags:** novelty, literature-survey, phd-assessment
**References:** Planning phase research agents (3 parallel)

---

### F-0012: Current state: ~1/3 of PhD thesis, researcher capable of PhD-level work

**Category:** methodology | **Verdict:** partial | **Confidence:** high
**Timestamp:** 2026-03-27T04:47:41.462806+00:00

Assessment by PhD committee simulation: exceptional methodology, honest negative findings, 537+ tests. Gaps: zero natural violations, simulated-only compaction, single runtime, missing theoretical depth (no completeness argument, no formal proofs, no database null theory engagement). Path requires: Finnish university enrollment, or academic collaborator, or workshop paper → industry venue route.

**Evidence:**
```json
{
  "thesis_completion": "33%",
  "strengths": [
    "methodology",
    "implementation",
    "honest negatives"
  ],
  "gaps": [
    "natural violations",
    "genuine compaction",
    "theory",
    "multi-arch"
  ],
  "test_count": 537,
  "open_theoretical_gaps": [
    "no composition algebra",
    "no evaluation logic for absent fields",
    "no possible-worlds semantics (Libkin)",
    "runtime-only enforcement"
  ],
  "must_cite_count": 18
}
```

**Tags:** phd-assessment, meta
**References:** PhD study design plan

---

### F-0013: Publication windows: NeurIPS (5wk), ICSE 2027 (3mo), AAAI 2027 (4mo)

**Category:** publication | **Verdict:** neutral | **Confidence:** high
**Timestamp:** 2026-03-27T04:47:41.462901+00:00

AGENT 2026, MemAgents, FormaliSE — all closed. Actionable: arXiv (immediate), NeurIPS 2026 (May 4-6), ICSE 2027 (Jun 23-30), AAAI 2027 (Jul 25 - Aug 1), OOPSLA 2027 R1 (~Oct 2026).

**Evidence:**
```json
{
  "closed": [
    "AGENT 2026",
    "MemAgents",
    "FormaliSE 2026",
    "AAMAS 2026",
    "OOPSLA 2026 R2"
  ],
  "open": {
    "arXiv": "always",
    "NeurIPS 2026": "2026-05-04",
    "ICSE 2027": "2026-06-23",
    "AAAI 2027": "2026-07-25",
    "OOPSLA 2027 R1": "~2026-10"
  }
}
```

**Tags:** PAPER-01, deadlines
**References:** Publication deadline research agent

---

## Phase 1 (1 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0001 | ontology | 8-state absence ontology formalized and verified | positive | high |

### F-0001: 8-state absence ontology formalized and verified

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-27T04:47:41.460763+00:00

64-entry transition table (45 legal, 19 illegal). 300K+ adversarial Hypothesis transitions with 0 violations. 99% mutation score (103/104 non-equivalent killed).

**Evidence:**
```json
{
  "states": 8,
  "transitions": 64,
  "legal": 45,
  "illegal": 19,
  "adversarial_transitions": 300000,
  "violations": 0,
  "mutation_score": 0.99,
  "mutants_killed": 103,
  "mutants_total": 104
}
```

**Tags:** RQ1, FORM-01, FORM-02
**References:** Phase 1 Plans 01-02

---

## Phase 3 (2 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0002 | violation | Violation detection: 44.4% on injected faults, 0% FPR | partial | high |
| F-0003 | negative | NEGATIVE: Zero natural violations in 30 runs | negative | high |

### F-0002: Violation detection: 44.4% on injected faults, 0% FPR

**Category:** violation | **Verdict:** partial | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-27T04:47:41.461292+00:00

4/9 fault types detected at 100% (D1, D2, D5, D9). Aggregate: 40/90 = 44.4% [CI: 0.344-0.544]. Differential: +0.444 vs uninstrumented. FPR = 0.0%.

**Evidence:**
```json
{
  "types_detected": [
    "D1",
    "D2",
    "D5",
    "D9"
  ],
  "types_missed": [
    "D3",
    "D4",
    "D6",
    "D7",
    "D8"
  ],
  "aggregate_rate": 0.444,
  "ci_lower": 0.344,
  "ci_upper": 0.544,
  "fpr": 0.0,
  "injections": 90,
  "detections": 40
}
```

**Tags:** RQ2, VIOL-01, VIOL-02
**References:** Phase 3 Plan 02

---

### F-0003: NEGATIVE: Zero natural violations in 30 runs

**Category:** negative | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-27T04:47:41.461408+00:00

0/30 clean runs detected natural structural violations. Clopper-Pearson 95% upper bound: 11.6%. Mechanism validated on injected faults but practical value on naturally-occurring failures is undemonstrated.

**Evidence:**
```json
{
  "runs": 30,
  "natural_violations": 0,
  "cp_upper_95": 0.116,
  "cp_lower_95": 0.0,
  "workload": "coding/patching tasks",
  "power_at_5pct": 0.785,
  "power_at_2pct": 0.455
}
```

**Tags:** RQ2, VIOL-03, negative-finding
**References:** Phase 3 Plan 02, Cross-reference report Section 3

---

## Phase 4 (1 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0004 | compaction | Simulated compaction: reachability 0.93→0.25 over 10-90% deletion | partial | medium |

### F-0004: Simulated compaction: reachability 0.93→0.25 over 10-90% deletion

**Category:** compaction | **Verdict:** partial | **Confidence:** medium
**Research Question:** RQ3
**Timestamp:** 2026-03-27T04:47:41.461493+00:00

Structural reachability degrades monotonically. Backtracking threshold at 80% deletion. Pre-compaction reachability 1.0 matches MockLM ceiling. SIMULATED ONLY — genuine LLM compaction untested.

**Evidence:**
```json
{
  "type": "simulated_deletion",
  "reachability_10pct": 0.932,
  "reachability_50pct": 0.821,
  "reachability_80pct": 0.438,
  "reachability_90pct": 0.25,
  "backtracking_threshold": 0.8,
  "pre_compaction": 1.0,
  "mockml_ceiling": 1.0,
  "violation_regression": "D1/D2/D5/D9 at 100% post-compaction"
}
```

**Tags:** RQ3, COMP-02, simulated-only
**References:** Phase 4 Plan 02

---

## Phase 5 (1 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0005 | methodology | v1.0 synthesis: RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL | partial | high |

### F-0005: v1.0 synthesis: RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL

**Category:** methodology | **Verdict:** partial | **Confidence:** high
**Timestamp:** 2026-03-27T04:47:41.461584+00:00

All 4 automated consistency checks pass. 62 programmatic cross-reference checks green. No stop/rethink conditions triggered. Compaction inconclusive (simulated only).

**Evidence:**
```json
{
  "rq1": "PASS",
  "rq2": "PARTIAL",
  "rq3": "PARTIAL",
  "consistency_checks": 4,
  "consistency_pass": 4,
  "xref_checks": 62,
  "xref_pass": 62,
  "total_tests": 492
}
```

**Tags:** synthesis, v1.0-complete
**References:** docs/cross-reference-report.md

---

## Phase 6 (2 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0006 | compaction | BREAKTHROUGH: compact_20260112 API enables full compaction observability | positive | high |
| F-0007 | baseline | Knowledge Objects: 60% fact loss per LLM compression pass | positive | high |

### F-0006: BREAKTHROUGH: compact_20260112 API enables full compaction observability

**Category:** compaction | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ3b
**Timestamp:** 2026-03-27T04:47:41.461686+00:00

Anthropic's compaction API with pause_after_compaction=true returns stop_reason='compaction' with exact boundary capture. Min trigger: 50K tokens, default 150K. This enables controlled genuine compaction experiments — the key missing piece from v1.0.

**Evidence:**
```json
{
  "api": "compact_20260112",
  "param": "pause_after_compaction",
  "stop_reason": "compaction",
  "min_trigger_tokens": 50000,
  "default_trigger_tokens": 150000,
  "compaction_block_type": "compaction"
}
```

**Tags:** COMP-04, breakthrough, api-discovery
**References:** Phase 6 Research, docs/phase-2.1-genuine-compaction-protocol.md

---

### F-0007: Knowledge Objects: 60% fact loss per LLM compression pass

**Category:** baseline | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ3b
**Timestamp:** 2026-03-27T04:47:41.461795+00:00

Zahn & Chana (arXiv:2603.17781, March 2026) measured 60% fact loss per compression pass and 54% project constraint erosion through cascading compaction. This validates our thesis — summaries are lossy and without grounded provenance refs, lost facts are unrecoverable.

**Evidence:**
```json
{
  "paper": "Zahn & Chana, arXiv:2603.17781",
  "date": "2026-03",
  "fact_loss_per_pass": 0.6,
  "constraint_erosion": 0.54,
  "method": "Facts as First Class Objects"
}
```

**Tags:** COMP-04, external-validation, literature
**References:** ref-knowledge-objects

---

## Phase 7 (2 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0008 | methodology | Power analysis: 200 runs gives 98.2% power at 2% violation rate | neutral | high |
| F-0009 | baseline | MAS-FIRE: failures manifest as 'soft semantic deviations' in multi-agent systems | positive | medium |

### F-0008: Power analysis: 200 runs gives 98.2% power at 2% violation rate

**Category:** methodology | **Verdict:** neutral | **Confidence:** high
**Research Question:** RQ2b
**Timestamp:** 2026-03-27T04:47:41.461873+00:00

Statistical power analysis computed. v1.0 had only 26% power to detect a 1% rate and 45.5% for 2%. 200 runs → CP upper bound 1.8% if still 0 violations, 98.2% power at 2%. For <1% claim need 368 runs.

**Evidence:**
```json
{
  "v1_runs": 30,
  "v1_cp_upper": 0.116,
  "v1_power_at_2pct": 0.455,
  "v2_target_runs": 200,
  "v2_cp_upper_if_zero": 0.018,
  "v2_power_at_2pct": 0.982,
  "v2_power_at_5pct": 1.0,
  "runs_for_1pct_bound": 368
}
```

**Tags:** VIOL-04, power-analysis, sample-size
**References:** tools/power_analysis.py, power_analysis_results.json

---

### F-0009: MAS-FIRE: failures manifest as 'soft semantic deviations' in multi-agent systems

**Category:** baseline | **Verdict:** positive | **Confidence:** medium
**Research Question:** RQ2b
**Timestamp:** 2026-03-27T04:47:41.461947+00:00

MAS-FIRE taxonomy identifies 15 fault types with the key insight that failures manifest as soft semantic deviations — exactly what typed absence should catch. Factory.ai found artifact tracking scores only 2.19-2.45/5.0 across all compression strategies.

**Evidence:**
```json
{
  "taxonomy": "MAS-FIRE",
  "fault_types": 15,
  "injection_mechanisms": 3,
  "key_insight": "soft semantic deviations",
  "factory_artifact_tracking": {
    "low": 2.19,
    "high": 2.45,
    "max": 5.0
  }
}
```

**Tags:** VIOL-04, external-validation, literature
**References:** MAS-FIRE taxonomy, Factory.ai evaluation

---

## Phase 8 (1 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0010 | architecture | All 4 target frameworks have sufficient extensibility without core patches | positive | medium |

### F-0010: All 4 target frameworks have sufficient extensibility without core patches

**Category:** architecture | **Verdict:** positive | **Confidence:** medium
**Research Question:** RQ4
**Timestamp:** 2026-03-27T04:47:41.462021+00:00

AG2 (9 hooks), LangGraph (callbacks + checkpointer), CrewAI (task hooks), OpenHands (event stream) all provide sufficient instrumentation points. AG2 is P0 (closest match to forge model), LangGraph P1 (biggest impact). Universal ForgeAdapter ABC designed.

**Evidence:**
```json
{
  "ag2_hooks": 9,
  "ag2_priority": "P0",
  "langgraph_priority": "P1",
  "crewai_priority": "P2",
  "openhands_priority": "P3",
  "core_patches_needed": 0,
  "adapter_pattern": "ForgeAdapter ABC"
}
```

**Tags:** XARCH-01, adapter-feasibility
**References:** .gpd/phases/08-cross-architecture/08-RESEARCH.md

---
