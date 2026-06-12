# Milestone 2 Research: The Forgetting Agent

## Objective

Close the three validation gaps from v1.0:
1. **Compaction gap:** Test genuine LLM context-window compaction (not simulated deletion)
2. **Violation gap:** Find natural violations on harder/longer/diverse tasks (or tighten upper bound)
3. **Architecture gap:** Validate on 2+ agent frameworks beyond Zarathustra/OpenClaw

## v1.0 Results to Build On

| Metric | v1.0 Result | v2.0 Target |
|--------|-------------|-------------|
| Natural violations | 0/30 (CP UB: 11.6%) | Detect or tighten to CP UB <= 2% |
| Compaction | Simulated only (0.93→0.25) | Genuine LLM compaction measured |
| Architectures | 1 (Zarathustra/OpenClaw) | 3+ (add LangGraph, CrewAI/OpenHands) |
| Test suite | 492 tests | 537+ tests (power analysis + SPF added) |
| Metrics | Structural reachability only | + Semantic Provenance Fidelity (SPF) |

---

## Phase 6: Genuine Compaction Experiments

### Problem Statement

v1.0 tested compaction by programmatically deleting oldest artifacts. This is a lower bound — real LLM compaction might preserve more (intelligent summarization) or less (lossy compression of critical refs). We don't know which until we test.

### Key Finding from Literature

**Knowledge Objects (Zahn & Chana, March 2026):** 60% of facts are lost per single LLM compression pass. This directly validates our thesis — summaries are lossy, and without grounded provenance refs, the lost facts are unrecoverable.

### Experimental Design

#### Benchmark Selection

**Primary:** SWE-Bench Verified (500 instances, human-validated, realistic coding tasks)
- Why: coding tasks are the domain where agent compaction most commonly occurs
- Long-horizon tasks (multi-file changes, debugging chains) will trigger compaction

**Secondary:** GAIA (general AI assistant tasks, diverse reasoning)
- Why: tests generality beyond coding; includes multi-step tool use

**Tertiary:** Custom long-horizon task corpus
- Purpose: tasks specifically designed to exceed 128K tokens
- Design: multi-step file editing → debugging → testing → documentation chains

#### Instrumentation Plan

Two approaches, ordered by feasibility:

**Approach A: Post-hoc session analysis**
- Run agent sessions normally, capture full session transcripts
- Apply forge tools post-hoc to analyze compaction events
- Identify before/after compaction boundaries in transcripts
- Measure: what refs survived, what was lost, what was summarized

**Approach B: Live instrumentation (preferred, if feasible)**
- Hook into agent's compaction mechanism
- Snapshot artifact state before compaction trigger
- Record compaction output (summary text)
- Snapshot artifact state after compaction
- Compute SPF on each compacted artifact

#### Metrics

1. **Structural reachability** (same as v1.0): resolved_refs / total_refs
2. **SPF — Semantic Provenance Fidelity** (NEW):
   - `SPF_jaccard`: token set overlap between original and recovered
   - `SPF_weighted`: TF-weighted token preservation
   - `SPF_embedding`: cosine similarity of embeddings (if sentence-transformers available)
3. **Fact retention rate**: fraction of key facts preserved through compaction
4. **Provenance chain depth post-compaction**: how deep can you trace back?

#### Sample Size

- **Minimum:** 50 genuine compaction events across 20+ tasks
- **Target:** 100 compaction events for robust statistics
- From power analysis: 200 runs needed for violation detection anyway

#### Controls

- v1.0 simulated compaction results as baseline
- MockLM anchor as ceiling
- Uninstrumented agent as floor

---

## Phase 7: Adversarial Task Design

### Problem Statement

v1.0 tested on coding/patching tasks only — a narrow slice. If violations only occur on complex multi-step reasoning or concurrent sub-agent calls, we'd never see them on simple patches.

### Statistical Power Analysis (computed)

From `tools/power_analysis.py`:

| If true rate is... | Runs needed for 95% power | v1.0 had power... |
|---------------------|--------------------------|-------------------|
| 1% | 299 | 26.0% |
| 2% | 149 | 45.5% |
| 5% | 59 | 78.5% |
| 10% | 29 | 95.8% |

**v1.0 had only 26% power to detect a 1% violation rate.** We literally couldn't have seen rare violations.

**v2.0 target:** 200 runs → 98.2% power at 2% rate, CP upper bound 1.8% if still 0 violations.

### Task Taxonomy

Tasks ranked by likelihood of surfacing each violation type:

