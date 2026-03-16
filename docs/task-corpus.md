# Real-Task Corpus: Coding/Patching Domain

**Phase:** 02-integration-and-baseline-establishment
**Plan:** 03
**Domain:** Coding/patching (real Zarathustra/OpenClaw workflows)
**Scope:** 3 short + 3 long tasks (expandable)
**Benchmark source:** Real Zarathustra tasks, NOT SWE-bench

---

## Design Decisions

- **CC-006:** Task corpus domain = coding/patching (real Zarathustra workflows)
- **CC-007:** Task corpus scope = 3 short + 3 long (Option C size, Option A domain), expandable
- **CC-008:** Benchmark source = real Zarathustra tasks, NOT SWE-bench

---

## Inclusion/Exclusion Criteria

### Inclusion

1. **Domain match:** Tasks must exercise the patch lifecycle that Zarathustra/OpenClaw actually performs: propose, validate, test, apply/reject.
2. **Observable lifecycle:** Each task must produce ledger events parseable by `openclaw_adapter.py` (task.start, task.done, patch.* events).
3. **Reproducibility:** Fixed prompt text, deterministic file content, success criteria checkable by automated validation (exit code, file diff, test pass).
4. **Provenance depth:** Long tasks must produce provenance chains of depth >= 3 (multi-step reasoning: read -> modify -> validate -> retry).
5. **Real failure modes:** At least 2 tasks must include expected patch failure/retry cycles (matching the patch1-7 pattern from the ledger sample).

### Exclusion

