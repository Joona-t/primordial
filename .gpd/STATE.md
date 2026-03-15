# Research State

## Project Reference

See: .gpd/PROJECT.md (updated 2025-03-15)

**Machine-readable scoping contract:** `.gpd/state.json` field `project_contract`

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** Phase 1 -- Ontology Formalization and Verification

## Current Position

**Current Phase:** 1
**Current Phase Name:** Ontology Formalization and Verification
**Total Phases:** 5
**Current Plan:** --
**Total Plans in Phase:** TBD
**Status:** Ready to plan
**Last Activity:** 2025-03-15
**Last Activity Description:** Roadmap created with 5 phases covering 17 requirements

**Progress:** [░░░░░░░░░░] 0%

## Active Calculations

None yet.

## Intermediate Results

None yet.

## Open Questions

- What specific real tasks constitute a sufficient stress test for compaction?
- Should timed_out and interrupted be distinct absence states? (Assigned to Phase 1 FORM-03)
- Should recoverability be binary or graded? (Assigned to Phase 1 FORM-03)
- How does Zarathustra's compaction work internally -- opaque API-level or transparent prompt-level? (HIGH priority, blocks Phase 2 integration strategy)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH priority, blocks Phase 4 analysis)

## Performance Metrics

| Label | Duration | Tasks | Files |
| ----- | -------- | ----- | ----- |
| -     | -        | -     | -     |

## Accumulated Context

### Decisions

None yet.

### Active Approximations

None yet.

**Convention Lock:**

Not applicable -- formal systems research. All metrics are dimensionless ratios or counts.

### Propagated Uncertainties

None yet.

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2 integration risk: Zarathustra's compaction mechanism is uncharacterized. If opaque, forge cannot attach meaningful source_refs, requiring integration redesign.
- Phase 4 is the weakest anchor: MockLM never hit genuine memory limits. Real compaction survival is genuinely open.
- Phase 3 risk: naturally-occurring violations may be rare enough that the test campaign produces a null result.

## Session Continuity

**Last session:** 2025-03-15
**Stopped at:** Roadmap creation complete. Ready to plan Phase 1.
**Resume file:** --
