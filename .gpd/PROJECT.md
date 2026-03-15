# Primordial Computing: Typed Absence and Provenance in Agentic Systems

## What This Is

A formal systems research project investigating whether typed absence, explicit provenance, and recoverable compaction can prevent silent state loss in long-running autonomous agents. The project has a working prototype (forge tools with 103 passing tests on MockLM) and aims to validate these protocols on a real agent runtime (Zarathustra/OpenClaw) under genuine context pressure.

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

- What specific real tasks constitute a sufficient stress test for compaction?
- Should timed_out and interrupted be distinct absence states?
- Should recoverability be binary or graded?

## Research Questions

### Answered

(None yet — investigate to answer)

### Active

- [ ] RQ1: Can absence be formalized as a useful computational ontology rather than an implementation accident?
- [ ] RQ2: Do typed absence and provenance-preserving protocols detect structural failures missed by ordinary logging and summary-based memory?
- [ ] RQ3: Can history be compacted while preserving grounded return paths to source artifacts?

### Out of Scope

- RQ4: Do these gains transfer beyond a single recursive runtime into other agent architectures? — deferred to future milestone

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

- MockLM experiment: 100% provenance reachability, 6/6 deliberate violations caught, 87% trace compression vs vanilla logger
- 103 passing tests across forge tools
- Null ontology draft v0 with 8 states and initial transition sketch

### What Is New

Moving from controlled MockLM to real LLM-backed agent runtime under genuine context pressure. Testing whether the protocols hold when compaction is forced by real memory constraints rather than simulated.

### Target Venue

System first, paper later. No venue targeted for this milestone.

### Computational Environment

Local development environment. Zarathustra/OpenClaw agent runtime. Python-based forge tools.

## Notation and Conventions

See `.gpd/CONVENTIONS.md` for all notation and sign conventions.

## Unit System

Not applicable (formal systems / software engineering research).

## Requirements

See `.gpd/REQUIREMENTS.md` for the detailed requirements specification.

## Key References

- **ref-mock-experiment:** MockLM experiment in primordial repo — forge tools with 103 passing tests (benchmark anchor)

## Constraints

- **Runtime:** Must use existing Zarathustra/OpenClaw agent — not a toy runtime
- **Real compaction:** Tasks must be long enough to trigger genuine context-window compaction
- **Evidence standard:** Self-report from the system is not sufficient evidence (from methodology)

## Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| Violation detection is primary signal over provenance scores | Real-world reliability matters more than perfect metrics | Guides acceptance criteria |
| Both MockLM and fresh Zarathustra baseline as anchors | Cross-reference between controlled and real conditions | Dual baseline design |
| System first, paper later | Build and validate before writing up | Paper deferred to future milestone |

---

_Last updated: 2025-03-15 after initialization_
