---
phase: 01-ontology-formalization-and-verification
plan: 02
depth: full
one-liner: "Adversarial property-based testing (10K+ Hypothesis sequences) and mutation testing (99% adjusted score) confirm transition table correctness and test suite quality"
subsystem: [validation, formalism]
tags: [hypothesis, property-based-testing, mutation-testing, state-machine, adversarial-testing]

requires:
  - phase: 01-ontology-formalization-and-verification
    plan: 01
    provides: [TRANSITION_TABLE, validate_transition, 8-state absence ontology]
provides:
  - Hypothesis RuleBasedStateMachine verification (10K+ adversarial sequences, 0 violations)
  - Parametrized negative tests for all 19 illegal transitions
  - Structural invariant tests (completeness, terminal, initial, self-transitions, connectivity)
  - Mutation testing confirmation (99% adjusted score, all survivors classified)
  - Gap-closure tests targeting 18 initially surviving mutants
affects: [03-instrumentation, 04-compaction-survival]

methods:
  added: [property-based-testing, rule-based-state-machine, mutation-testing, ast-based-mutation]
  patterns: [adversarial-exploration-then-mutation-verification, gap-closure-iteration]

key-files:
  created:
    - tools/test_forge_ontology.py
    - tools/run_mutation_tests.py
    - tools/conftest.py
    - docs/mutation-report.md
    - docs/mutation-results.json
    - setup.cfg
  modified: []

key-decisions:
  - "Used custom AST-based mutation testing instead of mutmut (both v2 and v3 incompatible with Python 3.14)"
  - "Hypothesis StateMachine tests skipped during mutation testing (too slow for per-mutant execution; parametrized tests sufficient for mutation killing)"
  - "7 surviving mutants classified: 6 equivalent (__main__ block), 1 low-value (warning side-effect)"

patterns-established:
  - "Two-round mutation testing: initial run identifies gaps, gap-closure tests kill survivors, re-run confirms"
  - "Equivalent mutant identification: __main__ blocks, try/except-guarded KeyError paths, warning-only changes"

conventions:
  - "8 canonical absence states: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable"
  - "Transition table: 45 legal, 19 illegal, 64 total entries"

plan_contract_ref: ".gpd/phases/01-ontology-formalization-and-verification/01-02-PLAN.md#/contract"
contract_results:
  claims:
    claim-adversarial-verified:
      status: passed
      summary: "Hypothesis RuleBasedStateMachine generated 10K+ adversarial transition sequences (30 steps each, ~300K transition attempts) without discovering any invariant violation. All 19 illegal transitions parametrized and correctly rejected."
      linked_ids: [deliv-hypothesis-tests, test-10k-sequences, test-negative-transitions, ref-forge-nulls-updated, ref-103-tests, ref-transition-table]
      evidence:
        - verifier: self-check
          method: Hypothesis property-based testing + parametrized negative tests
          confidence: high
          claim_id: claim-adversarial-verified
          deliverable_id: deliv-hypothesis-tests
          acceptance_test_id: test-10k-sequences
          reference_id: ref-forge-nulls-updated
          evidence_path: "tools/test_forge_ontology.py"
    claim-mutation-adequate:
      status: passed
      summary: "Mutation testing on forge_nulls.py achieves 99.0% adjusted mutation score (103 killed / 104 non-equivalent out of 110 total). All 7 survivors manually classified as equivalent (6) or low-value (1)."
      linked_ids: [deliv-mutation-report, test-mutation-score, ref-103-tests, ref-forge-nulls-updated]
      evidence:
        - verifier: self-check
          method: AST-based mutation testing with 5 operators (110 mutants)
          confidence: high
          claim_id: claim-mutation-adequate
          deliverable_id: deliv-mutation-report
          acceptance_test_id: test-mutation-score
          reference_id: ref-forge-nulls-updated
          evidence_path: "docs/mutation-report.md"
  deliverables:
    deliv-hypothesis-tests:
      status: passed
      path: "tools/test_forge_ontology.py"
      summary: "198 tests: 2 RuleBasedStateMachine classes (10K/5K examples), 19 illegal + 45 legal parametrized transition tests, 12 structural invariants, 7 invalid state tests, 64 table-vs-function tests, 42 gap-closure tests, 7 validation tests"
      linked_ids: [claim-adversarial-verified, test-10k-sequences, test-negative-transitions]
    deliv-mutation-report:
      status: passed
      path: "docs/mutation-report.md"
      summary: "Complete mutation testing report with 110 mutants, 103 killed, 7 survivors classified, adjusted score 99.0%, two-round gap-closure history"
      linked_ids: [claim-mutation-adequate, test-mutation-score]
  acceptance_tests:
    test-10k-sequences:
      status: passed
      summary: "AbsenceStateMachine ran 10000 examples x 30 steps = ~300K transition attempts. 5 invariants checked after every step. Zero violations found. Completed in ~41 seconds."
      linked_ids: [claim-adversarial-verified, deliv-hypothesis-tests, ref-forge-nulls-updated]
    test-negative-transitions:
      status: passed
      summary: "All 19 illegal transitions parametrized and correctly rejected by validate_transition(). 45 legal transitions parametrized and correctly accepted."
      linked_ids: [claim-adversarial-verified, deliv-hypothesis-tests, ref-transition-table]
    test-mutation-score:
      status: passed
      summary: "110 mutants generated, 103 killed, 7 survived (6 equivalent + 1 low-value). Adjusted score 99.0% > 85% threshold."
      linked_ids: [claim-mutation-adequate, deliv-mutation-report, ref-103-tests]
  references:
    ref-forge-nulls-updated:
      status: completed
      completed_actions: [read, use]
      missing_actions: []
      summary: "TRANSITION_TABLE and validate_transition() tested adversarially (10K+ sequences, 110 mutations). Code unchanged by this plan."
    ref-103-tests:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "All 103 existing tests pass alongside 198 new tests (301 total). Verified before, during, and after all changes."
    ref-transition-table:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "Human-readable transition table read and verified: 45 legal, 19 illegal, 64 total entries match code exactly."
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM experiment's 6/6 violation detection unchanged. The ontology tested here supports the violation detection framework."
  forbidden_proxies:
    fp-weak-hypothesis:
      status: rejected
      notes: "RuleBasedStateMachine tests BOTH that legal transitions maintain invariants AND that illegal transitions are rejected. 5 invariants checked: state validity, no illegal accepted, terminal respected, initial unreachable, log consistency."
    fp-coverage-not-mutation:
      status: rejected
      notes: "Mutation score (99.0% adjusted) reported, not code coverage. Custom mutation testing with 5 operators generated 110 mutants; 103 killed by the test suite."
    fp-low-examples:
      status: rejected
      notes: "max_examples=10000 explicitly set. Hypothesis completed 10000 examples with stateful_step_count=30, producing ~300K transition attempts."
  uncertainty_markers:
    weakest_anchors:
      - "6 equivalent mutants in __main__ block cannot be killed by any test -- this is inherent to demo/script code that is not imported"
      - "1 low-value mutation (warn_on_legacy=False -> True) changes warning behavior only, not functional correctness"
    unvalidated_assumptions: []
    competing_explanations: []
    disconfirming_observations: []

