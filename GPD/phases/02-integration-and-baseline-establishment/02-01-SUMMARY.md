---
phase: 02-integration-and-baseline-establishment
plan: 01
depth: full
one-liner: "Resolved Zarathustra as OpenClaw queue worker on separate VM; characterized semi-transparent state management with 4 feasible hook points, shifting adapter strategy from LLM compaction wrapping to JSONL ledger analysis"
subsystem: analysis
tags: [runtime-characterization, queue-worker, adapter-strategy, compaction-disambiguation]

requires:
  - phase: 01-ontology-formalization-and-verification
    provides: [forge tool suite, transition table, absence state ontology, violation classification]
provides:
  - "Zarathustra = OpenClaw on separate VM (decision CC-005)"
  - "Queue worker architecture characterized: byte cursor, JSONL ledger, patch lifecycle"
  - "Semi-transparent transparency classification with evidence"
  - "4 hook points for forge integration, all FEASIBLE"
  - "Adapter strategy: Approach 2 (post-hoc JSONL) primary, Approach 1 (wrapper) enhancement"
  - "Risk assessment: queue worker layer LOW risk; inner execution layer HIGH risk (uncharacterized)"
affects: [02-02 adapter design, 02-03 baseline measurement, Phase 4 provenance survival]

methods:
  added: [code inspection, JSONL event analysis, lifecycle reconstruction]
  patterns: [queue worker characterization, cursor-based state loss analysis]

key-files:
  created:
    - docs/zarathustra-identity.md
    - docs/compaction-characterization.md
  modified: []

key-decisions:
  - "CC-005: Zarathustra IS OpenClaw on a separate VM (user confirmed)"
  - "Adapter strategy: Approach 2 (post-hoc JSONL) primary, not Approach 1 (real-time wrapper)"
  - "Inner execution layer LLM compaction deferred to Plan 02-02 investigation"

patterns-established:
  - "Queue worker lifecycle: task.start -> [work + patch lifecycle] -> task.done -> cursor advance"
  - "Ledger event schema: {ts, kind, task_id} required; ok, detail, meta optional with constraints"
  - "Meta allowlisting by event kind prefix (patch.* vs task.* vs other)"

conventions:
  - "Compaction disambiguation: all uses qualified (LLM compaction vs forge trace compression)"
  - "Absence states: 8 canonical per forge_nulls.py"
  - "Unit system: N/A (formal systems research)"

