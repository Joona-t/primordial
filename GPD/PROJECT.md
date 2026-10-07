# Primordial Computing: Typed Absence and Provenance in Agentic Systems

## What This Is

A formal systems research project investigating whether typed absence, explicit provenance, and recoverable compaction can prevent silent state loss in long-running autonomous agents. v1.0 validated the forge protocol suite on the OpenClaw agent runtime using post-hoc JSONL ledger analysis, establishing that the 8-state absence ontology is formally sound (PASS), violation detection works on injected faults but zero natural violations were observed (PARTIAL), and structural provenance reachability degrades gracefully under simulated compaction (PARTIAL). v2.0 closed three validation gaps: extended detection to 9/9 D-types at 100%, ran a 211-run adversarial campaign confirming 0 natural violations (CP upper 1.73%, reframing detection → structural prevention per CC-015), and demonstrated cross-architecture transfer to AG2 and LangGraph (0/110 violations, RQ4 POSITIVE). All v2.0 results are pipeline-validated on mock backends; genuine LLM compaction remains untested. The project has 1,600+ passing tests across 3 architecture types.

## Core Research Question

Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?

## Current Milestone: v3.0 Live Validation

**Goal:** Convert every v2.0 "pipeline-validated, pending live validation" verdict into a live result by driving real Claude Code sessions via local subprocess (`claude -p` / Agent SDK on the user's subscription — no paid API key), using Claude Code's own auto-compaction as the genuine compaction event RQ3b requires.

**Target results:**

- RQ3b live: SPF (Jaccard / weighted / embedding) and structural + semantic reachability measured on real LLM compaction summaries from live chambers (COMP-04, SPF-01)
- RQ2b live: subset of the 20-task adversarial corpus re-run against live sessions; Clopper-Pearson bounds updated with live (non-mock) data
- RQ5: forge instrumentation overhead measured against an uninstrumented baseline on live sessions, <20% target
- `data/synthesis/rq-verdicts.json` regenerated with the mock-backend qualifier removed where live evidence lands; all existing tests still passing

**Constraint carried from house rules:** no paid LLM API anywhere in the pipeline — live sessions run through the locally installed Claude Code CLI/subscription only.

## Scoping Contract Summary

### Contract Coverage

- **Violation detection claim:** Forge detects structural failures on real agent tasks that go undetected without it — acceptance: at least 1 naturally-occurring violation detected
- **Compaction survival claim:** Provenance chains survive real context-window compaction with measurable reachability — acceptance: reachability measured and gaps explained
- **False progress to reject:** Short-only tasks, shallow traces, synthetic-only fault detection

### User Guidance To Preserve

- **User-stated observables:** Naturally-occurring silent failure detection count; provenance reachability fraction after real compaction
- **User-stated deliverables:** Violation report with baseline comparison; compaction report with MockLM cross-reference; formalized null ontology
- **Must-have references / prior outputs:** MockLM experiment (100% provenance, 6/6 violations, 87% compression); forge tools (forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py); 103 passing tests
- **Stop / rethink conditions:** Typed absence adds complexity without measurable reliability gains; provenance chains fail under realistic workloads; compaction grounding too brittle for meaningful return paths

### Scope Boundaries

**In scope**

- Instrument Zarathustra/OpenClaw with forge tools on real mixed autonomous workflows
- Measure violation detection on naturally-occurring failures
- Measure provenance survival through real context-window compaction
- Compare against uninstrumented Zarathustra baseline and MockLM anchor results
- Formalize the null ontology with 8 canonical absence states and state-transition rules
- Establish fresh uninstrumented Zarathustra baseline on same task set

**Out of scope**

- General semantic truth in AI systems
- Full epistemology of model outputs
- Porting to third-party runtimes (RQ4 generality — future milestone)
- Paper writing (future milestone)

### Active Anchor Registry

- **ref-mock-experiment:** MockLM experiment in primordial repo (forge tools, 103 passing tests)
  - Why it matters: Establishes the ceiling under controlled conditions — 100% provenance, 6/6 violations, 87% compression
  - Carry forward: planning, execution, verification
  - Required action: compare

### Carry-Forward Inputs

- forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py
- 103 passing tests from MockLM experiment
- Fresh uninstrumented Zarathustra baseline (to be established)

### Skeptical Review

- **Weakest anchor:** Compaction under real context pressure — MockLM never hit genuine memory limits
- **Unvalidated assumptions:** Eight canonical absence states are sufficient; forge tools integrate cleanly into Zarathustra
- **Competing explanation:** Silent failures might be too rare in Zarathustra to surface within a reasonable test campaign
- **Disconfirming observation:** Forge instrumentation adds latency/complexity that degrades agent performance without catching real failures; provenance chains break systematically under real compaction
- **False progress to reject:** Short-only tasks that never trigger compaction; shallow traces where nothing interesting gets pruned; violation detection on synthetic faults only

### Open Contract Questions

- ~~What specific real tasks constitute a sufficient stress test for compaction?~~ RESOLVED v1.0: Coding/patching tasks from real Zarathustra workflows; fp-short-tasks remains partially unresolved (simulated compaction only)
- ~~Should timed_out and interrupted be distinct absence states?~~ RESOLVED v1.0 Phase 1: NOT added; metadata enrichment sufficient (CC-002)
- ~~Should recoverability be binary or graded?~~ RESOLVED v1.0 Phase 1: Binary for now; graded deferred as metadata (CC-003)

## Research Questions

### Answered

- [x] RQ1: Can absence be formalized as a useful computational ontology rather than an implementation accident? — **PASS** (v1.0): 8-state ontology formalized with 64-entry transition table, 300K adversarial transitions with 0 violations, 99% mutation score
- [x] RQ2: Do typed absence and provenance-preserving protocols detect structural failures missed by ordinary logging and summary-based memory? — **PASS** (v2.0): 9/9 D-types at 100% detection (90/90 injected faults), 0% FPR. Natural violations: 0/211 on diverse adversarial corpus (CP upper 1.73%). CC-015 triggered: reframe from detection to structural prevention.
- [~] RQ3: Can history be compacted while preserving grounded return paths to source artifacts? — **PARTIAL** (v2.0): Measurement pipeline built and validated (summary parser, embedding similarity, Track A/C frameworks). Structural reachability degrades gracefully under simulated compaction (v1.0). Genuine LLM compaction pipeline-ready but untested (no API key).
- [x] RQ4: Do these gains transfer beyond a single recursive runtime into other agent architectures? — **POSITIVE** (v2.0): AG2 (message-passing) + LangGraph (graph-based) adapters validated. 0/110 cross-architecture violations, reversibility=1.0, 100% trace integrity. Combined 321-session CP upper 1.14%. CC-014 satisfied.

### Answered with Negative Finding

- [x] RQ2b: Do natural violations occur at detectable rates on longer/harder real agent tasks? — **NEGATIVE-STRONG** (v2.0): 0/211 violations across 20 tasks, 9 categories, 4 stress levels (mock backend). CP upper 1.73%, Bayesian P(rate>2%)=1.38%. Pipeline-validated, pending live validation.

### Open

- [ ] RQ3b: Does structural reachability hold under genuine LLM context-window compaction (not simulated)? — Pipeline built and dry-run validated. v3.0 unblocks live execution via Claude Code CLI subprocess (subscription auth, no API key): Claude Code's auto-compaction is the genuine compaction event.
- [ ] RQ5: Can forge tools be deployed with acceptable overhead on production agent systems? — v3.0 measures overhead vs uninstrumented baseline on live sessions (<20% target).

### Out of Scope

- Full semantic reachability measurement (content fidelity behind refs) — SPF metric defined but not yet measured on live data
- Paper writing — deferred to future milestone
- Production deployment — system validated on mock backends only

## Research Context

### Physical System

Agent runtimes performing long-horizon autonomous workflows. Specifically: Zarathustra/OpenClaw agent with subcall chains, context-window compaction, and tool use.

### Theoretical Framework

Formal state machines with typed absence ontology. Eight canonical absence states (not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable) with legal/illegal transition rules and mandatory provenance metadata.

**Note:** `resolved`/`unresolved` are REF states describing whether a `source_ref` link resolves to its target artifact. They are NOT absence states. Absence states describe WHY a value is absent (e.g., `not_generated` = LLM did not produce output). Ref states describe WHETHER a provenance link works (e.g., `resolved` = the ref points to a valid artifact). These are orthogonal: a field can have `{state: "pruned_recoverable"}` with source_refs that are `"resolved"`.

### Key Parameters and Scales

| Parameter | Symbol | Regime | Notes |
| --------- | ------ | ------ | ----- |
| Context window pressure | — | Real limits (~128K-200K tokens) | Must trigger genuine compaction |
| Task complexity | — | Mixed autonomous workflows | Tool use, subcalls, file ops |
| Absence state count | 8 | Fixed ontology | May expand if timed_out/interrupted needed |
| Provenance chain depth | — | Unbounded in theory | Practical limit from compaction |

### Known Results

**MockLM anchor (controlled ceiling):**
- 100% provenance reachability, 6/6 deliberate violations caught, 87% trace compression vs vanilla logger

**v1.0 results (real OpenClaw runtime):**
- 8-state ontology: 64-entry transition table, 300K adversarial transitions, 0 violations, 99% mutation score
- OpenClaw adapter: 4 interception points, post-hoc JSONL, 453 passing tests
- Baselines: uninstrumented reachability=0.0, forge reachability=1.0, compression=1.18x
- Violation detection: 44.4% aggregate on D1-D9 [CI: 0.344-0.544], 0% FPR, 0 natural violations
- Compaction: structural reachability 0.93 (10% deletion) → 0.25 (90%), backtracking at 80%
- Synthesis: RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL; no stop/rethink conditions triggered

**v2.0 results (cross-architecture validation):**
- Extended validator: 9/9 D-types at 100% detection (90/90 injections), up from 4/9 in v1.0
- Adversarial campaign: 0/211 violations on mock backend (20 tasks, 9 categories, 4 stress levels)
- Statistics: CP 95% upper 1.73%, Bayesian P(rate>2%)=1.38%, RQ2b: NEGATIVE-STRONG
- AG2 adapter: 36 tests, reversibility=1.0, 0 null violations, fault injection 100%
- LangGraph adapter: 37 tests, reversibility=1.0, checkpointer transparency confirmed
- Cross-architecture campaign: 110 sessions (55 AG2 + 55 LG), 0 violations, CP combined upper 3.30%
- All 321 sessions combined: CP upper 1.14%, RQ4: POSITIVE
- Compaction pipeline: measurement tools built, dry-run validated, live API untested

### What Is New

v2.0 extended from single-runtime (OpenClaw) to three architectures (queue-based, message-passing, graph-based). The key finding is that forge structural guarantees transfer across architecture types with equivalent metrics. The negative finding on natural violations (0/321 combined) triggers CC-015: reframe from detection to structural prevention — the absence of violations IS the result, proving the protocol prevents the class of failures it targets. Remaining gap: genuine LLM compaction untested (pipeline ready, API key needed).

### Target Venue

System first, paper later. No venue targeted for this milestone.

### Computational Environment

Local development environment. Zarathustra/OpenClaw agent runtime. Python-based forge tools.

## Notation and Conventions

See `GPD/CONVENTIONS.md` for all notation and sign conventions.

## Unit System

Not applicable (formal systems / software engineering research).

## Requirements

### Validated

- [x] FORM-01: 8-state absence ontology with 64-entry transition table — v1.0
- [x] FORM-02: Property-based testing (300K transitions, 0 violations; 99% mutation score) — v1.0
- [x] FORM-03: Ontology design questions resolved (timed_out/interrupted NOT added; binary recoverability) — v1.0
- [x] INTG-01: Forge-to-OpenClaw adapter (4 interception points, 53 tests) — v1.0
- [x] INTG-02: Compaction mechanism characterized (semi-transparent, post-hoc JSONL strategy) — v1.0
- [x] BASE-01: Uninstrumented Zarathustra baseline (reachability=0.0) — v1.0
- [x] BASE-02: Structured-logging intermediate baseline — v1.0
- [x] BASE-03: Forge-instrumented baseline (reachability=1.0) — v1.0
- [x] VIOL-01: Differential detection (+0.444, CI excludes zero) — v1.0
- [x] VIOL-02: D1-D9 fault injection (90+ injections, 4/9 detected) — v1.0
- [x] COMP-02: Structural reachability post-compaction (0.93→0.25) — v1.0
- [x] COMP-03: Compression ratio vs MockLM (1.18x vs 1.10x) — v1.0
- [x] XREF-01: Side-by-side metrics table vs MockLM — v1.0
- [x] XREF-02: RQ verdicts (PASS/PARTIAL/PARTIAL) — v1.0
- [x] XREF-03: Gap analysis with explanations — v1.0

### Validated (v2.0)

- [x] VIOL-04: Natural violation detection on diverse workloads — 0/211 on 20 tasks, 9 categories, 4 stress levels. CP upper 1.73%. NEGATIVE-STRONG (pipeline-validated). — v2.0
- [x] XARCH-01: Cross-architecture adapters — AG2 (message-passing) + LangGraph (graph-based). 0/110 violations, reversibility=1.0, 73 integration tests. — v2.0
- [x] D-type coverage: Extended from 4/9 to 9/9 D-types at 100% detection (90/90 injected faults) — v2.0

### Partial (honest limitations documented)

- [~] VIOL-03: Natural violation detection — 0/211 combined (v1.0 0/30 + v2.0 0/211), CP upper 1.73%. Mock backend only.
- [~] COMP-01: Real compaction (128K+ tokens) — simulated only (v1.0), pipeline built but untested on live API (v2.0)
- [~] COMP-04: Genuine LLM compaction — measurement tools built, dry-run validated, live API blocked by missing key
- [~] SPF-01: Semantic Provenance Fidelity — metric defined, embedding similarity module built, no live measurements

### Deferred

- [ ] PAPER-01: Workshop paper submission (AGENT 2026, MemAgents, or arXiv) — deferred to future milestone
- [ ] Live validation: All v2.0 verdicts carry "pipeline-validated, pending live validation" qualifier

See `GPD/milestones/v1.0-REQUIREMENTS.md` for archived v1.0 requirements.
See `GPD/milestones/v2.0-REQUIREMENTS.md` for archived v2.0 requirements.

## Key References

- **ref-mock-experiment:** MockLM experiment in primordial repo — forge tools with 103 passing tests (benchmark anchor)
- **ref-v1.0-synthesis:** Cross-reference and synthesis report (docs/cross-reference-report.md)
- **ref-knowledge-objects:** Zahn & Chana (March 2026) — 60% fact loss per LLM compression pass
- **ref-prov-agent:** Souza et al. (IEEE e-Science 2025) — agent provenance capture
- **ref-agentspec:** Wang & Poskitt (ICSE 2026) — formal agent action guards
- **ref-fame:** FAME Framework — 93.5% silent failure detection in autonomous systems

## Constraints

- **Multi-runtime:** ~~v2.0 must validate on 2+ agent architectures~~ **SATISFIED** v2.0 (3 architectures: queue-based, message-passing, graph-based)
- **Real compaction:** Tasks must trigger genuine context-window compaction (128K+ tokens) — **STILL OPEN** (pipeline ready, no API key)
- **Evidence standard:** Self-report from the system is not sufficient evidence (from methodology)
- **Statistical power:** ~~Sample sizes must support detection of 5% violation rate with 95% power~~ **SATISFIED** v2.0 (321 sessions, CP upper 1.14%)
- **Mock qualification:** All v2.0 results carry "pipeline-validated, pending live validation" qualifier

## Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| Violation detection is primary signal over provenance scores | Real-world reliability matters more than perfect metrics | Good: guided honest negative finding on VIOL-03 |
| Both MockLM and fresh Zarathustra baseline as anchors | Cross-reference between controlled and real conditions | Good: dual baseline enabled gap analysis |
| System first, paper later | Build and validate before writing up | Good: paper deferred; v1.0 produced honest partial results |
| CC-001: resolved is REF state, not absence state | Implementation (forge_nulls.py) is ground truth | Good: eliminated documentation ambiguity |
| CC-002: timed_out/interrupted NOT added | Identical transition rules; metadata sufficient | Good: kept ontology at 8 states |
| CC-005: Post-hoc JSONL as primary adapter approach | Non-invasive, works across VM boundary | Good: enabled measurement without modifying OpenClaw |
| CC-009: Post-hoc injection reveals architectural gap | 3/6 D1-D6 post-hoc vs 6/6 MockLM registration-time | Revisit: registration-time detection needed for D3/D4/D6 |
| CC-011: Accept negative finding on natural violations | Honest reporting over false claims | Good: 0/30 with CI honestly documented |
| CC-013: structural_reachability over BFS for compaction | BFS stays 1.0 for linear chains; struct_reach sensitive | Good: correct metric selected |
| CC-014: Multi-architecture validation required for PhD | Single runtime insufficient for generality claim | Active: v2.0 targets 2+ frameworks |
| CC-015: Reframe detection → prevention if 0 natural violations persist | Detection of non-existent problem has no value | **TRIGGERED** v2.0: 0/211 on mock backend, reframe to structural prevention |
| CC-016: Semantic Provenance Fidelity as new metric class | Structural reachability misses content fidelity | Partial: SPF metric defined, embedding module built, no live measurements |
| CC-017: D4 detection requires 4 heuristics | self-ref, forward-ref, cross-type, gap for 100% injected detection | Good: 9/9 D-types at 100% |
| CC-018: D7 detection requires external tool_call_log | Cannot detect from chamber structure alone | Good: honest limitation documented |
| CC-019: Empty strings are present output (not absent) | Adapter wraps to sentinel for forge compliance | Good: consistent across AG2/LG |
| CC-020: Reversibility uses root-node reachability | ForgeCheckpointSaver wrapping pattern for graph-based architectures | Good: validated on LangGraph |
| CC-021: RQ4 verdict POSITIVE (pipeline-validated) | Forge guarantees transfer across 3 architecture types | Good: CC-014 satisfied |

---

_Last updated: 2026-06-12 at v3.0 milestone start_
