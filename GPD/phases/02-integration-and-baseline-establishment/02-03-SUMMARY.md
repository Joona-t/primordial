---
phase: 02-integration-and-baseline-establishment
plan: 03
depth: full
one-liner: "Designed real-task corpus (3 short + 3 long coding tasks from Zarathustra workflows) and built three-tier measurement framework with bootstrap CIs"
subsystem: validation
tags: [baseline, measurement, structured-logging, task-corpus, bootstrap]

requires:
  - phase: 02-integration-and-baseline-establishment (Plan 02-01)
    provides: Runtime identity (OpenClaw/Zarathustra), compaction characterization, ledger event schema
  - phase: 02-integration-and-baseline-establishment (Plan 02-02)
    provides: OpenClaw adapter (openclaw_adapter.py) for forge-instrumented tier
provides:
  - Real-task corpus specification (docs/task-corpus.md) with 6 tasks across 2 tiers
  - Measurement framework (tools/baseline_measurement.py) computing all 5 canonical metrics
  - Structured logging intermediate baseline (tools/structured_logging_baseline.py) with zero forge imports
  - Bootstrap 95% CI computation for small-sample statistical reporting
affects: [02-04-baseline-execution, phase-3-provenance-survival]

methods:
  added: [bootstrap-ci, three-tier-baseline-comparison, span-based-event-recording]
  patterns: [schema-validation-without-forge, collect-then-compare-metrics]

key-files:
  created:
    - docs/task-corpus.md
    - tools/baseline_measurement.py
    - tools/structured_logging_baseline.py

key-decisions:
  - "CC-006: Task corpus domain = coding/patching (real Zarathustra workflows)"
  - "CC-007: Task corpus scope = 3 short + 3 long, expandable"
  - "CC-008: Benchmark source = real Zarathustra tasks, NOT SWE-bench"

patterns-established:
  - "Three-tier measurement: uninstrumented -> structured logging -> forge instrumented"
  - "Metric collection always produces all 5 canonical metrics per run"
  - "Bootstrap CIs with fixed seed (42) for reproducibility"

conventions:
  - "All uses of 'compaction' qualified per Convention #6"
  - "Metrics formulas match CONVENTIONS.md #7 exactly"
  - "Statistical reporting: bootstrap 95% CIs for N < 30"