**Category A: Context Exhaustion Tasks** (targets D2, D7)
- Long-horizon coding tasks requiring 100+ steps
- Multi-file refactoring across 10+ files
- Debugging chains requiring full stack trace recall
- *Expected violations:* Ungrounded summaries after compaction, trace data loss

**Category B: Recursive/Branching Tasks** (targets D3, D4)
- Tasks requiring backtracking (try approach A, fail, try approach B)
- Parallel sub-agent calls that must be synchronized
- Nested function call chains (agent calls agent calls agent)
- *Expected violations:* Dangling refs to abandoned branches, duplicate IDs from parallel calls

**Category C: Error Recovery Tasks** (targets D1, D5, D9)
- Tasks where the LLM produces empty/malformed responses
- Tasks requiring retry after tool failures
- Tasks where completion criteria are ambiguous
- *Expected violations:* Empty output without typed absence, null discipline violations

**Category D: State Mutation Tasks** (targets D6, D8)
- Tasks where intermediate state is overwritten
- Tasks with late-arriving async results
- Tasks with encoding/format transformations
- *Expected violations:* Post-seal registration, content corruption

### Task Corpus Specification

| Category | Tasks | Runs per task | Total runs | Target violations |
|----------|-------|---------------|------------|-------------------|
| A: Context Exhaustion | 10 | 5 | 50 | D2, D7 |
| B: Recursive/Branching | 10 | 5 | 50 | D3, D4 |
| C: Error Recovery | 10 | 5 | 50 | D1, D5, D9 |
| D: State Mutation | 10 | 5 | 50 | D6, D8 |
| **Total** | **40** | | **200** | **All D1-D9** |

### Benchmarks to Draw From

- **SWE-Bench:** Categories A, B (long debugging, multi-file changes)
- **WebArena:** Categories B, C (multi-step web interaction, error handling)
- **GAIA:** Categories A, B (multi-step reasoning, tool chains)
- **TAU-bench:** Categories C, D (tool-augmented tasks with edge cases)
- **Custom:** Categories C, D (specifically designed adversarial scenarios)

---

## Phase 8: Cross-Architecture Generalization

### Problem Statement

Validating on one runtime proves the concept works there. A PhD requires demonstrating generality. We need 2+ additional frameworks.

### Framework Assessment

| Framework | State Model | Compaction | Extensibility | Priority |
|-----------|------------|------------|---------------|----------|
| **LangGraph** | StateGraph (typed dict) | Checkpointers + manual | Add/remove nodes, callbacks | **HIGH** — most popular, best documented |
| **CrewAI** | Task/Agent outputs | None built-in | Process hooks, callbacks | **MEDIUM** — different paradigm tests generality |
| **OpenHands** | Action/Observation history | Conversation truncation | Event stream hooks | **MEDIUM** — direct competitor to Zarathustra |
| **AutoGen/AG2** | Message history | Manual truncation | GroupChat hooks | **LOW** — less active development |

### Recommended Priority: LangGraph first, then CrewAI

**LangGraph adapter design:**
- Intercept `StateGraph` node execution (before/after hooks)
- Map node outputs to forge artifacts
- Map state transitions to absence states
- Use checkpointer API for provenance chain
- Hook into message truncation for compaction measurement

**CrewAI adapter design:**
- Intercept `Task.execute()` and `Agent.execute_task()`
- Map crew task outputs to forge artifacts
- Map agent delegation to parent-child provenance refs
- Monitor for empty/failed task outputs → typed absence

### OpenTelemetry Integration

OpenTelemetry GenAI Semantic Conventions provide a framework-agnostic instrumentation layer. Plan:
1. Define custom span attributes for typed absence states
2. Map forge artifact lifecycle to OTel span events
3. Use span links for provenance references
4. Export to OTLP collector for analysis

Custom attributes:
- `forge.absence_state`: one of 8 canonical states
- `forge.artifact_id`: colon-separated hierarchical ID
- `forge.source_refs`: JSON array of upstream artifact IDs
- `forge.content_hash`: SHA-256 of artifact content

---

## New Metric: Semantic Provenance Fidelity (SPF)

### Definition

SPF measures whether the MEANING behind a provenance reference is preserved, not just whether the reference resolves structurally.

```
SPF(original, recovered) = cosine_similarity(embed(original), embed(recovered))
```

### Implementation (complete — `tools/semantic_provenance_fidelity.py`)

Three tiers of measurement:
1. **Token overlap** (zero-dependency baseline): Jaccard + weighted overlap
2. **Embedding cosine** (requires sentence-transformers): dense semantic similarity
3. **Content hash match** (exact preservation check)

### Calibration Plan