plan_contract_ref: "GPD/phases/02-integration-and-baseline-establishment/02-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-compaction-characterized:
      status: passed
      summary: "The target runtime's state management mechanism is characterized as a queue-based task processor with byte cursor advancement (not LLM context-window summarization). Transparency is SEMI-TRANSPARENT. Four hook points identified, all FEASIBLE. Adapter strategy recommended: Approach 2 (post-hoc JSONL) primary."
      linked_ids: [deliv-compaction-characterization, test-hook-points-identified, test-transparency-classified, ref-mock-experiment, ref-rlm-bridge-pattern]
    claim-runtime-identified:
      status: passed
      summary: "Zarathustra is concretely identified as OpenClaw running on a separate VM. Runtime is pure Python stdlib, directly importable. Integration samples provide ground truth code and event data."
      linked_ids: [deliv-zarathustra-identity, test-runtime-concrete, ref-mock-experiment]
  deliverables:
    deliv-compaction-characterization:
      status: passed
      path: "docs/compaction-characterization.md"
      summary: "Technical characterization document with all 6 required sections: locate codepath, classify transparency, identify hook points, assess attachability, recommend strategy, assess Phase 4 risk."
      linked_ids: [claim-compaction-characterized, test-hook-points-identified, test-transparency-classified]
    deliv-zarathustra-identity:
      status: passed
      path: "docs/zarathustra-identity.md"
      summary: "Identity resolution document with exact runtime name (OpenClaw), deployment location (separate VM), Python importability (direct), and relationship to stock OpenClaw (identical)."
      linked_ids: [claim-runtime-identified, test-runtime-concrete]
  acceptance_tests:
    test-hook-points-identified:
      status: passed
      summary: "4 hook points identified, all with feasibility verdicts: (1) append_ledger() wrapper - FEASIBLE, (2) next_task() wrapper - FEASIBLE, (3) advance_cursor_after_ledger() wrapper - FEASIBLE, (4) ledger file post-hoc parsing - FEASIBLE. Exceeds minimum of 2."
      linked_ids: [claim-compaction-characterized, deliv-compaction-characterization]
    test-transparency-classified:
      status: passed
      summary: "Classified as SEMI-TRANSPARENT with evidence table: task/patch lifecycle transparent via ledger, cursor state semi-transparent, error details semi-transparent (truncation), metadata beyond allowlist opaque, task execution internals opaque."
      linked_ids: [claim-compaction-characterized, deliv-compaction-characterization]
    test-runtime-concrete:
      status: passed
      summary: "Runtime identity concrete enough for import statements: queue_worker.py functions (next_task, append_ledger, load_state, save_state, advance_cursor_after_ledger) are directly importable pure Python stdlib."
      linked_ids: [claim-runtime-identified, deliv-zarathustra-identity]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "MockLM ceiling (100% provenance, 6/6 violations, 87% compression) read from experiment_results.json and compared as context for why characterization matters. The queue worker architecture means provenance survival at this layer is structurally different from the MockLM scenario (cursor advancement vs message summarization)."
    ref-rlm-bridge-pattern:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "PrimordialRLM adapter pattern read from primordial_rlm_bridge.py. The pattern (subclass/wrap runtime, intercept lifecycle events, register as forge artifacts) transfers conceptually. However, the specific hooks differ: queue worker has append_ledger/next_task/advance_cursor vs RLM's _completion_turn/_subcall/_compact_history."
  forbidden_proxies:
    fp-assumed-transparent:
      status: rejected
      notes: "Characterization explicitly classifies transparency as SEMI-TRANSPARENT (not transparent) with evidence table showing which aspects are transparent, semi-transparent, and opaque. Not assumed without evidence."
    fp-generic-characterization:
      status: rejected
      notes: "Characterization is specific to the OpenClaw queue worker: names actual Python functions (append_ledger, next_task, advance_cursor_after_ledger), actual file paths (~/.openclaw/workspace/out/), actual ledger schema, and actual meta allowlists. Could NOT apply to an arbitrary LLM framework."
  uncertainty_markers:
    weakest_anchors:
      - "Inner execution layer (run_queue.py) not characterized -- may involve opaque LLM compaction"
      - "Queue file rotation/deletion behavior in production unknown"
    unvalidated_assumptions:
      - "Integration samples represent the full runtime architecture (run_queue.py may add layers)"
      - "Ledger format is stable across OpenClaw versions"
    competing_explanations: []
    disconfirming_observations:
      - "If run_queue.py reveals opaque LLM compaction at the session layer, the ROADMAP backtracking trigger should be re-evaluated"

comparison_verdicts:
  - subject_id: claim-compaction-characterized
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    metric: "architectural_alignment"
    threshold: "mechanism characterized with transparency classification and hook points"
    verdict: pass
    recommended_action: "Proceed to Plan 02-02 adapter design using identified hook points"
    notes: "The queue worker architecture differs from MockLM scenario (cursor advancement vs message summarization) but forge tools are architecture-agnostic. The provenance model maps cleanly to the queue worker lifecycle."
  - subject_id: claim-compaction-characterized
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-rlm-bridge-pattern
    comparison_kind: prior_work
    metric: "pattern_transferability"
    threshold: "adapter pattern applicable with identified modifications"
    verdict: pass
    recommended_action: "Build PrimordialOpenClawAdapter following PrimordialRLM pattern but targeting queue worker hooks instead of RLM hooks"
    notes: "Core pattern (chamber lifecycle, artifact registration, source_refs) transfers. Hook points are different but equivalent in function."

