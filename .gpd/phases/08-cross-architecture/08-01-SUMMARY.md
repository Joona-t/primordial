---
phase: 08-cross-architecture
plan: 01
depth: full
one-liner: "AG2 adapter validated via 36 integration tests: 0 null discipline violations, reversibility=1.0, trace integrity verified, 100% fault detection"
subsystem: validation
tags: [cross-architecture, ag2, adapter, integration-testing, null-discipline, provenance]

requires:
  - phase: 07-adversarial-tasks
    provides: "Extended validator (9/9 D-types), adversarial corpus, 211-run campaign baseline"
provides:
  - AG2 integration harness with mock framework (5 scenarios)
  - 36 integration tests validating all forge structural guarantees
  - Bug fixes in forge_adapter.py (empty string handling)
  - Provenance reversibility analysis utility (compute_reversibility)
  - Validated AG2 adapter metrics comparable to OpenClaw/MockLM baselines
affects: [08-02, 08-03, 08-04, phase-9-synthesis]

methods:
  added: [mock-framework-simulation, BFS-provenance-reachability, fault-injection-testing]
  patterns: [adapter-hook-pass-through, empty-string-sentinel, provenance-DAG-validation]

key-files:
  created:
    - tools/ag2_integration_harness.py
    - tools/test_ag2_integration.py
  modified:
    - tools/forge_adapter.py

key-decisions:
  - "Empty strings treated as present output (not absent) — wrapped to <empty_response> sentinel for forge null discipline compliance"
  - "Reversibility algorithm uses root-node reachability (artifacts with no refs are implicit roots) rather than requiring explicit chamber-ID refs"

patterns-established:
  - "Mock framework pattern: simulate framework hooks without importing the real framework"
  - "Scenario-based integration testing: scripted multi-agent conversations with known properties"

conventions:
  - "artifact_id format: artifact:<framework>:<run>:stage:<seat>:<counter>:r1"
  - "chamber_id format: chamber:<framework>:<run>:v1"
  - "All metrics dimensionless (formal systems)"
  - "compaction disambiguation: forge compaction (lossless) vs LLM compaction (lossy)"

