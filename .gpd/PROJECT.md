# Primordial Computing: Typed Absence and Provenance in Agentic Systems

## What This Is

A formal systems research project investigating whether typed absence, explicit provenance, and recoverable compaction can prevent silent state loss in long-running autonomous agents. v1.0 validated the forge protocol suite on the OpenClaw agent runtime using post-hoc JSONL ledger analysis, establishing that the 8-state absence ontology is formally sound (PASS), violation detection works on injected faults but zero natural violations were observed (PARTIAL), and structural provenance reachability degrades gracefully under simulated compaction (PARTIAL). The project has 453 passing tests, a complete measurement pipeline, and honest negative findings.

## Core Research Question

Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?

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
- [~] RQ2: Do typed absence and provenance-preserving protocols detect structural failures missed by ordinary logging and summary-based memory? — **PARTIAL** (v1.0): 44.4% detection on D1-D9 injected faults, 0% FPR, but zero natural violations observed (0/30, CP upper bound 11.6%). Mechanism proven; real-world incidence unknown.
- [~] RQ3: Can history be compacted while preserving grounded return paths to source artifacts? — **PARTIAL** (v1.0): Structural reachability degrades gracefully (0.93→0.25 over 10-90% simulated deletion), backtracking at 80%. Simulated compaction only — genuine LLM compaction untested.

### Active

- [ ] RQ2b: Do natural violations occur at detectable rates on longer/harder real agent tasks?
- [ ] RQ3b: Does structural reachability hold under genuine LLM context-window compaction (not simulated)?
- [ ] RQ4: Do these gains transfer beyond a single recursive runtime into other agent architectures?

### Out of Scope

- Full semantic reachability measurement (content fidelity behind refs) — needs definition work first
- Paper writing — deferred to future milestone after RQ2b/RQ3b resolution

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

### What Is New

v1.0 moved from controlled MockLM to real OpenClaw agent runtime. Key gaps remaining: no naturally-occurring violations observed (may need longer/harder tasks or larger sample); compaction was simulated only (genuine LLM compaction untested due to opaque inner execution layer).

### Target Venue

System first, paper later. No venue targeted for this milestone.

### Computational Environment

Local development environment. Zarathustra/OpenClaw agent runtime. Python-based forge tools.

## Notation and Conventions

See `.gpd/CONVENTIONS.md` for all notation and sign conventions.

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

### Partial (negative findings, honestly documented)

- [~] VIOL-03: Natural violation detection — 0/30, CP upper bound 11.6% (negative finding)
- [~] COMP-01: Real compaction (128K+ tokens) — simulated only, honestly documented

### Active

(None yet — define with `/gpd:new-milestone`)

See `.gpd/milestones/v1.0-REQUIREMENTS.md` for archived v1.0 requirements.

## Key References

- **ref-mock-experiment:** MockLM experiment in primordial repo — forge tools with 103 passing tests (benchmark anchor)

## Constraints

- **Runtime:** Must use existing Zarathustra/OpenClaw agent — not a toy runtime
- **Real compaction:** Tasks must be long enough to trigger genuine context-window compaction
- **Evidence standard:** Self-report from the system is not sufficient evidence (from methodology)

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

---

_Last updated: 2026-03-16 after v1.0 milestone_
