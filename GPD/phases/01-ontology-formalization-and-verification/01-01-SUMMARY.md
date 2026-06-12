---
phase: 01-ontology-formalization-and-verification
plan: 01
depth: full
one-liner: "Formalized 8-state absence ontology with complete 64-entry transition table, validate_transition() function, and resolved all FORM-03 design questions"
subsystem: [formalism, validation]
tags: [state-machine, transition-table, absence-ontology, typed-absence, finite-state-machine]

requires: []
provides:
  - Complete 8x8 transition table (TRANSITION_TABLE) in forge_nulls.py
  - validate_transition(from_state, to_state) function in forge_nulls.py
  - Reconciled absence state documentation (PROJECT.md, CONVENTIONS.md)
  - FORM-03 design decisions (timed_out/interrupted, binary recoverability)
  - Human-readable transition table documentation (docs/transition-table.md)
affects: [02-property-based-testing, 03-instrumentation, 04-compaction-survival]

methods:
  added: [exhaustive-enumeration, structural-rules-derivation]
  patterns: [initial-terminal-default transition classification]

key-files:
  created:
    - docs/transition-table.md
  modified:
    - tools/forge_nulls.py
    - GPD/PROJECT.md
    - GPD/CONVENTIONS.md

key-decisions:
  - "CC-001: resolved is a REF state, not an absence state; not_generated is the correct 8th absence state"
  - "CC-002: timed_out/interrupted NOT added as distinct states; use metadata enrichment"
  - "CC-003: recoverability stays binary; graded deferred to Phase 4"
  - "Transition table built from 3 structural rules: initial (no incoming), terminal (no outgoing), self (always legal)"

patterns-established:
  - "Three-rule transition generation: initial states, terminal states, self-transitions determine the full table"
  - "Metadata enrichment over state expansion: reason field captures timeout/interrupt/etc without new states"
  - "Single source of truth: code data structure (TRANSITION_TABLE) is authoritative; docs mirror it"

conventions:
  - "8 canonical absence states: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable"
  - "resolved/unresolved are REF states (source_ref link status), NOT absence states"
  - "Initial states: not_invoked, not_generated (no incoming transitions)"
  - "Terminal state: deleted (no outgoing transitions)"
  - "Self-transitions: always legal (idempotent)"

