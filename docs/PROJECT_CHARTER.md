# Project Charter — Primordial Computing

## Working title
**Primordial Computing: Zero as Structured Capacity in Agentic Systems**

## Problem

Modern agentic systems routinely collapse meaningful kinds of absence into generic null-like states or summary text. This makes long-horizon computation harder to audit, harder to recover, and more vulnerable to silent corruption.

Common failures include:
- unknown vs missing being collapsed
- deletion vs pruning being conflated
- unresolved work appearing complete
- summaries replacing evidence without preserving lineage
- recursive outputs becoming detached from their provenance

## Thesis

The central claim of this project is:

> Agent systems become more reliable when absence, lineage, and compaction are treated as protocol-governed computational objects rather than incidental metadata.

This thesis has three concrete subclaims:

1. **Typed absence** improves truthfulness of system state representation.
2. **Explicit provenance** improves reconstructability and auditability.
3. **Recoverable compaction** improves long-horizon tractability without collapsing into semantic amnesia.

## Research questions

### RQ1 — Ontology
Can absence be formalized as a useful computational ontology rather than an implementation accident?

### RQ2 — Reliability
Do typed absence and provenance-preserving protocols detect structural failures missed by ordinary logging and summary-based memory?

### RQ3 — Compaction
Can history be compacted while preserving grounded return paths to source artifacts?

### RQ4 — Generality
Do these gains transfer beyond a single recursive runtime into other agent architectures?

## Hypothesis

> Systems that represent absence and transformation explicitly will outperform summary-only and flat-log baselines on structural reliability metrics such as fault detection, provenance reachability, corruption detection, and post-compaction recoverability.

## Deliverables

1. A philosophical foundations memo
2. A formal null ontology / state-transition specification
3. A reference implementation in a real agent runtime
4. A benchmark/evaluation harness
5. A paper-style report

## Non-goals

This project does **not** initially aim to solve:
- general semantic truth in AI systems
- full epistemology of model outputs
- all memory/retrieval problems
- fully autonomous scientific reasoning

It is narrower: a protocol and ontology project aimed at improving the structure of agentic computation.

## Falsifiers

The thesis weakens if:
- typed absence adds complexity without measurable reliability gains
- provenance chains fail under realistic recursive or compacted workloads
- compaction grounding proves too brittle to preserve meaningful return paths
- benefits do not generalize beyond a single toy runtime

## First milestone

**Milestone 0 — Foundations + protocol specification**

Ship:
- foundational memo
- null ontology draft
- state transition matrix
- initial methodology

Before expanding implementation complexity.