1. Generate 500+ (original, recovered) pairs from real compaction events
2. Have 3 human annotators rate semantic preservation (1-5 scale)
3. Compute correlation between SPF scores and human judgment
4. Establish thresholds: SPF >= 0.9 = "faithful", 0.7-0.9 = "degraded", < 0.7 = "lost"

---

## Publication Targets

### Immediate (2026)

- **arXiv preprint** of v1.0 results — establish priority, no deadline
- **Workshop papers** targeting agent reliability workshops at major conferences
  - Paper outline complete: `docs/paper-outline-v1.md`

### Post-Milestone 2 (2027)

- **ICSE 2027 Research Track** — empirical paper with cross-architecture results
- **AAMAS 2027** — multi-agent systems venue
- **OOPSLA 2027** — theoretical foundations (Milestone 3)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 0 natural violations on 200 runs | Medium | High | Reframe: absence discipline PREVENTS violations |
| Genuine compaction breaks all refs | Low | High | Design compaction-resistant ref strategies (hash anchors) |
| Framework APIs break during research | Medium | Medium | Pin versions, abstract adapter interface |
| Insufficient compute budget | Medium | Medium | Prioritize: Phase 7 (200 runs) > Phase 6 (50 compactions) > Phase 8 (adapters) |
| Competing publication appears | Low | Medium | Publish arXiv preprint immediately for priority |

---

## Dependencies and Prerequisites

- [x] Power analysis tool (537 tests passing)
- [x] SPF metric implementation (537 tests passing)
- [x] Paper outline drafted
- [ ] SWE-Bench setup and accessibility verification
- [ ] LangGraph adapter prototype
- [ ] CrewAI adapter prototype
- [ ] Embedding model for SPF (sentence-transformers)
- [ ] Compute budget estimate for 200+ agent runs

---

---

## Critical Findings from Deep Research (2026-03-27)

### Compaction Breakthrough: `compact_20260112` API

Anthropic's compaction API has a `pause_after_compaction: true` parameter that returns `stop_reason: "compaction"` and lets the client inspect the exact boundary before/after. This gives **full observability** into genuine compaction. The compaction block is JSON with `"type": "compaction"` containing summary text. Min trigger: 50K tokens, default 150K.

**This changes everything.** We can now run controlled genuine compaction experiments with full boundary capture. Protocol designed: 3 tracks, 180 trials, ~$800-1200 budget, 6 weeks.

Full protocol: `docs/phase-2.1-genuine-compaction-protocol.md`

### Adversarial Task Design: MAS-FIRE + ReliabilityBench

Key finding: MAS-FIRE taxonomy identifies 15 fault types in multi-agent systems with the critical insight that failures manifest as "soft semantic deviations" — exactly what typed absence should catch. Factory.ai found artifact tracking scores only 2.19-2.45/5.0 across all compression strategies — the exact weakness forge addresses.

Full design: `GPD/phases/07-adversarial-tasks/07-RESEARCH.md` (10 categories, 20 templates, 201 runs)

### Cross-Architecture: AG2 First, Not LangGraph

Surprising finding: AG2 (AutoGen v2) has the closest hook system to forge's interception model (9 hooks: messages, tools, LLM, state) with pass-through semantics. LangGraph is P1 (bigger impact but harder adapter). All 4 frameworks have sufficient extensibility without core patches.

Full analysis: `GPD/phases/08-cross-architecture/08-RESEARCH.md` (947 lines)

### Database Null Theory: 4 Open Gaps Identified

Primordial inherits from Codd (2 nulls), extends beyond Zaniolo (3 nulls), implements Date's vision (eliminate nulls via types). But 4 gaps: no composition algebra, no evaluation logic, no possible-worlds semantics (Libkin), runtime-only enforcement. The ontology is NOT a bilattice (temporal states break axioms). 18 must-cite references identified.

Full positioning: `docs/related-work-null-theory.md`

### Publication Windows

| Venue | Deadline | Status |
|-------|----------|--------|
| NeurIPS 2026 | May 4-6, 2026 | **5 weeks** — tight but possible |
| ICSE 2027 | Jun 23-30, 2026 | **3 months** — primary target |
| AAAI 2027 | Jul 25 - Aug 1, 2026 | **4 months** |
| arXiv | Anytime | Submit v1.0 immediately for priority |
| OOPSLA 2027 R1 | ~Oct 2026 | **6 months** — theoretical paper |

AGENT 2026, MemAgents, FormaliSE 2026 — all CLOSED. Next best workshop venues TBD.

---

**Do not implement Phase 6-8 plans yet. Research document complete. Ready for phase planning.**