duration: 20min
completed: 2026-03-15
---

# Phase 1, Plan 02: Property-Based Testing and Mutation Testing Summary

**Adversarial property-based testing (10K+ Hypothesis sequences) and mutation testing (99% adjusted score) confirm transition table correctness and test suite quality**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-15T23:17:00Z
- **Completed:** 2026-03-15T23:55:00Z
- **Tasks:** 3
- **Files created:** 6

## Key Results

- Hypothesis RuleBasedStateMachine: 10,000 examples x 30 steps = ~300K transition attempts with zero invariant violations [CONFIDENCE: HIGH]
- All 19 illegal transitions parametrized and correctly rejected; all 45 legal transitions accepted [CONFIDENCE: HIGH]
- Mutation testing: 110 mutants, 103 killed, 99.0% adjusted score (after classifying 6 equivalent + 1 low-value) [CONFIDENCE: HIGH]
- Full test suite: 301 tests pass (103 existing + 198 new) with zero failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Install hypothesis/mutmut and create test skeleton** - `1e320be` (setup)
2. **Task 2: Hypothesis RuleBasedStateMachine + negative transition tests** - `abb3b12` (validate)
3. **Task 3: Mutation testing and gap closure** - `6ac49d8` (validate)

## Files Created/Modified

- `tools/test_forge_ontology.py` - 198 property-based, parametrized, structural, and gap-closure tests
- `tools/run_mutation_tests.py` - Custom AST-based mutation testing script (mutmut Python 3.14 workaround)
- `tools/conftest.py` - sys.path setup for test discovery from project root
- `docs/mutation-report.md` - Complete mutation testing analysis with survivor classification
- `docs/mutation-results.json` - Machine-readable mutation results (110 mutants)
- `setup.cfg` - mutmut configuration (for future use when Python 3.14 support lands)

## Next Phase Readiness

- Transition table verified by adversarial testing: safe for Phase 2 instrumentation
- Test suite quality confirmed: new code changes will be caught by mutation-grade tests
- 301 tests provide comprehensive regression anchor for all downstream phases
- No changes to forge_nulls.py were needed (Plan 01 table is correct)

## Contract Coverage

