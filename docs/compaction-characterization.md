# Target Runtime LLM Compaction Characterization

**Phase:** 02-integration-and-baseline-establishment
**Plan:** 01
**Runtime:** OpenClaw (deployed as "Zarathustra" on separate VM)
**Based on:** Real runtime code at `integration_samples/openclaw/` (commit 028d235)
**Date:** 2026-03-16

---

## Critical Finding: Architecture Mismatch with Research Assumptions

The Phase 2 research (02-RESEARCH.md) assumed the target runtime performs **LLM context-window compaction** -- lossy semantic summarization that replaces old messages with a summary to stay within token limits. This is the mechanism that `PrimordialRLM._compact_history()` wraps in the existing bridge.

**The actual runtime code reveals a fundamentally different architecture.** OpenClaw/Zarathustra operates as a **queue-based task processor** with a byte cursor, append-only JSONL ledger, and patch lifecycle management. There is no LLM context-window compaction in the code provided.

This changes the integration strategy but does NOT invalidate the forge tool suite. The forge tools (chambers, artifacts, provenance refs, typed absence) are agnostic to the specific state-loss mechanism -- they can instrument any system where state is created, modified, or lost.

---

## 1. Locate the "Compaction" Codepath

### What the code actually does

The runtime consists of `queue_worker.py` (imported by `run_queue.py`), which implements a sequential task processor:

**Core data flow:**
```
console_queue.jsonl  -->  queue_worker.next_task()  -->  [execute task]
                                |                            |
                     byte_cursor from                  append_ledger()
                     console_queue_state.json           to queue_ledger.jsonl
                                |                            |
                     advance_cursor_after_ledger()  <---  ledger written
```

**Files and paths (all under `~/.openclaw/workspace/`):**

| File | Path | Role |
| --- | --- | --- |
| Queue | `out/console_queue.jsonl` | Input: task objects, read sequentially |
| State | `out/console_queue_state.json` | Byte cursor tracking queue position |
| Ledger | `out/queue_ledger.jsonl` | Append-only audit log (all events) |

**Functions in queue_worker.py:**

| Function | Purpose | Signature |
| --- | --- | --- |
| `next_task()` | Read next task object from queue after cursor | `() -> tuple[dict, int, int] | None` |
| `load_state()` | Load byte cursor from state file | `() -> dict` (with `byte_cursor`, `updated_at`) |
| `save_state()` | Persist byte cursor atomically | `(byte_cursor: int) -> None` |
| `append_ledger()` | Write event to ledger (task/patch lifecycle) | `(kind, task_id, ok, detail, meta) -> None` |
| `advance_cursor_after_ledger()` | Move cursor forward after ledger write | `(line_end: int) -> None` |
| `_atomic_write()` | Atomic file replacement (write to .tmp, os.replace) | `(path, data) -> None` |
| `_utc_iso_z()` | UTC timestamp string | `() -> str` |

### What triggers state loss (the analog of LLM compaction)

In this architecture, the mechanism analogous to LLM compaction is **cursor advancement**: once the cursor advances past a task in the queue file, that task is no longer visible to the worker. The task's record persists in the queue file and its lifecycle events persist in the ledger, but the worker will never re-process it.

Additionally, the ledger sample reveals several state-loss vectors:

1. **Cursor advancement** (`advance_cursor_after_ledger`): Tasks behind the cursor become invisible to the worker. This is the primary "forgetting" mechanism.

2. **Resume resets** (`overnight.resume` events): Resume events consistently show `queue_byte_start=0`, suggesting the cursor may reset on resume. This would cause re-processing of already-completed tasks, which is the opposite of LLM compaction -- it is state loss through *repetition* rather than *summarization*.

3. **Patch failures without recovery** (`patch.failed` events): The ledger shows 4 patch failures (all `apply_or_post_validate_fail` with `pre_validate=pass`, `post_validate=pass`). The intermediate state of these failed patches (the actual diff content, the validation results, the reason for apply failure) is not captured in the ledger -- only the outcome.

4. **Error truncation** (`detail` field): The `append_ledger()` function truncates `detail` to 300 characters (`detail[:299] + "..."` if `len(detail) > 300`). Long error messages or stack traces lose their tails.

5. **Meta field allowlisting**: The `append_ledger()` function filters metadata keys by event kind. For `patch.*` events, only 6 keys are allowed (`patch_file`, `touched_files`, `pre_validate`, `post_validate`, `tests_status`, `reason`). For `task.*` events, only `queue_byte_start` is allowed. All other metadata is silently dropped.