duration: 25min
completed: 2026-03-16
---

# Plan 02-01: Runtime Identity and Compaction Characterization Summary

**Resolved Zarathustra as OpenClaw queue worker on separate VM; characterized semi-transparent state management with 4 feasible hook points, shifting adapter strategy from LLM compaction wrapping to JSONL ledger analysis**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-16
- **Completed:** 2026-03-16
- **Tasks:** 2 (identity resolution + compaction characterization)
- **Files modified:** 2 created

## Key Results

- **CC-005: Zarathustra = OpenClaw** on separate VM, pure Python stdlib, directly importable [CONFIDENCE: HIGH -- user-confirmed identity, code-verified architecture]
- **Architecture: Queue-based task processor**, not LLM session manager with context-window compaction -- fundamentally different from research assumptions [CONFIDENCE: HIGH -- directly read from source code]
- **Transparency: SEMI-TRANSPARENT** -- structured JSONL ledger provides lifecycle visibility, but meta truncation, detail limits, and execution internals are opaque [CONFIDENCE: HIGH -- classified from code inspection with evidence table]
- **4 hook points, all FEASIBLE:** `append_ledger()`, `next_task()`, `advance_cursor_after_ledger()`, ledger file post-hoc parsing [CONFIDENCE: HIGH -- verified from function signatures and data flow]
- **Strategy shift:** Approach 2 (post-hoc JSONL) recommended as primary (non-invasive, works across VM boundary), Approach 1 (real-time wrapper) as enhancement [CONFIDENCE: MEDIUM -- depends on inner execution layer characterization in Plan 02-02]

## Task Commits

1. **Task 1: Resolve Zarathustra Runtime Identity** - `71f12be` (document)
2. **Task 2: Characterize Target Runtime Compaction Mechanism** - `7213b37` (analyze)

## Files Created/Modified

- `docs/zarathustra-identity.md` -- Identity resolution with runtime details, architecture summary, and impact on integration strategy
- `docs/compaction-characterization.md` -- Full characterization with all 6 required sections, evidence-based transparency classification, hook points with feasibility verdicts, adapter strategy recommendation, and Phase 4 risk assessment

## Next Phase Readiness

Plan 02-02 (adapter design and implementation) can proceed with:
- Concrete runtime target (OpenClaw queue worker on VM)
- 4 identified hook points with known feasibility
- Clear adapter strategy (Approach 2 primary, Approach 1 enhancement)
- Known risk: inner execution layer needs characterization when `run_queue.py` becomes available

**Critical open item for Plan 02-02:** Investigate whether task execution (inside `run_queue.py`) involves LLM compaction at the session layer. If yes, the adapter needs to instrument BOTH layers.

## Contract Coverage

- Claim IDs advanced: claim-compaction-characterized -> passed, claim-runtime-identified -> passed
- Deliverable IDs produced: deliv-compaction-characterization -> docs/compaction-characterization.md (passed), deliv-zarathustra-identity -> docs/zarathustra-identity.md (passed)
- Acceptance test IDs run: test-hook-points-identified -> passed (4 hook points, all FEASIBLE), test-transparency-classified -> passed (SEMI-TRANSPARENT with evidence), test-runtime-concrete -> passed (importable Python functions)
- Reference IDs surfaced: ref-mock-experiment -> completed (read, compare), ref-rlm-bridge-pattern -> completed (read)
- Forbidden proxies rejected: fp-assumed-transparent -> rejected (evidence-based classification), fp-generic-characterization -> rejected (runtime-specific details throughout)
- Decisive comparison verdicts: claim-compaction-characterized vs ref-mock-experiment -> pass, claim-compaction-characterized vs ref-rlm-bridge-pattern -> pass

## Validations Completed