plan_contract_ref: "GPD/phases/01-ontology-formalization-and-verification/01-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-ontology-complete:
      status: passed
      summary: "All 8 absence states have formal definitions. Complete 64-entry transition table classifies every (source, target) pair with no gaps or placeholders. 45 legal, 19 illegal."
      linked_ids: [deliv-transition-table, deliv-validate-transition, test-table-completeness, test-regression-103, test-known-illegal, ref-forge-nulls, ref-103-tests]
      evidence:
        - verifier: self-check
          method: exhaustive enumeration and regression testing
          confidence: high
          claim_id: claim-ontology-complete
          deliverable_id: deliv-transition-table
          acceptance_test_id: test-table-completeness
          reference_id: ref-forge-nulls
          evidence_path: "tools/forge_nulls.py"
    claim-open-questions-resolved:
      status: passed
      summary: "Both FORM-03 questions resolved with documented rationale. Q1: timed_out/interrupted not added (metadata enrichment). Q2: binary recoverability kept for Phase 1."
      linked_ids: [deliv-form03-resolution, test-form03-rationale, ref-forge-nulls]
      evidence:
        - verifier: self-check
          method: design analysis with transition rule comparison
          confidence: high
          claim_id: claim-open-questions-resolved
          deliverable_id: deliv-form03-resolution
          acceptance_test_id: test-form03-rationale
          reference_id: ref-forge-nulls
          evidence_path: "docs/transition-table.md"
    claim-discrepancy-resolved:
      status: passed
      summary: "PROJECT.md updated: resolved removed from absence state list, not_generated added. Semantic distinction documented: absence states vs ref states are orthogonal."
      linked_ids: [deliv-doc-fix, test-doc-consistency, ref-forge-nulls, ref-conventions]
      evidence:
        - verifier: self-check
          method: automated consistency check across 3 sources
          confidence: high
          claim_id: claim-discrepancy-resolved
          deliverable_id: deliv-doc-fix
          acceptance_test_id: test-doc-consistency
          reference_id: ref-conventions
          evidence_path: "GPD/PROJECT.md"
  deliverables:
    deliv-transition-table:
      status: passed
      path: "tools/forge_nulls.py"
      summary: "TRANSITION_TABLE dict with 64 entries classifying all (source, target) pairs. Built by _build_transition_table() from 3 structural rules."
      linked_ids: [claim-ontology-complete, test-table-completeness]
    deliv-validate-transition:
      status: passed
      path: "tools/forge_nulls.py"
      summary: "validate_transition(from_state, to_state) -> bool. Returns True/False for legal/illegal. Raises ValueError for invalid states."
      linked_ids: [claim-ontology-complete, test-known-illegal]
    deliv-doc-fix:
      status: passed
      path: "GPD/PROJECT.md"
      summary: "PROJECT.md lists correct 8 absence states matching V1_ABSENCE_STATES. Semantic distinction between absence states and ref states documented."
      linked_ids: [claim-discrepancy-resolved, test-doc-consistency]
    deliv-form03-resolution:
      status: passed
      path: "docs/transition-table.md"
      summary: "Design Decisions section with both FORM-03 questions addressed: question, evidence, DECIDED statement, consequences, revisit criteria."
      linked_ids: [claim-open-questions-resolved, test-form03-rationale]
    deliv-human-readable-table:
      status: passed
      path: "docs/transition-table.md"
      summary: "8x8 grid with L/X markings, legend, state definitions, illegal transition categories, example scenarios."
      linked_ids: [claim-ontology-complete]
  acceptance_tests:
    test-table-completeness:
      status: passed
      summary: "len(TRANSITION_TABLE) == 64 verified. All 8x8 pairs present with no TBD or placeholder entries."
      linked_ids: [claim-ontology-complete, deliv-transition-table]
    test-regression-103:
      status: passed
      summary: "All 103 tests pass with zero failures, zero errors (6 deprecation warnings as expected)."
      linked_ids: [claim-ontology-complete, ref-103-tests]
    test-known-illegal:
      status: passed
      summary: "validate_transition correctly rejects: deleted->unknown (False), unknown->not_invoked (False), withheld->not_generated (False). Correctly accepts: unknown->unknown (True). ValueError raised for resolved->unknown."
      linked_ids: [claim-ontology-complete, deliv-validate-transition]
    test-doc-consistency:
      status: passed
      summary: "forge_nulls.py, PROJECT.md, CONVENTIONS.md all list exactly: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable."
      linked_ids: [claim-discrepancy-resolved, deliv-doc-fix]
    test-form03-rationale:
      status: passed
      summary: "docs/transition-table.md contains Design Decisions section with both questions: (1) question, (2) evidence, (3) DECIDED statement, (4) consequences, (5) revisit criteria."
      linked_ids: [claim-open-questions-resolved, deliv-form03-resolution]
  references:
    ref-forge-nulls:
      status: completed
      completed_actions: [read, use]
      missing_actions: []
      summary: "V1_ABSENCE_STATES read as ground truth. Extended with TRANSITION_TABLE and validate_transition(). Existing functions unchanged."
    ref-103-tests:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "All 103 tests verified passing before, during, and after changes. No regressions introduced."
    ref-conventions:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "Known discrepancy documented in CONVENTIONS.md read and resolved. Convention changes CC-001, CC-002, CC-003 recorded."
  forbidden_proxies:
    fp-doc-only-table:
      status: rejected
      notes: "TRANSITION_TABLE is a machine-readable dict in forge_nulls.py. docs/transition-table.md is explicitly marked as a mirror, not the source of truth."
    fp-partial-table:
      status: rejected
      notes: "64 entries with no TBD or placeholder classifications. Every entry is explicitly True or False."
    fp-resolved-as-absence:
      status: rejected
      notes: "resolved NOT added to V1_ABSENCE_STATES. Documentation fixed to match implementation instead."
  uncertainty_markers:
    weakest_anchors:
      - "Transition classifications for ambiguous pairs rely on design judgment (e.g., withheld->unknown is legal because information can degrade)"
    unvalidated_assumptions:
      - "The three structural rules (initial/terminal/self) correctly capture all constraints -- no domain-specific exceptions were found but Hypothesis testing (Plan 02) will stress-test this"
    competing_explanations: []
    disconfirming_observations: []

duration: 5min
completed: 2026-03-15
---

# Phase 1, Plan 01: Ontology Formalization Summary

**Formalized 8-state absence ontology with complete 64-entry transition table, validate_transition() function, and resolved all FORM-03 design questions**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T21:18:00Z
- **Completed:** 2026-03-15T21:23:18Z
- **Tasks:** 3
- **Files modified:** 4

## Key Results

- Complete 8x8 transition table: 45 legal transitions, 19 illegal transitions, 64 total entries with no gaps
- `validate_transition()` correctly accepts legal transitions, rejects illegal ones, raises ValueError for non-existent states
- Documentation discrepancy resolved: `resolved` removed from absence state list, `not_generated` confirmed as correct 8th state
- FORM-03 decisions: neither `timed_out`/`interrupted` nor graded recoverability added for Phase 1 [CONFIDENCE: HIGH]

## Task Commits

Each task was committed atomically:

1. **Task 1: Reconcile resolved/not_generated discrepancy** - `904d65b` (docs)
2. **Task 2: Design and implement 8x8 transition table** - `7a435f2` (implement)
3. **Task 3: Resolve FORM-03 open questions** - `8975287` (docs)

## Files Created/Modified

- `tools/forge_nulls.py` - Added TRANSITION_TABLE (64-entry dict), validate_transition(), _INITIAL_STATES, _TERMINAL_STATES, _build_transition_table()
- `docs/transition-table.md` - Created: human-readable 8x8 grid, state definitions, illegal categories, example scenarios, FORM-03 design decisions
- `GPD/PROJECT.md` - Fixed absence state list (resolved -> not_generated), added ref state distinction note
- `GPD/CONVENTIONS.md` - Marked discrepancy and open questions as RESOLVED, added CC-001/CC-002/CC-003 convention changes

## Next Phase Readiness

- TRANSITION_TABLE and validate_transition() are ready for Hypothesis RuleBasedStateMachine testing (Plan 02)
- All 103 existing tests pass as regression anchor
- State definitions and transition rules are documented for downstream phases
- The transition table can be extended if Phase 4 compaction evidence warrants new states

## Contract Coverage

- Claim IDs advanced: claim-ontology-complete -> passed, claim-open-questions-resolved -> passed, claim-discrepancy-resolved -> passed
- Deliverable IDs produced: deliv-transition-table -> tools/forge_nulls.py, deliv-validate-transition -> tools/forge_nulls.py, deliv-doc-fix -> GPD/PROJECT.md, deliv-form03-resolution -> docs/transition-table.md, deliv-human-readable-table -> docs/transition-table.md
- Acceptance test IDs run: test-table-completeness -> passed, test-regression-103 -> passed, test-known-illegal -> passed, test-doc-consistency -> passed, test-form03-rationale -> passed
- Reference IDs surfaced: ref-forge-nulls -> read, use; ref-103-tests -> read, compare; ref-conventions -> read
- Forbidden proxies rejected: fp-doc-only-table -> rejected, fp-partial-table -> rejected, fp-resolved-as-absence -> rejected

## Validations Completed

- Table completeness: `len(TRANSITION_TABLE) == 64` verified
- Known-illegal transitions: `deleted->unknown` (False), `unknown->not_invoked` (False), `withheld->not_generated` (False) all correctly rejected
- Self-transitions: `unknown->unknown` (True) correctly accepted
- Invalid state handling: `resolved->unknown` raises ValueError
- Terminal state: `deleted` row has exactly 1 legal entry (self)
- Initial states: `not_invoked` and `not_generated` columns each have exactly 1 legal entry (self)
- Cross-source consistency: forge_nulls.py, PROJECT.md, CONVENTIONS.md all list identical 8 states
- Regression: all 103 existing tests pass (verified 3 times: after Task 1, Task 2, Task 3)

## Decisions Made

1. **CC-001:** `resolved` is a REF state (source_ref link status), not an absence state. PROJECT.md fixed to list `not_generated` instead.
2. **CC-002:** `timed_out`/`interrupted` NOT added as distinct absence states. Use metadata: `{state: "unresolved", reason: "timed_out"}`. Rationale: identical transition rules to existing states; adding 2 states would expand table from 64 to 100 entries with no new information.
3. **CC-003:** Recoverability stays binary (`pruned_recoverable` vs `deleted`). Graded recoverability deferred to Phase 4 when actual LLM compaction data exists.
4. **Transition table design:** Three structural rules (initial, terminal, self-transition) plus default-legal generate all 64 entries. This is manifestly complete and consistent.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Open Questions

- Will Hypothesis stateful testing (Plan 02) find any transition sequence that violates the structural invariants? The table was designed to be consistent but adversarial testing may reveal edge cases.
- Are there agent lifecycle scenarios that cannot be represented by the 8 states plus metadata? The uncertainty marker from the contract remains: if evidence surfaces in later phases, the ontology must expand.

## Self-Check: PASSED

- [x] tools/forge_nulls.py exists and contains TRANSITION_TABLE (64 entries) and validate_transition()
- [x] docs/transition-table.md exists with 8x8 grid and FORM-03 decisions
- [x] GPD/PROJECT.md lists correct 8 states
- [x] GPD/CONVENTIONS.md discrepancy and open questions marked RESOLVED
- [x] All 103 tests pass (verified after each task)
- [x] Commits 904d65b, 7a435f2, 8975287 exist in git log
- [x] No existing forge_nulls.py functions modified (only additions)
- [x] Convention changes CC-001, CC-002, CC-003 recorded
- [x] Contract coverage: all claim, deliverable, acceptance test, reference, and forbidden proxy IDs accounted for

---

_Phase: 01-ontology-formalization-and-verification_
_Completed: 2026-03-15_