### What the code does NOT do

There is NO evidence of:
- LLM context-window summarization (no message history, no prompt assembly, no token counting)
- Session JSONL with `branch_summary` entries (the research assumed this format)
- `identifierPolicy` or any identifier preservation during summarization
- A `_compact_history()` equivalent that replaces old messages with summaries
- Token threshold triggers (`autoCompactThreshold`, `softThresholdTokens`)
- Memory flush to durable notes before LLM compaction

**These are stock OpenClaw session-layer features.** The queue worker operates at a different layer -- it is the **task dispatch and execution tracking** layer, not the LLM conversation management layer. The LLM compaction (if it exists in this deployment) would happen inside the task execution itself, which is handled by `run_queue.py` (not provided in the samples).

---

## 2. Transparency Classification

**Classification: SEMI-TRANSPARENT**

**Evidence:**

The queue worker's state management is structurally transparent -- all lifecycle events are written to the JSONL ledger with timestamps, kinds, task IDs, and allowlisted metadata. However, it is not fully transparent because:

| Aspect | Transparency | Evidence |
| --- | --- | --- |
| Task lifecycle (start/done) | Transparent | Every task.start and task.done is logged with timestamp and ok/fail status |
| Patch lifecycle (proposed/applied/failed/rejected) | Transparent | Full patch lifecycle with validation status and touched files |
| Cursor state | Semi-transparent | Cursor value logged in meta but cursor resets on resume are implicit |
| Error details | Semi-transparent | `detail` field truncated to 300 chars; stack traces may be clipped |
| Metadata beyond allowlist | Opaque | Silently dropped by kind-specific allowlists in `append_ledger()` |
| Task execution internals | Opaque | What happens between task.start and task.done is not in this layer |
| Queue file contents | Not logged | The actual task object content is not reflected in the ledger |

**Justification for semi-transparent (not transparent or opaque):**

- NOT transparent: The system silently drops metadata beyond allowlists, truncates details, and does not log queue contents or execution internals. A fully transparent system would preserve all state.
- NOT opaque: The system does maintain a structured, parseable, append-only audit log (the ledger) with timestamps and lifecycle events. State transitions are observable.
- SEMI-TRANSPARENT: The ledger provides a reliable structural skeleton of what happened (which tasks ran, which patches were attempted, what succeeded/failed) but not the full content of what was processed or the detailed reasons for failures.

---

## 3. Hook Points for Forge Integration

### Hook Point 1: `append_ledger()` Wrapper

**Name and location:** `queue_worker.append_ledger()` (line 57 of `queue_worker.py`)

**What it intercepts:** Every lifecycle event -- task.start, task.done, patch.proposed, patch.applied, patch.failed, patch.rejected. This is the single audit entry point for all state changes.

**Integration approach:** Wrap `append_ledger()` to:
1. On `task.start`: Create a forge chamber (or register a new stage in an existing chamber). Create a `v1_stage_artifact` with the task_id as part of the artifact ID.
2. On `task.done` with `ok=True`: Seal the artifact with output. Add `source_refs` to any patch artifacts created during this task.
3. On `task.done` with `ok=False`: Set artifact output_state to `invalid` (task failed) or `unresolved` (task errored). Record the `detail` as the error.
4. On `patch.proposed/applied/failed/rejected`: Register child artifacts under the current task's chamber stage, with `source_refs` pointing to the parent task artifact.

**Feasibility verdict: FEASIBLE**

**Rationale:** The function has a clean signature (`kind, task_id, ok, detail, meta`), is pure Python stdlib, and is the centralized audit point. Wrapping it requires no changes to queue_worker.py -- the adapter can monkey-patch or subclass. The ledger write happens before cursor advancement (the code enforces this ordering), so forge registration can happen at the same point.

### Hook Point 2: `next_task()` Wrapper

**Name and location:** `queue_worker.next_task()` (line 82 of `queue_worker.py`)

**What it intercepts:** Queue consumption -- the moment a task object is dequeued and becomes the active work item. This is the "pre-execution" interception point.

**Integration approach:** Wrap `next_task()` to:
1. Capture the task object returned (including its full content, which is NOT logged to the ledger)
2. Record the byte range (`line_start`, `line_end`) for provenance tracking
3. Create a forge artifact representing the task input, before execution begins
4. Attach `source_refs` to the previous task's artifact (sequential provenance chain)

**Feasibility verdict: FEASIBLE**