plan_contract_ref: "GPD/phases/02-integration-and-baseline-establishment/02-03-PLAN.md#/contract"
contract_results:
  claims:
    claim-task-set-designed:
      status: passed
      summary: "Real-task corpus designed with 6 tasks (3 short, 3 long) from Zarathustra coding/patching workflows. All 3 long tasks target 128K+ tokens via retry cycles modeled after the real ledger sample."
      linked_ids: [deliv-task-corpus, test-compaction-tasks-exist, test-forbidden-proxy-coverage]
    claim-measurement-framework:
      status: passed
      summary: "Measurement framework computes all 5 canonical metrics with bootstrap 95% CIs. Structured logging baseline provides event recording, schema validation, timing, token counting, and error recording without any forge features."
      linked_ids: [deliv-measurement-framework, deliv-structured-logging, test-metrics-defined, test-structured-logging-distinct]
  deliverables:
    deliv-task-corpus:
      status: passed
      path: "docs/task-corpus.md"
      summary: "6-task corpus: TASK-S1 (license header), TASK-S2 (lint fix), TASK-S3 (unit test), TASK-L1 (JSONL validator with retries), TASK-L2 (config refactor with retries), TASK-L3 (cursor reset detection with retries)"
      linked_ids: [claim-task-set-designed, test-compaction-tasks-exist, test-forbidden-proxy-coverage]
    deliv-measurement-framework:
      status: passed
      path: "tools/baseline_measurement.py"
      summary: "Implements all 6 required functions: run_task_uninstrumented, run_task_structured_logging, run_task_forge_instrumented, collect_metrics, bootstrap_ci, persist_results"
      linked_ids: [claim-measurement-framework, test-metrics-defined]
    deliv-structured-logging:
      status: passed
      path: "tools/structured_logging_baseline.py"
      summary: "Implements event recording, schema validation, timing, token counting, error recording. Zero forge imports verified."
      linked_ids: [claim-measurement-framework, test-structured-logging-distinct]
  acceptance_tests:
    test-compaction-tasks-exist:
      status: passed
      summary: "3 long tasks (TASK-L1, TASK-L2, TASK-L3) all target 128K+ tokens via retry cycles."
      linked_ids: [claim-task-set-designed, deliv-task-corpus]
    test-forbidden-proxy-coverage:
      status: passed
      summary: "fp-short-tasks: 3 tasks >= 128K (L1-L3). fp-shallow-traces: 3 tasks with depth >= 3 (L1 depth 5+, L2 depth 5+, L3 depth 6+). fp-synthetic-only: all tasks use real Zarathustra workflows."
      linked_ids: [claim-task-set-designed, deliv-task-corpus]
    test-metrics-defined:
      status: passed
      summary: "All 5 canonical metrics computed: reachability_fraction, compression_ratio, vs_vanilla_pct, detection_rate (via compute_detection_rate), false_positive_rate (via compute_false_positive_rate)."
      linked_ids: [claim-measurement-framework, deliv-measurement-framework]
    test-structured-logging-distinct:
      status: passed
      summary: "Zero forge imports in structured_logging_baseline.py: grep confirmed no import/from statements reference forge_nulls, forge_chamber, forge_trace_codec, or forge_reversible_summary."
      linked_ids: [claim-measurement-framework, deliv-structured-logging]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "MockLM ceiling values (reachability 1.0, detection 6/6, compression 87%) used as order-of-magnitude anchors in collect_metrics() documentation and code comments."
    ref-vanilla-baseline:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "vanilla_baseline.py methodology reviewed. New measurement framework extends the approach to real tasks with three tiers instead of two."
  forbidden_proxies:
    fp-short-tasks:
      status: rejected
      notes: "3 long tasks (L1-L3) all target 128K+ tokens. Not all-short."
    fp-mockml-tasks:
      status: rejected
      notes: "All tasks use real Zarathustra workflows. No MockLM scenarios."
    fp-structlog-has-forge:
      status: rejected
      notes: "structured_logging_baseline.py has zero forge imports. Separation verified by grep."
  uncertainty_markers:
    weakest_anchors:
      - "Token count estimates use chars/4 heuristic, which can be off by 20-40% for code-heavy content"
      - "Long task retry counts (3-7) are estimates based on ledger sample patterns, not guarantees"
    unvalidated_assumptions:
      - "LLM runtime (Claude Code) will trigger context management at 128K+ tokens -- not verified until Plan 02-04 execution"
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-measurement-framework
    subject_kind: claim
    subject_role: supporting
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    metric: order_of_magnitude
    threshold: "uninstrumented detection ~ 0, forge detection approaching 6/6"
    verdict: pass
    recommended_action: "Execute baselines in Plan 02-04 to produce real numbers"
    notes: "Framework code documents expected O(M) values matching MockLM anchors; actual comparison deferred to execution"

duration: 15min
completed: 2026-03-16
---

# Plan 02-03: Task Corpus and Measurement Framework Summary

**Designed real-task corpus (3 short + 3 long coding tasks from Zarathustra workflows) and built three-tier measurement framework with bootstrap CIs**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 (1 checkpoint:decision resolved by user, 1 auto)
- **Files created:** 3

## Key Results

- Task corpus: 6 tasks (S1-S3 short, L1-L3 long) drawn from real Zarathustra patch lifecycle
- Long tasks modeled after the ledger sample's patch1-7 retry pattern (5-7 retries growing context past 128K tokens)
- Measurement framework computes all 5 CONVENTIONS.md #7 metrics with bootstrap 95% CIs
- Structured logging baseline verified to have zero forge imports (differential separation preserved)
- All 354 existing tests pass (regression clean)