- Claim IDs advanced: claim-adversarial-verified -> passed, claim-mutation-adequate -> passed
- Deliverable IDs produced: deliv-hypothesis-tests -> tools/test_forge_ontology.py, deliv-mutation-report -> docs/mutation-report.md
- Acceptance test IDs run: test-10k-sequences -> passed, test-negative-transitions -> passed, test-mutation-score -> passed
- Reference IDs surfaced: ref-forge-nulls-updated -> read, use; ref-103-tests -> read, compare; ref-transition-table -> read; ref-mock-experiment -> compare
- Forbidden proxies rejected: fp-weak-hypothesis -> rejected, fp-coverage-not-mutation -> rejected, fp-low-examples -> rejected

## Validations Completed

- **Hypothesis adversarial testing:** 10K examples x 30 steps, 5 invariants per step, zero violations
- **Illegal transition coverage:** All 19 illegal transitions individually parametrized and verified
- **Legal transition coverage:** All 45 legal transitions individually parametrized and verified
- **Structural invariants:** Table completeness (64), terminal (deleted), initial (not_invoked, not_generated), self-transitions, active connectivity, initial-to-active reachability
- **Invalid state handling:** ValueError for non-existent states, empty strings, None, case sensitivity, legacy aliases
- **Table-function agreement:** All 64 entries cross-checked between TRANSITION_TABLE dict and validate_transition()
- **Mutation score:** 99.0% adjusted (103/104 non-equivalent killed)
- **Regression:** 103 existing tests pass throughout all changes (verified at each task)

## Decisions Made

1. **Custom mutation testing tool:** mutmut v3.5.0 has Python 3.14 multiprocessing incompatibility; v2.5.1 has pony ORM deepcopy incompatibility. Wrote `run_mutation_tests.py` using Python's `ast` module with 5 mutation operators targeting state machine logic.
2. **Hypothesis tests excluded from mutation runs:** Each StateMachine test takes ~40-80s; running 110 mutants would take >2 hours. Parametrized tests (250+ fast tests in <0.5s) provide equivalent mutation-killing power for this codebase.
3. **Survivor classification:** 6 of 7 survivors are in the `__main__` demo block (equivalent by definition -- never imported during tests). 1 survivor changes `warn_on_legacy=False` to `True` (warning side-effect, not functional correctness).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Code Bug] mutmut incompatibility with Python 3.14**

- **Found during:** Task 3 (mutation testing)
- **Issue:** mutmut v3.5.0 crashes on `set_start_method('fork')` during trampoline import; mutmut v2.5.1 crashes on pony ORM deepcopy with itertools.count
- **Fix:** Wrote custom AST-based mutation testing script with 5 operators
- **Files created:** tools/run_mutation_tests.py
- **Verification:** 110 mutants generated and tested, consistent results across runs
- **Committed in:** 6ac49d8

**2. [Rule 1 - Code Bug] nonlocal variable in class body**

- **Found during:** Task 3 (first mutation script run)
- **Issue:** `nonlocal applied` inside a class body doesn't bind correctly in Python 3.14
- **Fix:** Changed to mutable dict pattern: `state = {"applied": False}`
- **Files modified:** tools/run_mutation_tests.py
- **Verification:** All 110 mutants processed without errors
- **Committed in:** 6ac49d8

**3. [Rule 4 - Missing Component] conftest.py for test discovery**

- **Found during:** Task 3 (mutmut configuration)
- **Issue:** Tests in tools/ could not be discovered from project root (sys.path missing)
- **Fix:** Created tools/conftest.py to add tools/ to sys.path
- **Files created:** tools/conftest.py
- **Verification:** `python3 -m pytest tools/ --co` discovers all 301 tests from project root
- **Committed in:** 6ac49d8

---

**Total deviations:** 3 auto-fixed (2 code bugs, 1 missing component)
**Impact on plan:** All necessary for correctness. Custom mutation tool achieves same goals as mutmut. No scope creep.

## Issues Encountered

None beyond the mutmut compatibility issues documented as deviations.

## Open Questions

- Will Phase 2 instrumentation require additional transition table tests? The current suite covers the table exhaustively but does not test the instrumentation layer.
- Should `run_mutation_tests.py` be maintained as a project tool, or should it be retired when mutmut adds Python 3.14 support?

## Self-Check: PASSED

- [x] tools/test_forge_ontology.py exists with 198 tests (RuleBasedStateMachine, parametrized, structural, gap-closure)
- [x] docs/mutation-report.md exists with complete analysis
- [x] docs/mutation-results.json exists with 110 mutant records
- [x] tools/run_mutation_tests.py exists and produces reproducible results
- [x] tools/conftest.py exists for test discovery
- [x] All 301 tests pass (103 + 198)
- [x] forge_nulls.py unchanged (git diff empty)
- [x] Commits 1e320be, abb3b12, 6ac49d8 exist in git log
- [x] Contract coverage: all claim, deliverable, acceptance test, reference, and forbidden proxy IDs accounted for
- [x] Adjusted mutation score 99.0% > 85% threshold

---

_Phase: 01-ontology-formalization-and-verification_
_Completed: 2026-03-15_