**Rationale:** The function returns `(task_obj, line_start, line_end)` which provides both the content and the positional metadata. The task object content is otherwise lost (the ledger only records the `task_id` and `detail`, not the full task body). Wrapping this function captures information that would otherwise be opaque.

### Hook Point 3: `advance_cursor_after_ledger()` Wrapper

**Name and location:** `queue_worker.advance_cursor_after_ledger()` (line 114 of `queue_worker.py`)

**What it intercepts:** The "forgetting" moment -- when the cursor moves past a completed task, making it invisible to future processing. This is the closest analog to LLM compaction's "pruning" of old messages.

**Integration approach:** Wrap to:
1. Before cursor advance: Snapshot the current cursor position
2. After cursor advance: Register a provenance event marking all task objects between old and new cursor positions as `pruned_recoverable` (recoverable because the queue file still contains them)
3. Attach `source_refs` from the cursor-advance artifact back to the task artifacts that are now behind the cursor

**Feasibility verdict: FEASIBLE**

**Rationale:** This is the precise point where state becomes "past" from the worker's perspective. The function takes a single argument (`line_end: int`) and calls `save_state()`, which is atomic. Wrapping adds no complexity.

### Hook Point 4: Ledger File Post-Hoc Parsing

**Name and location:** `~/.openclaw/workspace/out/queue_ledger.jsonl` (file on disk)

**What it intercepts:** Complete historical record of all events, after execution.

**Integration approach:** Parse the JSONL file after task execution to:
1. Reconstruct the task/patch lifecycle as a provenance DAG
2. Identify patterns (repeated failures, cursor resets, orphaned patches)
3. Build forge chambers and artifacts from historical data
4. Compare instrumented vs uninstrumented analysis of the same ledger

**Feasibility verdict: FEASIBLE**

**Rationale:** The ledger is well-structured JSONL with required fields (`ts`, `kind`, `task_id`). The `check_queue_ledger.py` validator confirms the format is stable and validated. Post-hoc parsing is non-invasive and works without modifying the runtime. However, it cannot capture task object contents (only available at `next_task()` call time) or prevent state loss in real time.

---

## 4. Forge Attachability Assessment

### Can forge `source_refs` be attached to queue worker artifacts?

**Yes.** The queue worker's data model maps naturally to forge's artifact model:

| Queue Worker Concept | Forge Artifact Mapping |
| --- | --- |
| Task lifecycle (start -> done) | Stage artifact with `source_refs` to previous tasks |
| Patch lifecycle (proposed -> applied/failed) | Child artifact with `source_refs` to parent task |
| Cursor position | Artifact metadata (byte range) |
| Ledger event | Artifact output (event content) |
| Queue file entry | Artifact input (task object content, via `next_task()` hook) |

**Artifact ID scheme (proposed):**
```
artifact:openclaw:<session_id>:task:<task_id>:r1       -- task artifact
artifact:openclaw:<session_id>:patch:<diff_name>:r1    -- patch artifact
artifact:openclaw:<session_id>:cursor:<byte_pos>:r1    -- cursor state artifact
chamber:openclaw:<session_id>:v1                       -- session chamber
```

### Do artifact IDs survive the "forgetting" mechanism?

**Yes, with qualification.** Cursor advancement does not destroy any data -- the queue file and ledger both persist on disk. The "forgetting" is purely from the worker's processing perspective (it will not re-read old entries). This means:

- Artifact IDs remain resolvable by reading the ledger file directly
- `source_refs` pointing to old artifacts remain valid because the ledger is append-only
- The provenance DAG is fully recoverable from ledger analysis
- This is fundamentally different from LLM compaction, where old messages are *replaced* by a summary

### Can forge distinguish which artifacts were "compacted" vs retained?

**Yes.** The cursor position provides a clear boundary:
- Artifacts with byte range `< cursor`: Behind the cursor (processed, "forgotten" by worker)
- Artifacts with byte range `>= cursor`: Ahead of cursor (pending or active)

The forge adapter can mark behind-cursor artifacts as `pruned_recoverable` (they are recoverable because the ledger and queue file persist) and ahead-of-cursor artifacts as active.

### Limitation: Task execution internals

The queue worker layer does NOT expose what happens during task execution (between `task.start` and `task.done`). If the task execution itself involves LLM calls with context-window management, that LLM compaction would occur at a different layer -- inside `run_queue.py` or whatever the task executor calls. The forge adapter at the queue worker layer cannot observe or instrument that inner compaction.

