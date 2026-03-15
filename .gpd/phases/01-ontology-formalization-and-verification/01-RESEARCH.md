# Phase 1: Ontology Formalization and Verification - Research

**Researched:** 2026-03-15
**Domain:** Formal systems / state machine specification / property-based testing / mutation testing
**Confidence:** HIGH

## Summary

Phase 1 formalizes the 8-state absence ontology as a complete, verified finite state machine with an explicit 64-entry transition table, resolves open design questions about ontology expansion and recoverability semantics, and validates the existing test suite via mutation testing. The problem is well-bounded: 8 states produce a finite 8x8 transition matrix (or 9x9 / 10x10 if expansion is warranted), the existing implementation in `forge_nulls.py` provides executable ground truth, and the tools (Hypothesis, mutmut) are mature and well-documented for exactly this class of problem.

The primary challenge is not computational but conceptual: deciding the correct transition rules requires understanding the semantics of each absence state in the context of real agent workflows. The existing implementation implicitly defines some transitions (via validation logic and the `absent()` constructor) but does not explicitly enumerate all 64 pairs. The open questions -- whether `timed_out` and `interrupted` should be distinct states, whether recoverability should be binary or graded -- require principled design decisions informed by real agent lifecycle patterns, not just formal completeness.

**Primary recommendation:** Build the transition table by systematic analysis of agent lifecycle scenarios, implement it as a `validate_transition(from_state, to_state) -> bool` function in `forge_nulls.py`, then use Hypothesis `RuleBasedStateMachine` with `settings(max_examples=1000, stateful_step_count=50)` to adversarially explore the state space. Resolve the `resolved` vs `not_generated` discrepancy first -- the implementation has `not_generated` where the documentation has `resolved`, and these serve different semantic roles (ref state vs absence state).

## Active Anchor References

| Anchor / Artifact | Type | Why It Matters Here | Required Action | Where It Must Reappear |
| --- | --- | --- | --- | --- |
| forge_nulls.py | implementation anchor | Contains V1_ABSENCE_STATES, AbsenceState enum, validation logic -- the executable ground truth | read, extend | plan, execution, verification |
| 103 passing tests | regression anchor | test_forge_v1_convergence.py defines current behavioral contract | preserve (all must still pass after changes) | plan, execution, verification |
| ref-mock-experiment | benchmark | 6/6 violations caught, 100% provenance -- ceiling that ontology must support | compare | verification |
| CONVENTIONS.md | specification | Documents known discrepancy (resolved vs not_generated) and open questions | read, resolve discrepancy | plan, execution |

**Missing or weak anchors:** No explicit transition table exists yet -- the 8x8 matrix is the primary deliverable of this phase. The implicit transition rules are scattered across forge_nulls.py (validation), forge_stage_output.py (ref states), and forge_chamber.py (chamber lifecycle). These must be extracted and formalized.

## Conventions

| Choice | Convention | Alternatives | Source |
| --- | --- | --- | --- |
| Absence states | 8 canonical: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable | Add resolved, timed_out, interrupted (expansion candidates) | forge_nulls.py V1_ABSENCE_STATES |
| Canonical field name | `state` (not `absence_state`) | `absence_state` (legacy, accepted at ingress only) | forge_nulls.py normalize_absent_object |
| Deprecated alias | `pruned` -> `pruned_recoverable` | Remove alias entirely | forge_nulls.py _LEGACY_ALIASES |
| Ref states | `resolved` / `unresolved` (for source_refs) | -- | forge_v1_bridge.py line 380 |
| Transition classification | legal / illegal / conditional | binary legal/illegal only | CONVENTIONS.md convention #3 |
| Hash algorithm | SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True) | -- | forge_stage_output.py, forge_trace_codec.py |

**CRITICAL: `resolved` is a REF STATE, not an ABSENCE STATE.** PROJECT.md and ROADMAP.md list `resolved` among the 8 absence states, but forge_nulls.py has `not_generated` instead. The implementation is ground truth. `resolved`/`unresolved` describe whether a source_ref successfully points to its target artifact -- they are metadata about provenance links, not about the absence of a value. Phase 1 FORM-01 must reconcile this discrepancy and produce the authoritative list.

## Mathematical Framework

### Key Equations and Starting Points

