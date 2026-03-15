# Absence State Transition Table

**Source of truth:** `tools/forge_nulls.py` — `TRANSITION_TABLE` dict and `validate_transition()` function.
This document is a human-readable mirror. If it diverges from the code, the code wins.

**Created:** Phase 1, Plan 01, Task 2
**Last updated:** Phase 1, Plan 01

---

## State Definitions

| State | Meaning | Category |
| ----- | ------- | -------- |
| `not_generated` | The LLM/tool did not produce output for this field | Initial |
| `not_invoked` | The tool/subcall was never called | Initial |
| `unknown` | The value is absent and the reason is unknown or lost | Active |
| `unresolved` | An attempt was made but did not complete successfully | Active |
| `withheld` | The value exists but is deliberately not provided | Active |
| `invalid` | A value was produced but failed structural validation | Active |
| `deleted` | The value was permanently removed; no recovery possible | Terminal |
| `pruned_recoverable` | The value was removed but can be recovered via source_refs | Active |

**Category semantics:**
- **Initial:** These states describe WHY a value was never produced. Nothing transitions INTO them because they represent "before any attempt" conditions. Entering them from another state would imply un-doing an action, which is incoherent.
- **Active:** These states describe the current status of an absent value. Transitions between active states are generally legal, representing agent lifecycle events (retry, investigation, compaction, etc.).
- **Terminal:** Once entered, no further transitions are possible (except idempotent self-transition). Deletion is permanent.

**Not absence states:** `resolved` and `unresolved` (in the context of `source_ref` entries) are REF states describing whether a provenance link points to a valid artifact. They are orthogonal to absence states and do not appear in this table.

---

## Transition Rules

Three structural rules generate the complete 64-entry table:

1. **Initial state rule:** Nothing transitions INTO `not_invoked` or `not_generated` (except self-transitions). These states mean "the action never happened" -- you cannot un-happen an action.

2. **Terminal state rule:** Nothing transitions OUT of `deleted` (except self-transition). Deletion is permanent. Recovery from deletion requires a different mechanism (e.g., backup restore) that operates outside the absence state machine.

3. **Self-transition rule:** Every state can transition to itself. This represents idempotent re-evaluation (e.g., "still unknown after another check").

4. **Default rule:** All other transitions are legal. Any non-terminal state can transition to any non-initial state, representing valid agent lifecycle events.

---

## 8x8 Transition Grid

**Legend:** L = Legal, X = Illegal

Rows = source (from) state. Columns = target (to) state.

| From \ To         | deleted | invalid | not_generated | not_invoked | pruned_recoverable | unknown | unresolved | withheld |
| ----------------- | ------- | ------- | ------------- | ----------- | ------------------ | ------- | ---------- | -------- |
| **deleted**            | L       | X       | X             | X           | X                  | X       | X          | X        |
| **invalid**            | L       | L       | X             | X           | L                  | L       | L          | L        |
| **not_generated**      | L       | L       | L             | X           | L                  | L       | L          | L        |
| **not_invoked**        | L       | L       | X             | L           | L                  | L       | L          | L        |
| **pruned_recoverable** | L       | L       | X             | X           | L                  | L       | L          | L        |
| **unknown**            | L       | L       | X             | X           | L                  | L       | L          | L        |
| **unresolved**         | L       | L       | X             | X           | L                  | L       | L          | L        |
| **withheld**           | L       | L       | X             | X           | L                  | L       | L          | L        |

**Counts:** 45 legal transitions, 19 illegal transitions, 64 total.

---

## Illegal Transition Categories

| Category | Count | Transitions | Rationale |
| -------- | ----- | ----------- | --------- |
| Into `not_invoked` (except self) | 7 | {deleted, invalid, not_generated, pruned_recoverable, unknown, unresolved, withheld} -> not_invoked | Cannot un-invoke: `not_invoked` means "never called," which cannot become true after any other state has been entered |
| Into `not_generated` (except self) | 7 | {deleted, invalid, not_invoked, pruned_recoverable, unknown, unresolved, withheld} -> not_generated | Cannot un-generate: `not_generated` means "LLM didn't produce output," which cannot become true retroactively |
| Out of `deleted` (except self) | 5 | deleted -> {invalid, pruned_recoverable, unknown, unresolved, withheld} | Deletion is terminal: permanent removal has no undo within the state machine (overlap with above categories: deleted->not_invoked and deleted->not_generated are already counted) |

**Total unique illegal:** 7 + 7 + 5 = 19 (deleted->not_invoked and deleted->not_generated counted in column rules, not double-counted).

---

## Example Agent Lifecycle Scenarios