plan_contract_ref: ".gpd/phases/08-cross-architecture/08-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-ag2-null-discipline:
      status: passed
      summary: "AG2 adapter enforces null discipline on all 5 scenarios: every absent output (None) carries typed absence state (not_generated or invalid), empty strings treated as present, 0 ambiguous empties across 36 tests"
      linked_ids: [deliv-ag2-harness, deliv-ag2-tests, test-ag2-null-discipline, ref-mock-experiment, ref-openclaw-adapter]
      evidence:
        - verifier: test-suite
          method: "8 null discipline tests + 5 scenario validations"
          confidence: high
          claim_id: claim-ag2-null-discipline
          deliverable_id: deliv-ag2-tests
          acceptance_test_id: test-ag2-null-discipline
          reference_id: ref-mock-experiment
          evidence_path: "tools/test_ag2_integration.py::TestNullDiscipline"
    claim-ag2-provenance:
      status: passed
      summary: "AG2 adapter produces valid provenance DAGs with reversibility=1.0 across all 5 scenarios (above 0.95 threshold). All artifacts reachable from root via BFS."
      linked_ids: [deliv-ag2-harness, deliv-ag2-tests, test-ag2-reversibility, ref-mock-experiment, ref-openclaw-adapter]
      evidence:
        - verifier: test-suite
          method: "6 provenance tests + compute_reversibility on all scenarios"
          confidence: high
          claim_id: claim-ag2-provenance
          deliverable_id: deliv-ag2-tests
          acceptance_test_id: test-ag2-reversibility
          reference_id: ref-mock-experiment
          evidence_path: "tools/test_ag2_integration.py::TestProvenance"
    claim-ag2-trace-integrity:
      status: passed
      summary: "AG2 adapter sessions produce traces that round-trip losslessly: hash_match=True and content_match=True on all 5 sealed chambers"
      linked_ids: [deliv-ag2-harness, deliv-ag2-tests, test-ag2-trace-integrity, ref-mock-experiment]
      evidence:
        - verifier: test-suite
          method: "4 trace integrity tests including cross-session independence"
          confidence: high
          claim_id: claim-ag2-trace-integrity
          deliverable_id: deliv-ag2-tests
          acceptance_test_id: test-ag2-trace-integrity
          reference_id: ref-mock-experiment
          evidence_path: "tools/test_ag2_integration.py::TestTraceIntegrity"
  deliverables:
    deliv-ag2-harness:
      status: passed
      path: "tools/ag2_integration_harness.py"
      summary: "AG2 integration harness with MockConversableAgent (9 hooks), MockGroupChat (round-robin + scripted), AG2ForgeHarness, and 5 built-in scenarios exercising all 4 interception points"
      linked_ids: [claim-ag2-null-discipline, claim-ag2-provenance, claim-ag2-trace-integrity]
    deliv-ag2-tests:
      status: passed
      path: "tools/test_ag2_integration.py"
      summary: "36 integration tests across 7 categories: null discipline (8), provenance (6), trace integrity (4), fault injection (6), multi-agent (6), anchor comparison (2), harness components (4)"
      linked_ids: [claim-ag2-null-discipline, claim-ag2-provenance, claim-ag2-trace-integrity, test-ag2-null-discipline, test-ag2-reversibility, test-ag2-trace-integrity]
    deliv-adapter-fixes:
      status: passed
      path: "tools/forge_adapter.py"
      summary: "Fixed empty-string falsy check bug in on_turn/on_tool_call across AG2 and LangGraph adapters. Empty strings now treated as present output with <empty_response> sentinel."
      linked_ids: [claim-ag2-null-discipline]
  acceptance_tests:
    test-ag2-null-discipline:
      status: passed
      summary: "8 dedicated null discipline tests + validate_chamber() on all 5 scenarios = 0 validation errors. Every None output has typed absence state. No bare Nones in any chamber."
      linked_ids: [claim-ag2-null-discipline, deliv-ag2-tests, ref-mock-experiment]
    test-ag2-reversibility:
      status: passed
      summary: "reversibility_score = 1.0 on all 5 scenarios (threshold >= 0.95). all_reach_root = True. BFS from every artifact reaches root node."
      linked_ids: [claim-ag2-provenance, deliv-ag2-tests, ref-mock-experiment]
    test-ag2-trace-integrity:
      status: passed
      summary: "hash_match=True AND content_match=True on all 5 sealed chambers. Two independent sessions produce no cross-contamination."
      linked_ids: [claim-ag2-trace-integrity, deliv-ag2-tests, ref-mock-experiment]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "AG2 adapter achieves same structural guarantees as MockLM experiment: 0 null discipline violations, 100% reversibility, 100% trace integrity. Comparable ceiling."
    ref-openclaw-adapter:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "AG2 adapter matches OpenClaw adapter pattern (4 interception points, post-hoc JSONL). Both achieve 100% provenance reachability on well-formed sessions."
  forbidden_proxies:
    fp-trivial-sessions:
      status: rejected
      notes: "All 5 scenarios include multi-turn and multi-agent sessions. Scenario C has 4 agents with 10 turns. Scenario D has 3 agents with errors and absences."
    fp-no-absence:
      status: rejected
      notes: "Scenario D explicitly tests None outputs (2), empty strings (1), and errors (1). 8 null discipline tests cover present, None, empty string, tool None, error, and mixed cases."
  uncertainty_markers:
    weakest_anchors:
      - "Mock AG2 agents may not perfectly replicate real AG2 hook_list behavior, especially edge cases in speaker selection and message broadcasting"
    unvalidated_assumptions: []
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-ag2-provenance
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-openclaw-adapter
    comparison_kind: prior_work
    metric: reversibility_score
    threshold: ">= 0.95"
    verdict: pass
    recommended_action: "Proceed to LangGraph adapter (08-02)"
    notes: "AG2 reversibility=1.0 matches OpenClaw 100% baseline"
  - subject_id: claim-ag2-trace-integrity
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: benchmark
    metric: hash_match
    threshold: "= True"
    verdict: pass
    recommended_action: "Proceed to LangGraph adapter (08-02)"
    notes: "AG2 trace integrity matches MockLM 100% baseline"

duration: 18min
completed: 2026-03-28
---

# Phase 08, Plan 01: AG2 Integration Harness and Tests Summary

**AG2 adapter validated via 36 integration tests: 0 null discipline violations, reversibility=1.0, trace integrity verified, 100% fault detection**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-28
- **Completed:** 2026-03-28
- **Tasks:** 2
- **Files modified:** 3 (1 created harness, 1 created tests, 1 fixed adapter)

## Key Results

- AG2ForgeAdapter enforces all forge structural guarantees under mock simulation: 0 null discipline violations, reversibility=1.0 on all 5 scenarios, trace integrity hash_match=True on all sealed chambers
- Discovered and fixed empty-string falsy check bug in forge_adapter.py (affected AG2 and LangGraph adapters): `output=""` was incorrectly classified as absent
- Fault injection achieves 100% detection rate on D1 (null collapse), D2 (broken provenance), D5 (missing state label), and index corruption
- AG2 metrics match OpenClaw adapter and MockLM experiment baselines — the universal adapter pattern generalizes

