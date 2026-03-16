# Zarathustra Runtime Identity Resolution

**Decision:** CC-005
**Phase:** 02-integration-and-baseline-establishment
**Plan:** 01
**Resolved:** 2026-03-16
**Status:** RESOLVED

## Identity

**Zarathustra IS OpenClaw.** The name "Zarathustra" refers to a specific OpenClaw deployment running on a separate VM from the development machine. It is not a fork, wrapper, or distinct project -- it is an OpenClaw instance.

## Concrete Runtime Details

| Property | Value |
| --- | --- |
| **Runtime name** | OpenClaw |
| **Deployment** | Separate VM (not localhost) |
| **Workspace path** | `~/.openclaw/workspace/` |
| **Queue file** | `~/.openclaw/workspace/out/console_queue.jsonl` |
| **State file** | `~/.openclaw/workspace/out/console_queue_state.json` |
| **Ledger file** | `~/.openclaw/workspace/out/queue_ledger.jsonl` |
| **Code evidence** | `queue_worker.py` (stdlib-only, imported by `run_queue.py`) |
| **Integration samples** | `integration_samples/openclaw/` (commit 028d235) |
| **Python importability** | Direct -- `queue_worker.py` is pure Python 3, stdlib only |
| **Relationship to stock OpenClaw** | Identical (not a fork, not a wrapper, not distinct) |

## Architecture Summary (from integration samples)

The runtime operates as a **queue-based task processor**, not a conversational LLM session manager:

1. **Queue** (`console_queue.jsonl`): JSONL file of task objects, read sequentially
2. **State** (`console_queue_state.json`): Byte cursor tracking position in queue file
3. **Ledger** (`queue_ledger.jsonl`): Append-only audit log of all task and patch lifecycle events
4. **Worker** (`queue_worker.py`): Reads next task from queue after cursor, processes it, logs to ledger, advances cursor

This architecture means the "compaction" mechanism is fundamentally different from what the Phase 2 research assumed (LLM context-window summarization). See `docs/compaction-characterization.md` for full analysis.

## Impact on Integration Strategy

### What Transfers from Research

- The adapter pattern concept (wrap runtime operations) still applies
- Forge tool imports (`forge_nulls`, `forge_chamber`, `forge_trace_codec`) remain valid
- The artifact registration pattern (`create_v1_stage_artifact`, `register_stage`) applies
- The JSONL-based observation approach (Approach 2 from research) aligns well

### What Changes from Research Assumptions

- **No LLM compaction to characterize:** The runtime does not do prompt-level summarization. The "compaction" is cursor advancement through a queue file.
- **No `_compact_history()` equivalent to wrap:** There is no in-process message history truncation.
- **Python interception is direct:** `queue_worker.py` is pure stdlib Python, importable and wrappable without language barriers (research flagged potential TypeScript concerns).
- **Event-driven, not turn-based:** The lifecycle is task.start -> task.done / patch lifecycle, not iteration-turn-based like RLM.

### Python Interception Availability

The adapter can directly:
- Import `queue_worker.py` functions (`next_task`, `append_ledger`, `advance_cursor_after_ledger`, `load_state`, `save_state`)
- Wrap `next_task()` to register artifacts on task pickup
- Wrap `append_ledger()` to intercept all lifecycle events
- Wrap `advance_cursor_after_ledger()` to track state advancement

Alternatively, for post-hoc analysis:
- Parse `queue_ledger.jsonl` directly (structured JSONL with `ts`, `kind`, `task_id` fields)
- The ledger format is already well-structured for provenance reconstruction

## Decision Rationale

The user confirmed: "Zarathustra IS OpenClaw. It runs on a separate VM, not this machine." The integration samples at `integration_samples/openclaw/` were pushed directly from the VM (commit 028d235) and contain the actual runtime code.

## Options Considered and Rejected

| Option | Rejected Because |
| --- | --- |
| Private fork of OpenClaw | User confirmed identical, not a fork |
| Distinct non-OpenClaw runtime | User confirmed it IS OpenClaw |
| Claude Code CLI agent | User confirmed separate VM deployment |

---

_Decision CC-005 recorded in Phase 2 Plan 01, Task 1._