This is documented as an open question for Plan 02-02: whether the task executor (`run_queue.py`) uses OpenClaw's session-layer LLM compaction, and if so, whether that layer also needs instrumentation.

---

## 5. Adapter Strategy Recommendation

**Recommended: Approach 2 (Post-hoc JSONL transcript analysis) as PRIMARY, with Approach 1 (Real-time wrapper) as ENHANCEMENT**

### Rationale

The research identified three approaches:

| Approach | Research Assumption | Reality | Verdict |
| --- | --- | --- | --- |
| **1: Real-time wrapper** | Wrap `_compact_history()` to intercept LLM compaction | No `_compact_history()` exists; but `append_ledger()`, `next_task()`, and `advance_cursor_after_ledger()` are wrappable | **FEASIBLE as enhancement** |
| **2: Post-hoc JSONL analysis** | Fallback if no wrappable function | The ledger is a well-structured JSONL audit log, purpose-built for exactly this kind of analysis | **PRIMARY approach** |
| **3: Prompt-layer interception** | Emergency fallback if state loss is opaque | State loss (cursor advancement) is NOT opaque -- it is fully trackable via the state file and ledger | **NOT NEEDED** |

### Why Approach 2 is primary

1. **Non-invasive:** Parsing the ledger requires zero modifications to the runtime. The adapter reads `queue_ledger.jsonl` after execution and builds forge chambers from the event stream.

2. **Complete lifecycle visibility:** The ledger already contains the full task and patch lifecycle with timestamps, status, and metadata. This is enough to build provenance DAGs.

3. **Works across VM boundary:** Since OpenClaw runs on a separate VM, post-hoc analysis of ledger files (copied or synced) avoids the complexity of real-time inter-VM instrumentation.

4. **Validated format:** The `check_queue_ledger.py` validator already enforces schema correctness, meaning the adapter can rely on consistent input.

### When to add Approach 1 (real-time wrapping)

Add real-time wrapping of `next_task()` and `append_ledger()` when:
- Task object content needs to be captured (the ledger does not record it)
- Real-time violation detection is needed (post-hoc analysis detects violations but cannot prevent them)
- The adapter needs to attach forge metadata to events as they occur

This would require deploying the adapter code on the VM alongside `queue_worker.py`, which is feasible since the worker is pure Python stdlib.

### Approach 3 is not needed

Prompt-layer interception was designed for opaque state loss. The queue worker's state management is semi-transparent (ledger-based), making Approach 3 unnecessary.

---

## 6. Risk Assessment for Phase 4 Provenance Survival

### Expected fate of `source_refs` after cursor advancement

**LOW RISK for this layer.** Unlike LLM compaction (which replaces messages with a summary, potentially losing artifact IDs), cursor advancement does not modify or destroy any data. The queue file and ledger persist. Provenance chains in the forge DAG remain fully resolvable by reading the files.

| Risk Factor | Severity | Mitigation |
| --- | --- | --- |
| Cursor advancement hides tasks from worker | LOW | Ledger and queue file persist; forge can resolve `source_refs` from files |
| Detail truncation (300 char limit) | MEDIUM | Wrap `append_ledger()` to capture full detail in forge artifact before truncation |
| Meta allowlist drops fields | MEDIUM | Wrap `append_ledger()` to capture full metadata in forge artifact |
| Resume cursor resets cause re-processing | LOW | Ledger is append-only; duplicate events are detectable by timestamp + task_id |
| Queue file deletion/rotation | UNKNOWN | Not observed in samples; needs investigation in production deployment |
| Task execution internals opaque at this layer | HIGH | See "Layered Risk" below |

### Layered Risk: Inner LLM Compaction

**This is the highest-risk item for Phase 4 provenance survival.**

The queue worker layer handles task dispatch. But task execution may involve LLM calls with their own context-window management (the standard OpenClaw session-layer features: `autoCompactThreshold`, `identifierPolicy`, `branch_summary` entries). If that inner layer performs LLM compaction, then:

1. The queue worker adapter would not observe it (it operates at the wrong layer)
2. Provenance chains within a task's execution would break at the LLM compaction boundary
3. The `pruned_recoverable` state would need to be assigned for artifacts whose content was summarized away

**This is the ROADMAP backtracking trigger scenario:** if LLM compaction at the session layer is fully opaque (no `session:compacted` event, no `branch_summary` entries, no `identifierPolicy` enforcement), then the entire provenance survival claim is at risk for the inner execution layer.