| Scenario | Transition Sequence | Rationale |
| -------- | ------------------- | --------- |
| Tool never called, then compacted | not_invoked -> pruned_recoverable | Agent decided not to invoke, later compaction pruned the record |
| LLM timeout, retry succeeds but invalid | not_generated -> invalid | First attempt timed out (not_generated), retry produced structurally invalid output |
| Unknown becomes withheld | unknown -> withheld | Investigation reveals the value was deliberately withheld |
| Pruned item recovered but stale | pruned_recoverable -> unknown | Recovery retrieved something but it's unclear if it's still valid |
| Unresolved gives up | unresolved -> unknown | Resolution attempt abandoned, context lost |
| Invalid item deleted | invalid -> deleted | Decided to permanently remove the invalid record |
| Attempted deletion of not_invoked | not_invoked -> deleted | Valid: deciding that this un-invoked tool slot should be permanently removed from the record |

---

## Design Decisions

### FORM-03 Question 1: Should `timed_out` and `interrupted` be distinct absence states?

**Question:** Real agent workflows produce timeouts (LLM API timeout, tool execution timeout, context limit reached) and interruptions (user cancel, SIGTERM, quota exceeded). Should these be first-class states in the ontology?

**Evidence considered:**
1. **Scenario mapping to existing states:**
   - Timeout with no output -> `not_generated` (LLM never produced anything)
   - Timeout with partial output -> `unresolved` (attempt was made but not completed)
   - Interrupt before invocation -> `not_invoked` (tool was never called)
   - Interrupt during execution -> `unresolved` (execution started but didn't finish)
2. **Transition rule analysis:** Every timeout/interrupt scenario maps to an existing state that already has the correct transition rules. A `timed_out` state would have identical transitions to `unresolved` (can transition to any active state, cannot transition to initial states). An `interrupted` state would similarly mirror either `not_generated` or `unresolved` depending on the interrupt timing.
3. **Cost of expansion:** Adding 2 states expands the transition table from 64 (8x8) to 100 (10x10) entries, each requiring classification and testing. The 36 new entries would all follow the same structural rules (initial/terminal/default), adding no information.
4. **Metadata alternative:** The reason for absence can be captured as metadata: `{state: "unresolved", reason: "timed_out"}` or `{state: "not_generated", reason: "interrupted"}`. This preserves the information without inflating the state space.

**DECIDED: Do NOT add `timed_out` or `interrupted` as distinct states.** Use metadata enrichment instead. The existing 8 states are sufficient because timeout/interrupt scenarios map cleanly to existing states with identical transition rules. The `reason` field on absence objects already supports this pattern.

**Consequences for the transition table:** The table remains 8x8 = 64 entries. No changes needed.

**When to revisit:** If a future phase discovers an agent scenario where a timed-out value needs DIFFERENT transition rules than an unresolved value (e.g., "timed_out can be auto-retried but unresolved cannot"), that would justify adding a distinct state. The trigger is differing transition rules, not differing reasons.

---

### FORM-03 Question 2: Should recoverability be binary or graded?

**Question:** Currently recoverability is binary: `pruned_recoverable` (can be recovered via source_refs) vs `deleted` (permanently removed). Real LLM compaction may produce partially recoverable states where structural refs survive but content is lossy-summarized. Should recoverability be a continuous score (0-1)?

**Evidence considered:**
1. **Transition rule analysis:** A value with recoverability 0.3 has the same legal transitions as a value with recoverability 0.9 -- both are in the `pruned_recoverable` state and can transition to any active state. Graded recoverability does not change the transition rules.
2. **Phase 4 dependency:** Graded recoverability is primarily useful for Phase 4 (compaction survival measurement), where `reachability_fraction` is the key metric. Phase 1 needs only the binary distinction to build the correct transition table.
3. **Metadata approach:** A recoverability score can be stored as metadata: `{state: "pruned_recoverable", recoverability: 0.7, reason: "llm_compaction"}`. This captures the granularity without inflating the state space.
4. **YAGNI:** No actual LLM compaction data exists yet. Designing graded recoverability without empirical compaction behavior risks over-engineering.

**DECIDED: Keep recoverability binary for Phase 1.** The absence state captures the category (`pruned_recoverable` vs `deleted`); metadata captures the degree when needed. Graded recoverability is a Phase 4 concern when actual LLM compaction behavior is observed.

**Consequences for the transition table:** No changes. `pruned_recoverable` remains a single state. No `recoverability_score` metadata is required in the absence object schema (though it is not forbidden).

**When to revisit:** When Phase 4 measures actual LLM compaction on real Zarathustra tasks. If the binary distinction proves too coarse for meaningful `reachability_fraction` analysis (e.g., all pruned items have wildly different recovery success rates), graded recoverability should be added as metadata on `pruned_recoverable`.