1. **Synthetic injection:** No tasks where violations are artificially injected (that is the MockLM experiment's job, already completed in Phase 1).
2. **External dependencies:** No tasks requiring network access, API keys, or databases not present in the test workspace.
3. **Unbounded scope:** No tasks where the LLM could wander indefinitely (every task has a maximum iteration cap).

---

## Statistical Requirements

- **Runs per task:** N >= 3 per baseline tier (uninstrumented, structured logging, forge)
- **Total runs:** 6 tasks x 3 tiers x 3 runs = 54 runs minimum
- **Reporting:** Bootstrap 95% CIs on all metrics with N < 30 samples
- **Reproducibility:** Fixed random seeds where applicable; deterministic workspace state at task start
- **Cost model:** Session time on Claude Code subscription (not per-token API cost)

---

## Task Definitions

### SHORT Tasks (single-step patches, expected < 32K tokens)

These tasks calibrate the baseline: each is a simple, single-file operation that completes in one propose-apply cycle. Context stays small. No retries expected.

#### TASK-S1: Add License Header

| Field | Value |
|---|---|
| **ID** | `TASK-S1` |
| **Tier** | SHORT |
| **Expected tokens** | ~5K-10K |
| **Expected provenance depth** | 2 (read file -> patch file) |
| **Expected patch lifecycle** | 1 propose -> 1 apply |
| **Expected ledger events** | task.start, patch.proposed, patch.applied, task.done |

**Prompt:**
```
Add a standard MIT license header comment to the top of tools/check_queue_ledger.py.
The header should include: copyright year 2026, author "OpenClaw Contributors",
and the SPDX identifier "SPDX-License-Identifier: MIT".
```

**Workspace setup:**
- Provide `tools/check_queue_ledger.py` as a small Python script (30-50 lines) without a license header.

**Success criteria:**
- File begins with a comment block containing "MIT", "2026", "SPDX-License-Identifier".
- Rest of file unchanged (diff is header-only addition).
- Script still runs: `python3 tools/check_queue_ledger.py --help` exits 0.

---

#### TASK-S2: Fix Linting Error

| Field | Value |
|---|---|
| **ID** | `TASK-S2` |
| **Tier** | SHORT |
| **Expected tokens** | ~5K-10K |
| **Expected provenance depth** | 2 (identify error -> fix error) |
| **Expected patch lifecycle** | 1 propose -> 1 apply |
| **Expected ledger events** | task.start, patch.proposed, patch.applied, task.done |

**Prompt:**
```
Fix the undefined variable error in queue_worker.py. The function append_ledger()
references 'validation_status' on line 71 but the variable is named 'pre_validate'
in the meta allowlist. Fix the reference to use the correct variable name.
```

**Workspace setup:**
- Provide `queue_worker.py` with a deliberate `validation_status` reference error in the allowlist (mirroring the actual NameError seen in the ledger sample at line 7: `NameError("name 'validation_status' is not defined")`).

**Success criteria:**
- `python3 -c "import queue_worker"` succeeds (no NameError).
- The fix changes `validation_status` to `pre_validate` (or removes the stale reference).
- No other lines modified.

---

#### TASK-S3: Add Unit Test

| Field | Value |
|---|---|
| **ID** | `TASK-S3` |
| **Tier** | SHORT |
| **Expected tokens** | ~8K-15K |
| **Expected provenance depth** | 2-3 (read code -> write test -> verify test passes) |
| **Expected patch lifecycle** | 1 propose -> 1 apply |
| **Expected ledger events** | task.start, patch.proposed, patch.applied, task.done |

**Prompt:**
```
Write a unit test for the load_state() function in queue_worker.py. The test should
cover three cases: (1) state file does not exist (returns default with byte_cursor=0),
(2) state file exists with valid JSON, (3) state file exists with corrupted/non-dict
content (returns default). Save as tests/test_load_state.py.
```

**Workspace setup:**
- Provide `queue_worker.py` (the real code from integration_samples).
- Ensure `tests/` directory exists but has no `test_load_state.py`.

**Success criteria:**
- `tests/test_load_state.py` exists and contains 3 test functions.
- `python3 -m pytest tests/test_load_state.py -v` passes with 3 passed.

---

### LONG Tasks (multi-step with retry loops, expected 128K+ tokens)

These tasks exercise the self-modification cycle that Zarathustra naturally performs. Each is designed to trigger patch failures and retries, growing context through the propose -> validate -> fail -> retry loop observed in the real ledger (patches 1-7 attempting the same validator task).

The 128K+ token expectation comes from the retry cycle: each failed attempt adds the failure output, the retry prompt, and the next attempt's output to the context. With 3-5 retries at ~20-30K tokens each, plus the original context, total context grows past 128K.

#### TASK-L1: Add JSONL Schema Validator (The Ledger Validator Task)

| Field | Value |
|---|---|
| **ID** | `TASK-L1` |
| **Tier** | LONG |
| **Expected tokens** | 128K-200K (based on 5-7 retries at ~25K each) |
| **Expected provenance depth** | 5+ (read spec -> write code -> test -> fail -> retry -> ... -> succeed) |
| **Expected patch lifecycle** | 3-7 propose -> 1-4 fail -> 0-3 reject -> 1 apply |
| **Expected ledger events** | task.start, N*(patch.proposed, patch.failed), patch.proposed, patch.applied, task.done |
| **Modeled after** | Ledger sample: patches 1-7 all attempting `add_queue_ledger_validator` with repeated `apply_or_post_validate_fail` |

**Prompt:**
```
Create a JSONL schema validator tool at tools/check_queue_ledger.py that:
1. Reads a queue_ledger.jsonl file
2. Validates each line has required fields: ts (ISO 8601), kind (string), task_id (string)
3. Validates optional fields: ok (boolean), detail (string, max 300 chars), meta (object)
4. Validates meta field allowlists per event kind:
   - patch.*: patch_file, touched_files, pre_validate, post_validate, tests_status, reason
   - task.*: queue_byte_start
   - other: empty meta only
5. Reports validation errors with line numbers
6. Exits 0 if all valid, 1 if any errors

The validator must pass when run against the sample ledger file at
integration_samples/openclaw/queue_ledger.sample.jsonl.
```

**Workspace setup:**
- Provide `queue_worker.py` (for the allowlist spec).
- Provide `integration_samples/openclaw/queue_ledger.sample.jsonl` (the real sample).
- Post-validation check: run the produced script against the sample ledger.
- **Critical:** The post-validation must use the _actual_ ledger sample, which has edge cases (STOP task_id, `no_change` details, events with no `ok` field). These edge cases cause patch failures in naive implementations, forcing the retry loop.

**Success criteria:**
- `tools/check_queue_ledger.py` exists.
- `python3 tools/check_queue_ledger.py integration_samples/openclaw/queue_ledger.sample.jsonl` exits 0.
- The validator catches at least: missing `ts`, missing `kind`, invalid meta keys.

**Why this triggers retries:** The sample ledger has subtle edge cases (the STOP task_id, the `patch.rejected` event where task_id is literally `"patch.rejected"`, events without an `ok` field). Naive implementations fail post-validation against the sample and must retry.

---

#### TASK-L2: Refactor Meta Allowlist to Config-Driven

| Field | Value |
|---|---|
| **ID** | `TASK-L2` |
| **Tier** | LONG |
| **Expected tokens** | 128K-180K (based on 3-5 retries for test failures) |
| **Expected provenance depth** | 5+ (read code -> design config -> implement -> test -> fail -> fix -> retest) |
| **Expected patch lifecycle** | 2-5 propose -> 1-3 fail -> 1 apply |
| **Expected ledger events** | task.start, N*(patch.proposed, patch.failed/rejected), patch.applied, task.done |

**Prompt:**
```
Refactor the meta field allowlist in queue_worker.py from hardcoded sets to a
config-driven approach:

1. Create a meta_allowlist.json config file with this structure:
   {
     "patch.*": ["patch_file", "touched_files", "pre_validate", "post_validate",
                  "tests_status", "reason"],
     "task.*": ["queue_byte_start"],
     "default": []
   }

2. Modify append_ledger() to load allowlists from meta_allowlist.json instead of
   hardcoded sets. Fall back to hardcoded defaults if config file is missing.

3. Write tests proving:
   a. With config file: allowlist matches config
   b. Without config file: allowlist matches current hardcoded behavior
   c. With config adding a new key "custom_field" to "task.*": the new key is
      allowed in task.* events

All existing behavior must be preserved (the sample ledger must still validate
identically before and after refactoring).
```

**Workspace setup:**
- Provide the real `queue_worker.py` from integration_samples.
- Provide the sample ledger for regression validation.

**Success criteria:**
- `meta_allowlist.json` exists with the specified structure.
- `queue_worker.py` loads from config, falls back to hardcoded.
- All 3 test scenarios pass.
- `python3 -c "import queue_worker; queue_worker.append_ledger('task.start', task_id='test', meta={'queue_byte_start': 0})"` succeeds.
- Existing ledger validation still passes.

**Why this triggers retries:** The refactoring must preserve exact existing behavior including the edge case where `os.path.dirname(LEDGER)` must exist. Config loading adds file-not-found paths. Test setup is fiddly with temporary directories and mock configs.

---

#### TASK-L3: Add Cursor Reset Detection and Warning

| Field | Value |
|---|---|
| **ID** | `TASK-L3` |
| **Tier** | LONG |
| **Expected tokens** | 128K-200K (based on 4-6 retries for logic and test failures) |
| **Expected provenance depth** | 6+ (analyze ledger pattern -> design detection -> implement -> test with real data -> fail -> iterate) |
| **Expected patch lifecycle** | 3-6 propose -> 2-4 fail -> 1 apply |
| **Expected ledger events** | task.start, N*(patch.proposed, patch.failed/rejected), patch.applied, task.done |
| **Modeled after** | Ledger sample: resume1, resume3-7 all show `queue_byte_start=0`, indicating cursor resets |

**Prompt:**
```
The queue ledger shows a pattern where overnight.resume events reset the cursor
to byte 0, causing re-processing of already-completed tasks. Implement cursor
reset detection:

1. Add a detect_cursor_resets(ledger_path) function to queue_worker.py that:
   a. Reads the ledger and finds all task.start events with queue_byte_start=0
      that occur after any task.done event
   b. Returns a list of {task_id, timestamp, previous_task_done_at} for each reset
   c. Logs a WARNING for each detected reset

2. Add an --audit flag to the ledger validator (check_queue_ledger.py, from TASK-L1
   or provided) that calls detect_cursor_resets() and reports findings.

3. Write tests covering:
   a. Ledger with no resets -> empty list
   b. Ledger with one reset -> list of length 1 with correct task_id
   c. The sample ledger -> detects the actual resume-based resets (resume1 through resume7)
   d. Edge case: first task.start with byte_cursor=0 is NOT a reset (it's the initial start)

Test against the real sample ledger: resume events 1, 3-7 are all cursor resets.
```

**Workspace setup:**
- Provide `queue_worker.py` and `check_queue_ledger.py` (either from TASK-L1 output or pre-built).
- Provide the sample ledger.

**Success criteria:**
- `detect_cursor_resets()` function exists in `queue_worker.py`.
- Running against the sample ledger detects 6 cursor resets (resume1, resume3-7).
- `check_queue_ledger.py --audit` reports cursor resets.
- All 4 test cases pass.

**Why this triggers retries:** The detection logic has edge cases: the very first task.start at byte 0 is legitimate (not a reset). The resume events in the sample ledger have varying patterns. Distinguishing "first start" from "reset" requires tracking state across events.

---

## Token Count Estimation

Token counts are estimated using the chars/4 heuristic.

**Known limitation (from plan approximation spec):** This heuristic can be off by 20-40% for code-heavy content. If actual token counts differ significantly from estimates, document the discrepancy and adjust tier classification accordingly. Actual tokenizer measurement (tiktoken) should be used during baseline execution in Plan 02-04 if available.

| Task | Tier | Estimated Tokens | Estimation Basis |
|---|---|---|---|
| TASK-S1 | SHORT | 5K-10K | Single file read + header patch; no retries |
| TASK-S2 | SHORT | 5K-10K | Single file read + one-line fix; no retries |
| TASK-S3 | SHORT | 8K-15K | File read + test file creation; minimal retries |
| TASK-L1 | LONG | 128K-200K | Based on ledger sample: 5-7 retries, each adding ~25K context |
| TASK-L2 | LONG | 128K-180K | Multi-file refactoring with 3-5 retry cycles |
| TASK-L3 | LONG | 128K-200K | Pattern analysis + implementation + edge-case fixing, 4-6 retries |

### Forbidden Proxy Coverage

| Forbidden Proxy | Guard | Coverage |
|---|---|---|
| fp-short-tasks | At least 3 tasks >= 128K tokens | TASK-L1, TASK-L2, TASK-L3 (3 long tasks targeting 128K+) |
| fp-mockml-tasks | Task corpus uses real tasks, not MockLM | All tasks use real Zarathustra workflows; no MockLM |
| fp-shallow-traces | At least 3 tasks with provenance depth >= 3 | TASK-L1 (5+), TASK-L2 (5+), TASK-L3 (6+) |

---

## Compaction Threshold Investigation

**Status:** Deferred to Plan 02-01 characterization work (per user direction).

The compaction characterization (docs/compaction-characterization.md) found that the queue worker layer does NOT perform LLM context-window compaction -- it uses cursor-based "forgetting." The 128K+ token threshold in this corpus design assumes that the LLM runtime (Claude Code in this case) will trigger its own context-window management when sessions grow large enough.

If no tasks naturally reach 128K tokens due to faster-than-expected resolution, the corpus can be expanded with additional retry-inducing constraints (tighter validation, more edge cases in test data).

---

## Workspace Template

Each task run requires a clean workspace with:

1. **Working directory:** Temporary directory with the files specified in "Workspace setup"
2. **Queue file:** `out/console_queue.jsonl` containing the task prompt
3. **State file:** `out/console_queue_state.json` with `byte_cursor: 0`
4. **Ledger file:** `out/queue_ledger.jsonl` (empty at start)

After execution:
1. Check success criteria
2. Parse the resulting `queue_ledger.jsonl` through the measurement framework
3. Record raw token counts, duration, ledger events

---

## Expansion Path

If 6 tasks prove insufficient for statistical significance (CV > 50% on key metrics):

1. **Add MEDIUM tier:** Tasks in the 32K-128K range (e.g., multi-file linting fixes, test suite additions)
2. **Add more LONG tasks:** Additional self-modification cycles targeting different code patterns
3. **Increase N:** Raise from N=3 to N=5 runs per task per tier

---

_Designed: 2026-03-16_
_Domain decision: CC-006_
_Scope decision: CC-007_
_Benchmark decision: CC-008_