### Specific failure modes for Phase 4

1. **Cursor-based state loss (LOW risk):** Forge can track this because the ledger provides full visibility. Provenance DAGs survive because the underlying data persists.

2. **Detail/meta truncation (MEDIUM risk):** Forge can mitigate by wrapping `append_ledger()` to capture full data before truncation. Without wrapping, some provenance metadata is lost.

3. **Inner LLM compaction (HIGH risk):** If task execution uses OpenClaw's session-layer LLM compaction, and that layer is opaque from the queue worker's perspective, then provenance chains within tasks would break. This needs investigation in Plan 02-02 when building the adapter -- specifically, whether `run_queue.py` exposes session-layer events.

4. **Queue file rotation/deletion (UNKNOWN risk):** If the production deployment rotates or deletes old queue files, `source_refs` pointing to tasks in deleted files would become unresolvable (REF.REF_UNRESOLVED). The ledger (append-only) would still have the lifecycle events, but the original task content would be lost.

### ROADMAP Backtracking Evaluation

**The queue worker layer does NOT trigger the backtracking condition.** The backtracking trigger from the ROADMAP is: "LLM compaction is fully opaque (no hook points, no transcript evidence)." At the queue worker layer, state management is semi-transparent with 4 viable hook points.

**The inner execution layer remains UNCHARACTERIZED.** If Plan 02-02 discovers that task execution involves opaque LLM compaction, the backtracking trigger should be re-evaluated at that point.

---

## Appendix A: Ledger Event Schema

Based on `queue_worker.py` and `queue_ledger.sample.jsonl`:

### Required fields (all events)
```json
{
  "ts": "2026-02-19T10:36:12.765426Z",  // UTC ISO 8601 with microseconds
  "kind": "task.start",                   // Event kind (see list below)
  "task_id": "t1"                         // Task or patch identifier
}
```

### Optional fields
```json
{
  "ok": true,                             // Boolean, present on task.done and some patch events
  "detail": "write_file",                 // String, max 300 chars (truncated with "..." if longer)
  "meta": {                               // Object, filtered by event-kind allowlist
    "queue_byte_start": 0                 // Example: task.* events only allow this key
  }
}
```

### Event kinds observed
| Kind | Count in Sample | Description |
| --- | --- | --- |
| `task.start` | 16 | Task dequeued and execution beginning |
| `task.done` | 13 | Task execution completed (check `ok` for success/failure) |
| `patch.proposed` | 9 | Diff file created in `out/patches_pending/` |
| `patch.failed` | 4 | Patch apply or validation failed |
| `patch.rejected` | 3 | Patch rejected (e.g., no change detected) |
| `patch.applied` | 2 | Patch successfully applied with validation passing |

### Meta field allowlists
| Event kind prefix | Allowed meta keys |
| --- | --- |
| `patch.*` | `patch_file`, `touched_files`, `pre_validate`, `post_validate`, `tests_status`, `reason` |
| `task.*` | `queue_byte_start` |
| Other | Empty `{}` (all meta silently dropped) |

## Appendix B: Comparison with Research Assumptions

| Research Assumption | Actual Finding | Impact |
| --- | --- | --- |
| Runtime has LLM context-window compaction (lossy summarization) | Runtime has queue cursor advancement (lossless at file level) | Adapter strategy shifts from wrapping `_compact_history()` to wrapping queue lifecycle |
| Compaction writes `branch_summary` to session JSONL | No session JSONL; instead, append-only `queue_ledger.jsonl` | Post-hoc analysis uses ledger events, not session transcript parsing |
| `identifierPolicy` preserves IDs during compaction | No ID preservation needed -- cursor advancement doesn't modify data | Source_refs survive by default (data persists in files) |
| `session:compacted` event hook requested but not implemented | No compaction events needed -- cursor advancement is the "forgetting" mechanism | Hook points are `append_ledger()`, `next_task()`, `advance_cursor_after_ledger()` |
| TypeScript runtime may block Python interception | Runtime is pure Python stdlib | Direct wrapping is straightforward |
| Need 128K+ token tasks to trigger compaction | No token-based threshold; cursor advances after any task completion | Task size is irrelevant to the "forgetting" mechanism |
| `autoCompactThreshold`, `softThresholdTokens` configuration | No token thresholds in this layer | Configuration concerns apply to inner execution layer only |

---

_Characterization based on code inspection of `integration_samples/openclaw/` (commit 028d235)._
_All uses of "compaction" in this document are qualified per Convention #6._
