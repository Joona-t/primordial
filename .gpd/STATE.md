# Research State

## Project Reference

See: .gpd/PROJECT.md

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** Phase 1 complete. Ready to plan Phase 2.

## Current Position

**Current Phase:** 1 (complete)
**Current Phase Name:** Ontology Formalization and Verification
**Total Phases:** 5
**Current Plan:** 2/2 (all complete)
**Total Plans in Phase:** 2
**Status:** Phase 1 complete
**Last Activity:** 2026-03-16 — Phase 1 execution complete (all plans passed)

**Progress:** [██░░░░░░░░] 20%

## Active Calculations

None (Phase 1 complete, Phase 2 not started).

## Intermediate Results

- **TRANSITION_TABLE:** 64 entries (45 legal, 19 illegal) — tools/forge_nulls.py
- **validate_transition():** function returning bool, ValueError for invalid states — tools/forge_nulls.py
- **Hypothesis verification:** 10K examples x 30 steps = 300K transitions, 0 invariant violations
- **Mutation score:** 99.0% adjusted (103/110 killed, 6 equivalent, 1 low-value)
- **Total test count:** 301 (103 existing + 198 new)

## Open Questions

- What specific real tasks constitute a sufficient stress test for compaction?
- How does Zarathustra's compaction work internally -- opaque API-level or transparent prompt-level? (HIGH, blocks Phase 2)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH, blocks Phase 4)

## Performance Metrics

| Label | Duration | Tasks | Files |
| ----- | -------- | ----- | ----- |
| Plan 01-01 | ~5 min | 3 | 4 |
| Plan 01-02 | ~20 min | 3 | 7 |

## Accumulated Context

### Decisions

- **CC-001:** resolved is a REF state, not an absence state; not_generated is the correct 8th absence state (Phase 1 Plan 01 Task 1)
- **CC-002:** timed_out/interrupted NOT added as distinct absence states — identical transition rules to existing states; metadata enrichment sufficient (Phase 1 Plan 01 Task 3)
- **CC-003:** Recoverability stays binary for Phase 1 — does not change transition rules; no empirical compaction data yet; YAGNI (Phase 1 Plan 01 Task 3)
- **CC-004:** Custom AST mutation testing over mutmut (Python 3.14 incompatibility) (Phase 1 Plan 02 Task 3)

### Active Approximations

None (formal systems, no approximations needed).

**Convention Lock:**

- Metric signature: N/A
- Fourier convention: N/A
- Natural units: N/A
- Gauge choice: N/A
- Regularization scheme: N/A
- Renormalization scheme: N/A
- Coordinate system: N/A
- Spin basis: N/A
- State normalization: N/A
- Coupling convention: N/A
- Index positioning: N/A
- Time ordering: N/A
- Commutation convention: N/A
- Levi-Civita sign: N/A
- Generator normalization: N/A
- Covariant derivative sign: N/A
- Gamma matrix convention: N/A
- Creation/annihilation order: N/A

*Custom conventions:*
- Absence State Ontology: 8 states: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable. Deprecated alias: pruned -> pruned_recoverable. FORMALIZED in Phase 1 FORM-01.
- Absence Object Form: Canonical v1: {value: null, state: <AbsenceState>}. Legacy ingress: {value: null, absence_state: <AbsenceState>} accepted and normalized. Sibling pattern: {field: null, field_state: <AbsenceState>}.
- State Transition Legality: 8x8 matrix (64 entries). 45 legal, 19 illegal. TRANSITION_TABLE in forge_nulls.py is source of truth. validate_transition() enforces. Initial states (not_invoked, not_generated) have no incoming. Terminal state (deleted) has no outgoing. Self-transitions always legal.
- Provenance Reference Format: Lightweight parent_id + source_refs list. Not full W3C PROV. Empty refs valid. Unresolvable ref = REF.REF_UNRESOLVED error.
- Artifact Id Format: Colon-separated hierarchical. Artifacts: artifact:<run>:stage:<seat>:<revision>. Chambers: chamber:<seg1>:<seg2>[:<segN>]. Regex validated.
- Compaction Disambiguation: TWO meanings, always qualified. Forge compaction = lossless hash-verified dedup. LLM compaction = lossy semantic summarization. Unqualified 'compaction' FORBIDDEN.
- Metrics Definitions: reachability_fraction=(reachable/total via BFS). compression_ratio=original/encoded. vs_vanilla_pct=(forge-vanilla)/vanilla*100. All dimensionless. MockLM anchors: reach=1.0, detect=6/6, compress=87%.
- Violation Classification: Structural only: illegal state transitions or missing metadata. NOT hallucination, NOT fault, NOT semantic error. Fault taxonomy D1-D9.
- Unit System Project: N/A -- formal systems research. All metrics dimensionless ratios or counts. No physical units.
- Hash Integrity: SHA-256 on canonical JSON: json.dumps(obj, sort_keys=True, ensure_ascii=True). Round-trip verification for forge trace compression.
- Protocol Versioning: schema_version=forge.internal.v1 (chambers/artifacts). encoding=forge.trace.v1 (trace codec). Legacy pre-v1 accepted at ingress, normalized.

### Propagated Uncertainties

None yet.

### Pending Todos

None yet.

### Blockers/Concerns

None

## Session Continuity

**Last session:** 2026-03-16
**Stopped at:** Phase 1 complete. Ready to plan Phase 2.
**Resume file:** —