| Equation / Formalism | Name/Description | Source | Role in This Phase |
| --- | --- | --- | --- |
| T: S x S -> {legal, illegal, conditional} | Transition function | To be defined (Phase 1 deliverable) | The 8x8 (or NxN) matrix classifying every state pair |
| S = {not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable} | State set | forge_nulls.py V1_ABSENCE_STATES | Domain of the transition function |
| Pre(s, t): metadata requirements | Hoare-style preconditions | SUMMARY.md theoretical connection #1 | Each conditional transition has preconditions (e.g., pruned_recoverable requires source_refs) |
| mutation_score = killed_mutants / total_mutants | Mutation testing metric | SBQS 2024 benchmark paper | Quality gate for test suite (target > 0.85) |

### Required Techniques

| Technique | What It Does | Where Applied | Standard Reference |
| --- | --- | --- | --- |
| Finite state machine specification | Enumerate all states, transitions, and invariants | Transition table construction | Any formal methods textbook; Sipser "Introduction to the Theory of Computation" for FSM basics |
| Hypothesis RuleBasedStateMachine | Generate adversarial sequences of state transitions | FORM-02 property-based testing | [Hypothesis stateful testing docs](https://hypothesis.readthedocs.io/en/latest/stateful.html) |
| Mutation testing (mutmut) | Systematically mutate source code to verify test adequacy | Test suite quality validation | [mutmut documentation](https://mutmut.readthedocs.io/) |
| Typestate analysis | Encode legal state transitions into the type system | Conceptual framework for the ontology | Strom & Yemini (1986); [Stanford CS 242 lecture](https://stanford-cs242.github.io/f19/lectures/08-2-typestate.html) |

### Approximation Schemes

No approximations needed. The state space is finite (8 states = 64 transitions; 10 states = 100 transitions). All computations are exact enumeration over a small, discrete domain.

## Standard Approaches

### Approach 1: Bottom-Up from Implementation (RECOMMENDED)

**What:** Extract implicit transition rules from the existing forge_nulls.py validation logic, forge_chamber.py lifecycle, and forge_stage_output.py artifact creation. Build the transition table by systematically asking "given an entity currently in state X, what events can move it to state Y?" for every (X, Y) pair.

**Why standard:** The implementation is the executable ground truth (per CONVENTIONS.md). Building the formal specification from the implementation ensures alignment and catches implicit assumptions.

**Track record:** This is the standard approach for formalizing existing systems -- Amazon's use of TLA+ at AWS started from existing protocols, not from scratch specifications.

**Key steps:**

1. **Reconcile the state list.** Confirm the 8 canonical states from forge_nulls.py. Decide whether `resolved` belongs (finding: it does NOT -- it is a ref state). Decide whether `not_generated` belongs (finding: it DOES -- it is in the implementation).
2. **Enumerate lifecycle scenarios.** For each state, document the agent events that produce it (e.g., "a tool call times out -> the result field is `unknown`" or "a subcall is never made -> the output is `not_invoked`").
3. **Build the 8x8 matrix.** For every (source, target) pair, classify as legal, illegal, or conditional. Start with the 3 known-illegal transitions (any->not_invoked, any->not_generated, deleted->any_except_deleted) and work outward.
4. **Define preconditions for conditional transitions.** A conditional transition requires specific metadata (e.g., transitioning to `pruned_recoverable` requires `source_refs` to be populated).
5. **Implement `validate_transition()`.** Add to forge_nulls.py as a function that takes (from_state, to_state) and returns True/False/raises.
6. **Write Hypothesis RuleBasedStateMachine tests.** Model the state machine and generate adversarial sequences.
7. **Run mutmut on forge_nulls.py.** Verify mutation score > 85%.

**Known difficulties at each step:**

- Step 1: The `resolved`/`not_generated` discrepancy MUST be resolved before proceeding. Failing to do so propagates confusion into all downstream phases.
- Step 3: Some (source, target) pairs may be ambiguous -- e.g., can `withheld` transition to `resolved`? (If the withheld content is later released, yes.) These require design decisions, not just implementation analysis.
- Step 5: The transition function must handle the difference between the state of a VALUE (absence state) and the state of a REF (resolved/unresolved). These are distinct concepts and must not be conflated.

### Approach 2: Top-Down from Semantics (FALLBACK)

**What:** Start from the semantic meaning of each state and derive transitions from first principles. Define each state's entry/exit conditions axiomatically, then derive the transition table as a consequence.

**When to switch:** If the implementation contains implicit transitions that are semantically wrong (i.e., the code allows a transition that should not be legal), the top-down approach provides an independent specification to compare against.

**Tradeoffs:** More rigorous but risks diverging from the implementation. Any spec-vs-implementation mismatch must be resolved (and the resolution documented) before the phase can complete.

### Anti-Patterns to Avoid

- **Conflating ref states with absence states.** `resolved`/`unresolved` describe source_ref link status. `not_generated`/`unknown`/etc. describe value absence reasons. These are orthogonal. Do NOT add `resolved` to the absence state ontology just because PROJECT.md lists it.
  - _Example:_ A field can be `{value: null, state: "pruned_recoverable"}` with source_refs that are `"resolved"` -- the absence state and the ref state are independent.

- **Treating the transition table as a one-time artifact.** The table must be machine-readable (not just a markdown table) and programmatically enforced. A table that only exists in documentation will drift from the implementation.
  - _Example:_ Implement the table as a dict/frozenset in forge_nulls.py, not just as a table in RESEARCH.md or PLAN.md.

- **Over-expanding the ontology prematurely.** Adding `timed_out`, `interrupted`, `expired`, `retryable`, etc. before evidence shows they are needed creates maintenance burden. Phase 1 FORM-03 should resolve this with documented rationale, not by defaulting to "add everything."

## Existing Results to Leverage

**This section documents results the executor should CITE rather than re-derive.**

### Established Results (DO NOT RE-DERIVE)

| Result | Exact Form | Source | How to Use |
| --- | --- | --- | --- |
| 8 canonical absence states | `V1_ABSENCE_STATES = frozenset({"not_generated", "not_invoked", "unknown", "unresolved", "withheld", "invalid", "deleted", "pruned_recoverable"})` | forge_nulls.py line 21-30 | Starting point for transition table |
| Legacy alias mapping | `_LEGACY_ALIASES = {"pruned": "pruned_recoverable"}` | forge_nulls.py line 33-35 | Preserve backward compatibility |
| 3 known-illegal transitions | any->not_invoked, any->not_generated, deleted->any_except_deleted | CONVENTIONS.md convention #3 | Seed the transition table |
| Ref state validation | `state in {"resolved", "unresolved"}` | forge_v1_bridge.py line 380 | Keep ref states separate from absence states |
| AbsenceState enum | 8 members + PRUNED deprecated alias | forge_nulls.py line 38-49 | Extend with validate_transition method or companion function |
| Validation logic | validate_field, validate_record, normalize_record | forge_nulls.py | Must continue passing all 103 tests after changes |
| V1_REF_CONTAINER_KEYS | `frozenset({"refs", "source_refs"})` -- exempt from null discipline | forge_nulls.py line 202 | Empty refs/source_refs are valid, not absent |

**Key insight:** The existing 103 tests define the behavioral contract. Any formalization that breaks existing tests has introduced a regression. The transition table must be consistent with what the current validation logic already accepts and rejects.

### Relevant Prior Work

| Paper/Result | Authors | Year | Relevance | What to Extract |
| --- | --- | --- | --- | --- |
| Typestate: A Programming Language Concept | Strom & Yemini | 1986 | Original typestate concept -- encoding state in the type system | Conceptual framework for absence states as typestates |
| A Theory of Typestate-Oriented Programming | Aldrich et al. | 2009 | Formal foundations for typestate with access permissions | Theoretical backing for the transition-legality concept |
| Null References: The Billion Dollar Mistake | Hoare | 2009 | Motivates typed absence over raw null | Cite as motivation; do not re-derive |
| Use of Formal Methods at Amazon Web Services | Amazon | 2014 | TLA+ for protocol verification at scale | Validates the approach of formalizing existing protocols |
| Hypothesis PBT empirical evaluation | OOPSLA 2025 | 2025 | PBT finds ~50x more mutations than unit tests | Justifies Hypothesis as primary testing tool |
| Mutation Testing Tools for Python | SBQS 2024 | 2024 | Mutmut benchmarks: 88.5% detection rate, 1200 mutants/min | Calibrates mutation score expectations |
| Omittable -- Solving the Ambiguity of Null | committing-crimes.com | 2025 | Multi-state null beyond binary Option type | Validates the design space this project occupies |

## Computational Tools

### Core Tools

| Tool | Version/Module | Purpose | Why Standard |
| --- | --- | --- | --- |
| pytest | 8.x | Test runner | Standard Python testing; existing 103 tests use unittest but pytest runs both |
| Hypothesis | 6.x (RuleBasedStateMachine) | Property-based stateful testing | Only Python library with first-class state machine support; @rule, @precondition, @invariant decorators |
| mutmut | 3.x | Mutation testing | Most actively maintained Python mutation tester; 1200 mutants/min; 88.5% detection rate on Python |

### Supporting Tools

| Tool | Purpose | When to Use |
| --- | --- | --- |
| mypy (strict) | Static type checking | Verify AbsenceState type flows correctly; catch forgotten None-checks |
| Python enum (stdlib) | State enumeration | Already used via AbsenceState(str, Enum) |
| frozenset (stdlib) | Immutable state sets | Already used for V1_ABSENCE_STATES |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
| --- | --- | --- |
| Hypothesis RuleBasedStateMachine | TLA+ model checker | TLA+ provides exhaustive verification but requires Java tooling and a separate specification language; Hypothesis tests the actual Python implementation directly. TLA+ is listed as EXTD-01 (follow-up, not Phase 1 requirement). |
| mutmut | Cosmic Ray | Cosmic Ray has broader operator set but 82.7% detection rate vs mutmut's 88.5% on Python; slower execution. mutmut is the better choice for this project. |
| Custom transition validator | transitions library (pytransitions) | The `transitions` library provides a full FSM framework, but the absence ontology is simple enough (8 states, ~20 transitions) that a custom dict-based implementation is clearer and avoids an external dependency. |

### Computational Feasibility

| Computation | Estimated Cost | Bottleneck | Mitigation |
| --- | --- | --- | --- |
| Hypothesis 10K+ examples, 50 steps each | ~5-30 seconds | CPU-bound state machine exploration | Trivial for 8-state machine |
| Mutmut on forge_nulls.py (~300 lines) | ~5-10 minutes | Runs full test suite per mutant | 103 tests are fast (< 1s total); manageable |
| Transition table enumeration | Negligible | 64 (source, target) pairs to classify | Manual design work, not computation |

**Installation / Setup:**
```bash
# These should already be available; verify versions
pip install hypothesis mutmut pytest mypy
```

## Validation Strategies

### Internal Consistency Checks

| Check | What It Validates | How to Perform | Expected Result |
| --- | --- | --- | --- |
| Transition table completeness | Every (source, target) pair is classified | Assert len(transition_table) == N*N where N = number of states | 64 entries for 8 states; no gaps |
| Self-transition consistency | Every state can either self-transition or not, explicitly | Check diagonal of transition matrix | Design decision: self-transitions should generally be legal (idempotent re-assignment) |
| Terminal state verification | deleted is terminal (no outgoing transitions except self) | Verify row in transition matrix | All deleted->X (X != deleted) are illegal |
| Initial state verification | not_invoked and not_generated have no incoming transitions | Verify columns in transition matrix | All X->not_invoked and X->not_generated are illegal |
| Precondition coverage | Every conditional transition has documented metadata requirements | Review each conditional entry | E.g., pruned_recoverable requires source_refs |
| 103 test regression | No existing test breaks | Run full test suite after changes | All 103 pass |

### Known Limits and Benchmarks

| Limit | Parameter Regime | Known Result | Source |
| --- | --- | --- | --- |
| MockLM violation detection | 6 deliberate violations | 6/6 detected | experiment_results.json |
| MockLM provenance reachability | 3 scenarios | 100% | experiment_results.json |
| Hypothesis exploration depth | 1000 examples x 50 steps | ~50K transitions explored | Hypothesis docs default recommendation |
| Mutation score baseline | Pure logic modules | > 85% target | METHODS.md recommendation; SBQS 2024 benchmarks |

### Numerical Validation

Not applicable -- all computations are discrete/boolean (transition legal/illegal). No floating-point arithmetic involved.

### Red Flags During Computation

- **If Hypothesis finds an invariant violation on a transition classified as "legal":** The transition table has a bug. Revise before proceeding. This is the Phase 1 backtracking trigger.
- **If mutation score is below 70%:** The test suite has fundamental gaps. Write additional tests targeting the surviving mutants before claiming the ontology is verified.
- **If multiple (source, target) pairs remain "conditional" with vague preconditions:** The ontology is under-specified. Every conditional transition must have a concrete, machine-checkable precondition.
- **If the `resolved`/`not_generated` discrepancy is not resolved first:** All downstream work inherits the confusion. This must be the FIRST task.

## Common Pitfalls

### Pitfall 1: Conflating Ref States with Absence States

**What goes wrong:** Adding `resolved` to V1_ABSENCE_STATES because the documentation lists it, when it actually describes a different concept (source_ref link status, not value absence).
**Why it happens:** PROJECT.md and ROADMAP.md list `resolved` among the 8 absence states. The CONVENTIONS.md flags this as a documentation error.
**How to avoid:** Read forge_v1_bridge.py line 380: `if state not in {"resolved", "unresolved"}` -- this validates ref states, not absence states. Maintain the separation. Update documentation to match implementation.
**Warning signs:** Tests start failing because `normalize_absence_state("resolved")` raises ValueError.
**Recovery:** Remove `resolved` from documentation lists; keep `not_generated` in the absence ontology where it belongs.

### Pitfall 2: Over-Expanding the Ontology Without Evidence

**What goes wrong:** Adding `timed_out`, `interrupted`, `expired`, `retryable`, `pending`, etc. as new states without evidence that the existing 8 states cannot represent these scenarios.
**Why it happens:** It feels safer to have more states. The FORM-03 requirement explicitly asks about expansion.
**How to avoid:** For each candidate state, ask: "Can this scenario be represented by an existing state with appropriate metadata?" If `timed_out` can be represented as `{state: "unresolved", reason: "timed_out"}`, adding a separate state gains nothing but adds 2N transitions to manage.
**Warning signs:** The transition table grows from 64 to 100+ entries with many conditional transitions that have similar preconditions.
**Recovery:** Prefer metadata enrichment over state expansion. Reserve state expansion for cases where transition rules genuinely differ.

### Pitfall 3: Non-Machine-Readable Transition Table

**What goes wrong:** The transition table is specified only in a markdown document and not encoded in the Python implementation.
**Why it happens:** Writing a markdown table feels like "formalizing" the ontology.
**How to avoid:** The transition table must be a data structure in forge_nulls.py (dict, frozenset, or similar) that `validate_transition()` consults. The markdown table in documentation is a human-readable view of the machine-readable source.
**Warning signs:** The Hypothesis tests import the transition rules from a different location than forge_nulls.py's runtime validation.
**Recovery:** Single source of truth: the Python data structure. Documentation is generated from or mirrors it.

### Pitfall 4: Hypothesis Tests That Are Too Weak

**What goes wrong:** The RuleBasedStateMachine only models legal transitions, so it never tests whether illegal transitions are properly rejected.
**Why it happens:** The natural approach is to define rules for legal transitions and invariants that check validity. But this only tests the "happy path" of the state machine.
**How to avoid:** Include explicit negative tests: for each illegal transition, verify that `validate_transition(from_state, to_state)` raises or returns False. The RuleBasedStateMachine tests the positive property (legal transitions maintain invariants); separate unit tests verify the negative property (illegal transitions are rejected).
**Warning signs:** The RuleBasedStateMachine passes 10K examples but a manual test of `validate_transition("deleted", "unknown")` succeeds when it should fail.
**Recovery:** Add explicit parametrized tests for all illegal transitions alongside the stateful tests.

### Pitfall 5: Equivalent Mutants Inflating Failure Count

**What goes wrong:** Mutmut reports surviving mutants that are actually equivalent (they change code but not behavior), making the mutation score appear lower than it is.
**Why it happens:** Some mutations produce semantically equivalent code (e.g., reordering independent dict operations). Manual review is required to identify these.
**How to avoid:** Expect 5-15% of surviving mutants to be equivalent. Review each survivor manually. Use `mutmut show <id>` to inspect. Mark genuinely equivalent mutants as such.
**Warning signs:** Mutation score is 75-80% but most survivors are trivial reorderings.
**Recovery:** Manual review of survivors; document equivalent mutants; report adjusted mutation score.

## Level of Rigor

**Required for this phase:** Formal specification with implementation-level verification.

**Justification:** The absence ontology is the foundation for all downstream work. An incorrectly specified transition table produces meaningless measurements in Phases 3-4. The state space is small enough for exhaustive specification (64 entries) and near-exhaustive testing (Hypothesis explores ~50K paths). Formal proof is not needed (TLA+ is deferred to EXTD-01), but the specification must be complete, unambiguous, and programmatically enforced.

**What this means concretely:**

- Every (source, target) pair must be explicitly classified (no "TBD" or "probably legal")
- Every conditional transition must have a concrete, testable precondition
- Every invariant must be checked by Hypothesis after every step
- The transition table must be a data structure in Python, not just documentation
- Mutation score > 85% on forge_nulls.py confirms the test suite catches real defects

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| Binary null/not-null (Option/Maybe type) | Multi-state absence ontology (8+ states) | This project (novel) | Distinguishes REASON for absence, not just presence/absence |
| Implicit null semantics | Explicit typed absence with state machine rules | Emerging (Omittable pattern, typestate analysis) | Prevents the "billion dollar mistake" class of errors |
| Ad-hoc transition validation | Property-based stateful testing (Hypothesis) | ~2015+ (Hypothesis matured) | Finds edge cases human-written tests miss |
| Code coverage as test quality | Mutation testing (mutmut) | ~2018+ (mutmut active development) | Measures actual fault detection, not just line coverage |

**Superseded approaches to avoid:**

- **Code coverage as test adequacy:** Coverage tells you what code was executed, not whether tests check anything meaningful. Use mutation score instead. Coverage is a secondary sanity check only.
- **unittest.TestCase-only testing:** While the existing 103 tests use unittest and must be preserved, new tests should use Hypothesis for the stateful testing component. unittest is fine for deterministic unit tests.

## Open Questions

1. **Should `resolved` be an absence state or not?**
   - What we know: Implementation has `not_generated` where documentation has `resolved`. `resolved` is used as a ref state. These are different concepts.
   - What's unclear: Does any agent scenario require `resolved` as an absence state (meaning "this value was absent but has been resolved")?
   - Impact on this phase: Must be resolved FIRST -- it determines the state count (8 vs 9) and the transition table dimensions.
   - Recommendation: Keep `not_generated` in the absence ontology. Do NOT add `resolved` as an absence state. Update documentation. `resolved` remains a ref state only.

2. **Should `timed_out` and `interrupted` be distinct states?**
   - What we know: Real agent workflows produce timeouts (LLM API, tool calls) and interruptions (user cancel, context limits). Currently these would map to `unknown` or `unresolved`.
   - What's unclear: Do timed_out/interrupted require DIFFERENT transition rules than unknown/unresolved? If the transition rules are identical, metadata suffices.
   - Impact on this phase: Adding 2 states expands the matrix from 64 to 100 entries.
   - Recommendation: Research real agent timeout/interrupt patterns. If the transition rules differ (e.g., `timed_out` can be retried while `unknown` cannot), add them. If only the reason differs, use metadata: `{state: "unresolved", reason: "timed_out"}`. Lean toward NOT expanding unless evidence compels it. YAGNI.

3. **Should recoverability be binary or graded?**
   - What we know: Currently binary: `pruned_recoverable` vs `deleted` (non-recoverable). Real compaction may produce partially recoverable states (structural refs survive but content is lossy-summarized).
   - What's unclear: Would graded recoverability (e.g., a 0-1 confidence score on the recoverability of a pruned artifact) improve downstream decision-making?
   - Impact on this phase: Graded recoverability changes `pruned_recoverable` from a state to a state+metadata pair.
   - Recommendation: Keep binary for Phase 1. Graded recoverability is a Phase 4 concern when actual compaction behavior is observed. The absence state captures the category (recoverable vs not); metadata captures the degree. This is the metadata-enrichment-over-state-expansion principle.

4. **What is the correct handling of self-transitions?**
   - What we know: An entity re-entering the same state (e.g., unknown -> unknown after another failed lookup) is semantically valid.
   - What's unclear: Should self-transitions update metadata (timestamp, reason) or be no-ops?
   - Impact on this phase: Affects the diagonal of the transition matrix (8 entries).
   - Recommendation: Self-transitions should be legal for most states (they represent idempotent re-evaluation). `not_invoked` self-transition is trivially legal (nothing happened). `deleted` self-transition is legal (re-confirming deletion). Mark all 8 diagonal entries as legal.

## Alternative Approaches if Primary Fails

| If This Fails | Because Of | Switch To | Cost of Switching |
| --- | --- | --- | --- |
| Bottom-up from implementation | Implementation has contradictory implicit rules | Top-down from semantics (define axioms, derive transitions) | ~2x effort; must then reconcile spec with implementation |
| Hypothesis RuleBasedStateMachine | State machine is too simple for Hypothesis to find bugs (all paths are trivial) | Exhaustive enumeration of all 8^50 paths (computationally infeasible but 8^3 = 512 3-step paths is tractable) | Modest; simple nested loop covers short paths |
| mutmut | Excessive equivalent mutants or incompatibility with unittest-based tests | Cosmic Ray (alternative mutation tester) | Low; same concept, different tool |
| 8-state ontology | Evidence from FORM-03 analysis shows timed_out/interrupted need distinct transitions | Expand to 10-state ontology and redo transition table | ~50% rework of the transition table (100 entries vs 64) |

**Decision criteria:** If Hypothesis finds no violations after 10K examples AND manual review confirms the transition table is correct, the approach has succeeded. If Hypothesis finds violations, the transition table must be revised (backtracking trigger). If FORM-03 evidence supports expansion, expand before finalizing.

## The Discrepancy Resolution Task

This is the most critical pre-requisite for all other work in this phase. The state list must be authoritative before building the transition table.

**Current situation:**

| Source | Listed States |
| --- | --- |
| forge_nulls.py V1_ABSENCE_STATES | not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable |
| PROJECT.md / ROADMAP.md success criteria | not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable, **resolved** |
| CONVENTIONS.md | Documents the discrepancy; declares implementation wins pending Phase 1 |

**Resolution (recommended):**

1. The authoritative list is the implementation: `{not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable}`.
2. `resolved` is a REF STATE (describes source_ref link status), not an absence state. It should NOT be added to V1_ABSENCE_STATES.
3. `not_generated` means "the LLM/tool did not produce output" -- this is a genuine absence reason distinct from `not_invoked` ("the tool was never called").
4. Update PROJECT.md and ROADMAP.md to match the implementation.
5. Document the semantic distinction between absence states (value absence reasons) and ref states (provenance link status).

## Hypothesis RuleBasedStateMachine Design

The stateful test should model a single entity whose absence state evolves through transitions. Key design decisions:

**State representation:** A single `self.state` string from V1_ABSENCE_STATES, plus `self.metadata` dict tracking required companions (reason, source_refs, etc.).

**Rules:** One `@rule` per legal transition. Use `@precondition` to restrict rules to states where the transition is legal.

**Invariants:**
1. `self.state` is always in V1_ABSENCE_STATES
2. If `self.state == "pruned_recoverable"`, `self.metadata["source_refs"]` must be non-empty
3. No illegal transition has been recorded in the transition log
4. The transition log is consistent with the transition table

**Settings:** `settings(max_examples=1000, stateful_step_count=50)` produces ~50K transition steps. For the Phase 1 success criteria of "10K+ adversarial sequences," use `max_examples=10000, stateful_step_count=30` (which produces 10K+ sequences of 30 steps each, ~300K total transitions).

**Negative testing:** Separate from the RuleBasedStateMachine, write parametrized tests that attempt every illegal transition and verify rejection.

## Mutation Testing Strategy

**Target modules:** `forge_nulls.py` (primary), `forge_trace_codec.py` and `forge_reversible_summary.py` (secondary, for broader test quality assessment).

**Configuration:**
```ini
[tool.mutmut]
paths_to_mutate = "tools/forge_nulls.py"
tests_dir = "tools/"
runner = "python -m pytest"
```

**Expected results:**
- ~100-200 mutants for forge_nulls.py (~300 lines of logic)
- Target: > 85% killed (> 85 out of 100 mutants detected by tests)
- ~5-15% equivalent mutants requiring manual review

**Handling survivors:**
1. Run `mutmut results` to list survivors
2. For each: `mutmut show <id>` to inspect the mutation
3. Classify as: (a) genuine gap -- write new test, (b) equivalent mutant -- document, (c) low-value mutation -- document rationale for not testing
4. Report adjusted score excluding confirmed equivalent mutants

## Sources

### Primary (HIGH confidence)

- [Hypothesis stateful testing documentation](https://hypothesis.readthedocs.io/en/latest/stateful.html) -- RuleBasedStateMachine API: @rule, @precondition, @invariant, @initialize, Bundles, settings
- [OOPSLA 2025 PBT Empirical Study](https://2025.splashcon.org/details/OOPSLA/102/An-Empirical-Evaluation-of-Property-Based-Testing-in-Python) -- Hypothesis finds ~50x more mutations than average unit tests (426 Python programs)
- [SBQS 2024 Mutation Testing Tools for Python](https://dl.acm.org/doi/10.1145/3701625.3701659) -- Mutmut 88.5% detection rate, Cosmic Ray 82.7%; comparative benchmark
- [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf) -- TLA+ for protocol verification at production scale
- [mutmut documentation](https://mutmut.readthedocs.io/) -- Configuration, operation, result interpretation
- forge_nulls.py (local) -- Executable ground truth for absence state ontology

### Secondary (MEDIUM confidence)

- [Hypothesis rule-based stateful testing article](https://hypothesis.works/articles/rule-based-stateful-testing/) -- Conceptual introduction to RuleBasedStateMachine
- [Stanford CS 242: Typestate](https://stanford-cs242.github.io/f19/lectures/08-2-typestate.html) -- Typestate analysis foundations
- [Omittable -- Solving the Ambiguity of Null](https://committing-crimes.com/articles/2025-09-16-null-and-absence/) -- Multi-state null beyond binary Option type
- [Mutation Testing with Mutmut: Python for Code Reliability 2026](https://johal.in/mutation-testing-with-mutmut-python-for-code-reliability-2026/) -- Practical mutmut guide with configuration examples
- [State-transition table (Grokipedia)](https://grokipedia.com/page/State-transition_table) -- Standard FSM transition table representation
- [MCP Tasks primitive for timeout handling](https://medium.com/@ai_transfer_lab/why-your-mcp-agent-keeps-timing-out-and-the-fix-that-just-shipped-ad9cb130f8c4) -- Agent timeout lifecycle states; informs timed_out/interrupted design question

### Tertiary (LOW confidence)

- [Formalizing UML State Machines for Automated Verification](https://arxiv.org/pdf/2407.17215) -- Survey of FSM formalization approaches (MEDIUM-LOW; survey, not primary research)

## Metadata

**Confidence breakdown:**

- Mathematical framework: HIGH -- finite state machines are textbook material; 8 states is trivially small
- Standard approaches: HIGH -- Hypothesis RuleBasedStateMachine and mutmut are mature, well-documented tools used for exactly this class of problem
- Computational tools: HIGH -- all tools are pip-installable Python packages with stable APIs
- Validation strategies: HIGH -- exhaustive enumeration of a finite state space plus mutation testing provides strong coverage guarantees

**Research date:** 2026-03-15
**Valid until:** Indefinitely for the formal methods aspects; tool versions (Hypothesis 6.x, mutmut 3.x) may change APIs but the concepts are stable.

## Caveats and Self-Critique

1. **Assumption that might be wrong:** The 8-state ontology is treated as sufficient pending FORM-03 evidence. If real agent workflows produce scenarios that genuinely cannot be represented by any existing state + metadata combination, the ontology must be expanded. I am leaning toward NOT expanding, which risks under-specification.

2. **Alternative approach dismissed perhaps too quickly:** TLA+ model checking (EXTD-01) could provide exhaustive verification of safety and liveness properties. I dismissed it as "follow-up" because the requirements list it as follow-up and the state space is small enough for Hypothesis. But TLA+ would catch temporal properties (liveness: "every unresolved state eventually resolves or times out") that Hypothesis cannot test. If temporal properties matter for correctness, TLA+ should be promoted from follow-up to Phase 1.

3. **Limitation I may be understating:** The transition table is a design artifact, not a discovery. There is no "correct" transition table waiting to be found -- the project must DECIDE what transitions are legal. The research informs these decisions but cannot make them automatically. The executor will need design judgment, not just formal verification.

4. **Simpler method overlooked?** For a state machine with only 8 states, a simple exhaustive test (enumerate all 64 transitions, assert each is correctly classified) may be more effective than Hypothesis for finding bugs. Hypothesis excels at finding bugs in SEQUENCES of transitions, which is valuable, but the individual transition classification can be verified by brute force. Both approaches should be used.

5. **Would a specialist disagree?** A formal methods specialist would likely push for TLA+ or Alloy rather than Hypothesis, arguing that implementation-level testing cannot prove specification correctness. This is technically correct -- Hypothesis tests the implementation, not the specification. The counterargument is that for an 8-state FSM, the specification IS simple enough to verify by inspection, and what matters is that the implementation matches.