## Task Commits

1. **Task 1: Design Real-Task Corpus** - `8328818` (docs)
2. **Task 2: Build Measurement Framework + Structured Logging Baseline** - `2eca75e` (implement)

## Files Created/Modified

- `docs/task-corpus.md` -- 6-task corpus specification with inclusion/exclusion criteria, token estimates, forbidden proxy coverage
- `tools/baseline_measurement.py` -- Three-tier measurement framework: run_task_uninstrumented(), run_task_structured_logging(), run_task_forge_instrumented(), collect_metrics(), bootstrap_ci(), persist_results()
- `tools/structured_logging_baseline.py` -- Intermediate baseline: Span, SchemaValidator, StructuredLoggingSession, process_ledger_with_logging()

## Next Phase Readiness

- Task corpus ready for Plan 02-04 baseline execution
- Measurement framework ready to orchestrate all three tiers
- Structured logging baseline ready as intermediate tier
- All forbidden proxies explicitly rejected
- Missing: actual task execution against a runtime (deferred to Plan 02-04)

## Contract Coverage

- Claim IDs: claim-task-set-designed -> passed, claim-measurement-framework -> passed
- Deliverable IDs: deliv-task-corpus -> passed, deliv-measurement-framework -> passed, deliv-structured-logging -> passed
- Acceptance test IDs: test-compaction-tasks-exist -> passed, test-forbidden-proxy-coverage -> passed, test-metrics-defined -> passed, test-structured-logging-distinct -> passed
- Reference IDs: ref-mock-experiment -> read+compare, ref-vanilla-baseline -> read
- Forbidden proxies: fp-short-tasks -> rejected, fp-mockml-tasks -> rejected, fp-structlog-has-forge -> rejected
- Comparison verdicts: claim-measurement-framework vs ref-mock-experiment -> pass (O(M) consistency)

## Validations Completed

- Forge import separation: `grep` confirms zero forge imports in structured_logging_baseline.py
- SchemaValidator: validates required fields, null detection, type checking
- Span lifecycle: creation, attributes, events, end, serialization
- StructuredLoggingSession: turn/tool_call context managers, token tracking, error capture
- process_ledger_with_logging: processes real sample ledger (47 events)
- bootstrap_ci: produces valid intervals, handles edge cases (single value, empty list)
- collect_metrics: computes all 5 canonical metrics per CONVENTIONS.md #7
- persist_results: writes raw_results.json, metrics.json, aggregate_metrics.json
- Regression: all 354 existing tests pass

## Decisions Made

- CC-006: Coding/patching domain chosen (matches what the ledger shows Zarathustra actually does)
- CC-007: 3 short + 3 long scope (Option C size at Option A domain), expandable if CV > 50%
- CC-008: Real Zarathustra tasks, not SWE-bench (testing actual failure modes, not external benchmarks)
- Used Python stdlib `random` as fallback when numpy unavailable for bootstrap CI
- Fixed random seed (42) for bootstrap reproducibility
- Schema validation uses `error_message` key (not `message`) to avoid logging LogRecord key collision

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Code Bug] Logging LogRecord key collision**

- **Found during:** Task 2 (structured_logging_baseline.py)
- **Issue:** Error record dict used `message` key which conflicts with Python logging's reserved LogRecord attribute
- **Fix:** Renamed to `error_message` in the error record dict; used safe keys in logging `extra` parameter
- **Files modified:** tools/structured_logging_baseline.py
- **Verification:** Error recording test passes without KeyError
- **Committed in:** 2eca75e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 code bug)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Open Questions

- Will long tasks actually reach 128K+ tokens in practice? (Estimated from ledger patterns; actual measurement in Plan 02-04)
- What is the LLM compaction threshold for Claude Code sessions? (Deferred investigation per user direction)
- How does the inner execution layer (run_queue.py) manage LLM context? (From compaction characterization, Section 6)

---

_Phase: 02-integration-and-baseline-establishment_
_Plan: 03_
_Completed: 2026-03-16_
