# Research State

## Project Reference

See: .gpd/PROJECT.md (updated 2026-03-16)

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** Planning next research stage

## Current Position

**Current Phase:** --
**Total Phases:** 5 (all complete, v1.0 archived)
**Status:** Milestone v1.0 complete. Ready for `/gpd:new-milestone`.
**Last Activity:** 2026-03-16 — v1.0 milestone archived

**Progress:** [██████████] 100% (v1.0)

## Active Calculations

None (between milestones).

## Intermediate Results

See `.gpd/milestones/v1.0/RESEARCH-DIGEST.md` for complete v1.0 results.

## Open Questions

- Does run_queue.py use session-layer LLM compaction during task execution? (HIGH)
- What is the queue file rotation/deletion policy in production? (MEDIUM)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH)

## Accumulated Context

### Decisions

Full decision log: see `.gpd/milestones/v1.0/RESEARCH-DIGEST.md` and `.gpd/milestones/v1.0-ROADMAP.md`.

### Active Approximations

None (formal systems, no approximations needed).

**Convention Lock:**

- All 18 canonical physics conventions: N/A (formal systems project)

*Custom conventions:*
- Absence State Ontology: 8 states (formalized Phase 1)
- Absence Object Form: Canonical v1 {value: null, state: ...}
- State Transition Legality: 8x8 matrix (45 legal, 19 illegal)
- Provenance Reference Format: parent_id + source_refs
- Artifact ID Format: Colon-separated hierarchical
- Compaction Disambiguation: forge (lossless) vs LLM (lossy); unqualified FORBIDDEN
- Metrics Definitions: reachability_fraction, compression_ratio, vs_vanilla_pct, detection rate, FPR
- Violation Classification: Structural only (D1-D9)
- Hash Integrity: SHA-256 on canonical JSON
- Protocol Versioning: forge.internal.v1 / forge.trace.v1

See `.gpd/CONVENTIONS.md` for full details.

### Blockers/Concerns

None

## Session Continuity

**Last session:** 2026-03-16
**Stopped at:** v1.0 milestone archived. Next: `/gpd:new-milestone`
**Resume file:** —
