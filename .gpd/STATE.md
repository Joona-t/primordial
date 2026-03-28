# Research State

## Project Reference

See: .gpd/PROJECT.md (updated 2026-03-27)

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** v2.0 — The Forgetting Agent: close validation gaps with genuine compaction, diverse workloads, and cross-architecture testing

## Current Position

**Current Phase:** 8 (Cross-Architecture) — COMPLETE
**Current Plan:** 4/4
**Total Plans in Phase:** 4
**Total Phases:** 8 (5 complete from v1.0, 3 complete in v2.0: Phase 6 code complete, Phase 7 complete, Phase 8 complete)
**Status:** Phase 8 complete. RQ4: POSITIVE (pipeline-validated, pending live validation). 0/110 cross-architecture violations, CP upper 3.30%.
**Last Activity:** 2026-03-28 — Phase 8 all 4 plans executed. AG2+LangGraph adapters validated, 110-session campaign, RQ4 verdict.

**Progress:** [██████████] 100% (v1.0 complete, v2.0 phases 6-8 complete)

## Active Calculations

- Phase 2.1 research: genuine compaction experiment design (agent running)
- Phase 2.2 research: adversarial task corpus design (agent running)
- Phase 2.3 research: cross-architecture adapter feasibility (agent running)
- Publication deadline research (agent running)

## Intermediate Results

### v1.0 Results (archived)
See `.gpd/milestones/v1.0/RESEARCH-DIGEST.md` for complete v1.0 results.

### v2.0 Literature Survey (2026-03-27)
- **Novelty confirmed:** No prior work combines typed absence + provenance + compaction in single framework
- **Closest competitors:** PROV-AGENT (captures, doesn't enforce), AgentSpec (guards actions, not data), Knowledge Objects (measures loss, doesn't prevent), Kumiho (formal memory, not structural integrity)
- **Key empirical finding:** 60% fact loss per LLM compression pass (Knowledge Objects, March 2026)
- **Assessment:** Current work is ~1/3 PhD thesis; needs validation breadth, theoretical depth, demonstrated impact

## Open Questions

- Does run_queue.py use session-layer LLM compaction during task execution? (HIGH — from v1.0)
- What is the queue file rotation/deletion policy in production? (MEDIUM — from v1.0)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH — SPF-01)
- ~~Which agent frameworks have the most accessible instrumentation hooks?~~ RESOLVED Phase 8: AG2 (safeguard hooks) and LangGraph (CheckpointSaver) both provide adequate interception points
- ~~What sample size is needed to detect a 5% natural violation rate?~~ RESOLVED Phase 7: N=211, CP upper 1.73%, 98%+ power at 2% rate

## Accumulated Context

### Decisions

Full v1.0 decision log: see `.gpd/milestones/v1.0/RESEARCH-DIGEST.md`.

New v2.0 decisions:
- CC-014: Multi-architecture validation required for PhD-level generality claim
- CC-015: Reframe detection → prevention if 0 natural violations persist on 200+ diverse runs — **TRIGGERED** (0/211 on mock backend)
- CC-016: Semantic Provenance Fidelity (SPF) as new metric class bridging structural/semantic gap
- CC-017: D4 detection requires 4 heuristics (self-ref, forward-ref, cross-type, gap) for 100% on injected faults
- CC-018: D7 detection requires external tool_call_log; cannot be detected from chamber structure alone
- CC-019: Empty strings are present output (not absent) — adapter wraps to sentinel for forge compliance
- CC-020: Reversibility uses root-node reachability; ForgeCheckpointSaver wrapping pattern validated for graph-based architectures
- CC-021: RQ4 verdict POSITIVE (pipeline-validated, pending live validation) — forge guarantees transfer across 3 architecture types

### Active Approximations

None (formal systems, no approximations needed).

**Convention Lock:**

- All v1.0 conventions carry forward (see `.gpd/CONVENTIONS.md`)

*New v2.0 conventions (pending formalization):*
- Semantic Provenance Fidelity: embedding cosine similarity between original and recovered artifacts
- Genuine vs. simulated compaction: explicitly labeled in all measurements
- Cross-architecture metrics: same definitions across frameworks, architectural differences documented

### Blockers/Concerns

- SWE-Bench setup requirements unknown (need research agent output)
- Agent framework API stability uncertain (LangGraph/CrewAI evolve rapidly)

### Phase 7 Results (2026-03-28)
- **Extended validator:** 9/9 D-types at 100% detection (90/90 injections), up from 4/9 in v1.0
- **Adversarial corpus:** 20 task templates, 9 categories, 42 unique (task, D-type) pairs
- **Campaign:** 211 runs (mock backend), 0 genuine violations
- **Statistics:** CP 95% upper bound 1.73%, Bayesian P(rate>2%) = 1.38%
- **RQ2b verdict:** NEGATIVE-STRONG (pipeline-validated, pending live validation)
- **CC-015 triggered:** Reframe detection → structural prevention
- **Tests:** 599 new tests (59 extended validator + 489 corpus/runner + 51 analysis)

### Phase 8 Results (2026-03-28)
- **AG2 adapter:** 36 tests, reversibility=1.0, 0 null violations, trace integrity verified, fault injection 100%
- **LangGraph adapter:** 37 tests, reversibility=1.0, 0 null violations, trace integrity verified, checkpointer transparency confirmed
- **Campaign:** 110 sessions (55 AG2 + 55 LangGraph), 0 violations
- **Statistics:** Combined CP 95% upper bound 3.30%. All sessions combined (321): CP upper 1.14%
- **RQ4 verdict:** POSITIVE (pipeline-validated, pending live validation)
- **CC-014 SATISFIED:** Multi-architecture requirement met (3 architecture types: message-passing, graph-based, queue-based)
- **CC-015 CONSISTENT:** Structural prevention framing reinforced across architectures
- **Coverage gaps:** AG2 5 invisible transitions, LangGraph 6 invisible transitions (documented)
- **Tests:** 187 new tests (36 AG2 + 37 LangGraph + 76 campaign + 38 analysis)

## Session Continuity

**Last session:** 2026-03-28
**Stopped at:** Phase 8 complete. All v2.0 phases done. Milestone v2.0 ready for completion.
**Resume file:** —