- All 6 required sections present in compaction characterization (verified by automated check)
- Hook points name actual functions (append_ledger, next_task, advance_cursor_after_ledger) not generic descriptions
- Transparency classification is one of the three valid options (semi-transparent) with evidence table
- 4 hook points exceed minimum of 2, all with feasibility verdicts
- Adapter strategy recommendation (Approach 2 primary) with rationale tied to transparency findings
- Zero unqualified uses of "compaction" (2 flagged in automated check were contextually qualified; fixed to be explicit)
- Risk assessment names 4 specific failure modes with severity ratings

## Decisions & Deviations

### Decisions Made

**CC-005 (Zarathustra Identity):** Zarathustra IS OpenClaw on a separate VM. User confirmed directly. This resolves the blocking ambiguity from the research phase.

**Adapter strategy shift:** Research recommended Approach 1 (real-time wrapper of `_compact_history()`) as primary. The actual code has no `_compact_history()` -- it has a queue worker. Strategy shifted to Approach 2 (post-hoc JSONL analysis) as primary, with Approach 1 (wrapping queue worker functions) as enhancement.

### Deviations from Plan

**[Rule 3 - Approximation Breakdown] Research assumptions do not match actual runtime architecture**

- **Found during:** Task 2 (compaction characterization)
- **Issue:** Research assumed LLM context-window compaction (lossy summarization of message history). Actual code is a queue-based task processor with byte cursor advancement.
- **Impact:** The plan's Task 2 action items (locate compaction codepath, characterize token thresholds, check identifierPolicy, etc.) needed reinterpretation for the actual architecture.
- **Fix:** Characterized the actual "forgetting" mechanism (cursor advancement) and the actual state-loss vectors (truncation, meta filtering, resume resets) instead of the assumed ones.
- **Verification:** All 6 sections of the characterization document address the actual architecture, not the assumed one.
- **This is not a scope change (Rule 6):** The objective ("characterize the target runtime's state management and identify hook points") is unchanged. Only the specific mechanism differs from what was expected.

## Open Questions

- Does `run_queue.py` (the task executor that imports `queue_worker.py`) use OpenClaw's session-layer LLM compaction during task execution? (HIGH -- affects inner-layer provenance)
- What is the queue file rotation/deletion policy in production? (MEDIUM -- affects long-term source_ref resolvability)
- Are there additional event kinds beyond the 6 observed in the sample? (LOW -- the adapter should handle unknown kinds gracefully)

## Key Quantities and Uncertainties

| Quantity | Value | Source | Notes |
| --- | --- | --- | --- |
| Hook points identified | 4 | Code inspection of queue_worker.py | All FEASIBLE; may increase when run_queue.py is characterized |
| Ledger event kinds observed | 6 | queue_ledger.sample.jsonl (47 events) | task.start, task.done, patch.proposed, patch.failed, patch.rejected, patch.applied |
| Detail truncation limit | 300 chars | queue_worker.py line 67 | Longer details truncated with "..." suffix |
| Meta allowlist size (patch.*) | 6 keys | queue_worker.py line 71 | patch_file, touched_files, pre_validate, post_validate, tests_status, reason |
| Meta allowlist size (task.*) | 1 key | queue_worker.py line 74 | queue_byte_start only |

## Approximations Used

| Approximation | Valid When | Error Estimate | Breaks Down At |
| --- | --- | --- | --- |
| Integration samples represent full architecture | `run_queue.py` uses only `queue_worker.py` functions | Unknown | If `run_queue.py` adds LLM session management layer |
| Ledger format is stable | OpenClaw version unchanged | N/A | OpenClaw version upgrade could change schema |
| Documentation-based characterization | Stock OpenClaw, no private modifications | Matches user confirmation | If VM has custom patches not reflected in samples |

---

_Phase: 02-integration-and-baseline-establishment, Plan: 01_
_Completed: 2026-03-16_