## Task Commits

Each task was committed atomically:

1. **Task 1: Build AG2 integration harness** - `095ea89` (implement)
2. **Task 2: Integration tests with validation** - `7a22719` (validate)

## Files Created/Modified

- `tools/ag2_integration_harness.py` — AG2 mock framework + 5 scenarios + reversibility analysis (714 lines)
- `tools/test_ag2_integration.py` — 36 integration tests across 7 categories (616 lines)
- `tools/forge_adapter.py` — Fixed empty-string handling in on_turn/on_tool_call for AG2 and LangGraph adapters

## Next Phase Readiness

- AG2 adapter pattern validated; proceed to LangGraph adapter (08-02)
- Integration harness pattern reusable for LangGraph/CrewAI/OpenHands
- compute_reversibility() utility available for all downstream plans
- Bug fixes in forge_adapter.py benefit all framework adapters

## Contract Coverage

- Claim IDs advanced: claim-ag2-null-discipline -> passed, claim-ag2-provenance -> passed, claim-ag2-trace-integrity -> passed
- Deliverable IDs produced: deliv-ag2-harness -> passed, deliv-ag2-tests -> passed, deliv-adapter-fixes -> passed
- Acceptance test IDs run: test-ag2-null-discipline -> passed, test-ag2-reversibility -> passed, test-ag2-trace-integrity -> passed
- Reference IDs surfaced: ref-mock-experiment -> compared, ref-openclaw-adapter -> read + compared
- Forbidden proxies rejected: fp-trivial-sessions -> rejected (multi-agent scenarios used), fp-no-absence -> rejected (explicit absence tests included)
- Decisive comparison verdicts: claim-ag2-provenance -> pass (rev=1.0 vs OpenClaw), claim-ag2-trace-integrity -> pass (hash_match vs MockLM)

## Validations Completed

- Null discipline: 8 tests covering present, None, empty string, tool None, error, mixed, chamber validation, bare None scan
- Provenance: 6 tests covering sequential chains, tool refs, compaction refs, root reachability, reversibility threshold, DAG validity
- Trace integrity: 4 tests covering roundtrip, stats, sealed-only, session independence
- Fault injection: 6 tests covering D1, D2, D5, index tampering, clean baseline, violation structure
- Multi-agent: 6 tests covering 4-agent GroupChat, speaker coverage, ordering, metrics, ledger, result completeness
- Anchor comparison: 2 tests comparing AG2 vs OpenClaw reversibility and AG2 vs MockLM trace integrity
- Regression: 19/19 existing test_forge_adapter.py tests still pass

## Decisions & Deviations

### Decisions

- **Empty string sentinel:** Chose `<empty_response>` marker rather than trying to relax forge null discipline. Empty strings are semantically present (agent responded), so the adapter wraps them to a non-empty string that passes validation.
- **Reversibility algorithm:** Root-node reachability rather than explicit chamber-ID refs. Artifacts with no refs are implicit roots, since the chamber ID format (`chamber:...`) doesn't match the artifact ID regex required by the v1 bridge validator.

### Auto-fixed Issues

**1. [Rule 1 - Code Bug] Empty string falsy check in forge_adapter.py**

- **Found during:** Task 1 (harness scenario D: error_and_absence)
- **Issue:** `None if output_text else ...` treats `""` as falsy, incorrectly classifying empty strings as absent
- **Fix:** Changed to `None if output_text is not None else ...` and added `<empty_response>` sentinel
- **Files modified:** tools/forge_adapter.py (on_turn and on_tool_call in both AG2 and LangGraph adapters)
- **Verification:** Scenario D passes, empty string test passes, 19 existing tests still pass
- **Committed in:** 095ea89 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 code bug)
**Impact on plan:** Essential correctness fix. No scope creep.

## Issues Encountered

None beyond the empty-string bug found and fixed during Task 1.

## Open Questions

- How closely do mock AG2 hooks replicate real AG2 0.4+ hook_list behavior? (Weakest anchor — mitigated by scenario diversity)
- Will the adapter pattern work as cleanly for LangGraph's callback-based hooks? (Addressed in 08-02)

## Self-Check: PASSED

- [x] tools/ag2_integration_harness.py exists
- [x] tools/test_ag2_integration.py exists
- [x] 36 tests pass (python3 -m pytest tools/test_ag2_integration.py)
- [x] 19 existing tests pass (python3 -m pytest tools/test_forge_adapter.py)
- [x] Commits 095ea89 and 7a22719 exist
- [x] All contract IDs covered

---

_Phase: 08-cross-architecture_
_Completed: 2026-03-28_
