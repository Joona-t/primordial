---
phase: 06-genuine-compaction
plan: 02
depth: full
one-liner: "Built experiment orchestration infrastructure: GenuineCompactionRunner (API + dry-run, 30 tests) and 3 Track A task templates with validated provenance chains (33 tests)"
subsystem: [orchestration, experiment-design]
tags: [compaction, runner, task-templates, provenance-chains, dry-run, API-integration]

requires:
  - phase: 06-genuine-compaction
    plan: 01
    provides: [summary_parser.py, embedding_similarity.py]
  - phase: 01-formalism-and-validation
    provides: [V1_ABSENCE_STATES, ARTIFACT_ID_PATTERN, forge_nulls.py]
  - phase: 05-semantic-provenance-fidelity
    provides: [SPFMetric, jaccard_similarity, weighted_token_overlap]
provides:
  - genuine_compaction_runner.py: GenuineCompactionRunner, RunnerConfig, CompactionSnapshot, BoundaryCapture, TrialResult
  - task_templates.py: TaskTemplate, CodingTaskTemplate, DebuggingTaskTemplate, SpecificationTaskTemplate
affects: [06-03 Track A experiments, 06-04 Track B experiments, 06-05 Track C ablation]

methods:
  added: [compact_20260112 API integration with pause_after_compaction, dry-run mode for pipeline validation, exponential backoff retry logic, provenance chain depth computation via DAG walk]
  patterns: [template method for task iteration, dataclass-based config/result, JSONL structured logging]

key-files:
  created:
    - tools/genuine_compaction_runner.py
    - tools/test_genuine_compaction_runner.py
    - tools/task_templates.py
    - tools/test_task_templates.py

key-decisions:
  - "Dry-run simulates LLM compaction at midpoint: first half of artifacts lost, second half surviving with 5 IDs in summary"
  - "Retry logic: exponential backoff (2, 4, 8s) with max 3 retries, each retry logged to FindingsLedger"
  - "Source ref chain: each artifact references its predecessor; every 3rd also references 3-back for DAG depth"
  - "Boundary capture integrates summary_parser + embedding_similarity for three-tier classification at capture time"

patterns-established:
  - "Template method: TaskTemplate base class with _iteration_prompts() override for category-specific content"
  - "Structured trial results: RunnerConfig -> GenuineCompactionRunner.run_trial() -> TrialResult -> JSONL"
  - "Boundary capture: pre/post CompactionSnapshot + tier classification + SPF measurement in single capture_boundary() call"

conventions:
  - "artifact ID format: artifact:<run>:iter:<n>:r1 (CONVENTIONS.md #5)"
  - "compaction disambiguation: forge=lossless, LLM=lossy (CONVENTIONS.md #6)"
  - "all metrics dimensionless (CONVENTIONS.md #7)"
  - "JSONL mode field: 'live' for API calls, 'dry-run' for simulated"

plan_contract_ref: "GPD/phases/06-genuine-compaction/06-02-PLAN.md#/contract"
contract_results:
  claims:
    claim-runner:
      status: passed
      summary: "GenuineCompactionRunner correctly captures LLM compaction boundaries (pre/post snapshots), computes all metrics (structural_reachability, artifact_id_survival, compression_ratio, degraded_fraction, spf_scores), and logs to JSONL. Dry-run validated end-to-end."
      linked_ids: [deliv-runner, deliv-runner-tests, test-dry-run-pipeline, ref-mock-experiment, ref-compaction-api]
    claim-templates:
      status: passed
      summary: "All 3 Track A task templates generate 20 distinct iteration prompts with unique artifact IDs, provenance chains of depth >= 5 after 10 iterations, substantial content per iteration (>200 chars prompt, ~500-1000 token expected responses), and valid source_ref DAGs (no dangling refs, no cycles)."
      linked_ids: [deliv-templates, deliv-template-tests, test-template-depth, ref-mock-experiment]
  deliverables:
    deliv-runner:
      status: passed
      path: "tools/genuine_compaction_runner.py"
      summary: "Implements GenuineCompactionRunner with run_trial(), capture_boundary(), log_results(). Includes RunnerConfig, CompactionSnapshot, BoundaryCapture, TrialResult dataclasses. API integration via compact_20260112 with pause_after_compaction. Retry logic with exponential backoff."
      linked_ids: [claim-runner, test-dry-run-pipeline]
    deliv-templates:
      status: passed
      path: "tools/task_templates.py"
      summary: "Implements TaskTemplate base class + CodingTaskTemplate (A1, auth system build), DebuggingTaskTemplate (A2, 4-bug hypothesis-test-revise chains), SpecificationTaskTemplate (A3, 12-requirement notification system). All with provenance chain building."
      linked_ids: [claim-templates, test-template-depth]
    deliv-runner-tests:
      status: passed
      path: "tools/test_genuine_compaction_runner.py"
      summary: "30 tests: config validation, snapshot serialization, dry-run E2E (7 tests), JSONL schema (4 tests), metric computation (3 tests), boundary capture (3 tests), retry logic (3 tests), summary_parser integration, embedding_similarity integration, MockLM anchor comparison"
      linked_ids: [claim-runner]
    deliv-template-tests:
      status: passed
      path: "tools/test_task_templates.py"
      summary: "33 tests: base class (3), coding template (8), debugging template (7), spec template (7), cross-template provenance depth (2), source ref integrity (2), token estimation (2), runner integration (1)"
      linked_ids: [claim-templates]
  acceptance_tests:
    test-dry-run-pipeline:
      status: passed
      summary: "Dry-run produces valid JSONL with all required fields. structural_reachability=0.5 (half survive by design), artifact_id_survival=0.5, compression_ratio=107.27, degraded_fraction=0.5, spf_scores present with jaccard/token_overlap/weighted_overlap. All metric values in valid ranges."
      linked_ids: [claim-runner, deliv-runner, deliv-runner-tests]
    test-template-depth:
      status: passed
      summary: "All 3 templates produce provenance chains of depth >= 5 after 10 iterations. All artifact IDs unique (20 per template). All source_refs resolve (no dangling). No cycles in DAG. Depth >= 3 after only 5 iterations (fp-shallow-traces rejected)."
      linked_ids: [claim-templates, deliv-templates, deliv-template-tests]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [compare]
      missing_actions: []
      summary: "MockLM anchor verified: compute_artifact_survival on fully-present IDs returns survival_rate=1.0, matching MockLM ceiling. Dry-run on simulated data produces structural_reachability=0.5 (by design: half survive) which is consistent with the ceiling being 1.0 for uncompacted data."
    ref-compaction-api:
      status: completed
      completed_actions: [read]
      missing_actions: []
      summary: "compact_20260112 API integrated: context_management with edits[].type='compact_20260112', trigger.type='input_tokens', pause_after_compaction=True, optional instructions parameter for provenance-aware summarization. Beta header 'compact-20260112' included in API calls."
  forbidden_proxies:
    fp-short-tasks:
      status: rejected
      notes: "All 3 templates produce prompts > 200 chars per iteration. 20 iterations of prompts total > 1500 words across all templates. Expected response tokens 500-1000 per iteration, easily reaching 80K threshold in 15-20 iterations."
    fp-shallow-traces:
      status: rejected
      notes: "All 3 templates reach provenance depth >= 5 after 10 iterations and >= 3 after 5 iterations. Source ref chains include both sequential (predecessor) and skip (3-back) references for DAG depth."
  uncertainty_markers:
    weakest_anchors:
      - "compact_20260112 API behavior in live mode untested — dry-run validates pipeline logic only"
      - "Token estimates are approximate — actual compaction threshold crossing depends on model response length"
    unvalidated_assumptions:
      - "Dry-run simulated LLM compaction preserves exactly the second half of artifacts — real LLM behavior may differ"
    competing_explanations: []
    disconfirming_observations: []

comparison_verdicts:
  - subject_id: claim-runner
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: baseline
    metric: "structural_reachability on fully-surviving data"
    threshold: "survival_rate = 1.0 for all-present IDs"
    verdict: pass
    recommended_action: "Run live API trial (Plan 03) to validate genuine LLM compaction behavior"
    notes: "Dry-run pipeline validated. MockLM ceiling of 1.0 confirmed for uncompacted data."
  - subject_id: claim-templates
    subject_kind: claim
    subject_role: decisive
    reference_id: ref-mock-experiment
    comparison_kind: existence
    metric: "provenance depth and content substantiality"
    threshold: "depth >= 5 after 10 iterations, prompts > 200 chars"
    verdict: pass
    recommended_action: "Use templates in Track A experiments (Plan 03)"
    notes: "All forbidden proxies rejected. Templates produce rich content suitable for genuine compaction experiments."

duration: 19min
completed: 2026-03-28
---

# Phase 6 Plan 02: Experiment Orchestration Infrastructure Summary

**Built experiment orchestration infrastructure: GenuineCompactionRunner (API + dry-run, 30 tests) and 3 Track A task templates with validated provenance chains (33 tests)**

## Performance

- **Duration:** 19 min
- **Started:** 2026-03-28T04:06:57Z
- **Completed:** 2026-03-28T04:26:16Z
- **Tasks:** 2/2
- **Files created:** 4
- **New tests:** 63

## Key Results

- **genuine_compaction_runner.py:** GenuineCompactionRunner class with run_trial(), capture_boundary(), log_results(). Supports both live API mode (compact_20260112 with pause_after_compaction) and dry-run mode. Retry logic with exponential backoff. JSONL logging with full schema. [CONFIDENCE: HIGH — 3 independent checks: dry-run E2E, JSONL schema validation, MockLM anchor comparison]
- **task_templates.py:** 3 Track A templates (CodingTaskTemplate, DebuggingTaskTemplate, SpecificationTaskTemplate). All produce 20 distinct iterations with deep provenance chains (depth >= 5), unique artifact IDs, and substantial content. [CONFIDENCE: HIGH — 3 independent checks: provenance depth validation, source ref integrity, forbidden proxy rejection]
- **Dry-run metrics validated:** structural_reachability=0.5, artifact_id_survival=0.5, compression_ratio=107.27, degraded_fraction=0.5, spf_scores present with all sub-metrics [CONFIDENCE: MEDIUM — validates pipeline logic only, not genuine LLM behavior]
- **Zero regressions:** Full test suite 699 passed, 4 skipped, 0 failures (plus 63 new tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build genuine compaction runner** - `f4a075c` (implement)
2. **Task 2: Build Track A task templates** - `fd0cc56` (implement)

## Files Created/Modified

- `tools/genuine_compaction_runner.py` — Experiment orchestration: API integration, dry-run, boundary capture, JSONL logging
- `tools/test_genuine_compaction_runner.py` — 30 tests covering dry-run E2E, JSONL, metrics, retry, integration
- `tools/task_templates.py` — 3 Track A templates with provenance chain building
- `tools/test_task_templates.py` — 33 tests covering all templates, depth, integrity, tokens, compatibility

## Next Phase Readiness

- Runner + templates ready for Track A pilot execution (Plan 03)
- Dry-run validates entire measurement pipeline without API costs
- Templates generate sufficient content to trigger 80K compaction threshold
- JSONL output parseable by standard json.loads() per line
- Integration chain verified: task_templates -> genuine_compaction_runner -> summary_parser -> embedding_similarity -> semantic_provenance_fidelity
- **Environment note:** ANTHROPIC_API_KEY required for live mode. Without it, runner falls back to dry-run automatically.

## Contract Coverage

- Claim IDs advanced: claim-runner -> passed, claim-templates -> passed
- Deliverable IDs produced: deliv-runner -> passed, deliv-templates -> passed, deliv-runner-tests -> passed, deliv-template-tests -> passed
- Acceptance test IDs run: test-dry-run-pipeline -> passed, test-template-depth -> passed
- Reference IDs surfaced: ref-mock-experiment -> compared, ref-compaction-api -> read
- Forbidden proxies: fp-short-tasks -> rejected (substantial content verified), fp-shallow-traces -> rejected (depth >= 5 verified)
- Decisive comparison verdicts: claim-runner -> pass (MockLM anchor), claim-templates -> pass (depth + content)

## Validations Completed

- Dry-run end-to-end: template -> runner -> boundary capture -> metrics -> JSONL -> parse -> verify schema
- All 63 new tests pass (30 runner + 33 templates)
- JSONL schema has all required fields: trial_id, track, task_category, model, mode, provenance_aware, threshold, compaction_events, aggregate_metrics, trace_stats, timestamp
- Aggregate metrics have all required sub-fields: structural_reachability, artifact_id_survival, compression_ratio, degraded_fraction, spf_scores
- All metric values in valid ranges: reachability in [0,1], survival in [0,1], compression > 0, degraded_fraction in [0,1]
- Provenance depth >= 5 after 10 iterations for all 3 templates
- 20 unique artifact IDs per template, no duplicates
- Source ref DAG: no dangling refs, no cycles
- All prompts > 200 chars (fp-short-tasks rejected)
- Import chain clean: no circular imports across 5-module dependency chain
- Full regression: 699 passed, 4 skipped, 0 failures (before adding new tests)

## Decisions & Deviations

### Decisions Made

1. **Dry-run midpoint simulation:** LLM compaction simulated at iteration num_iterations//2. First half of artifacts lost, second half survive (up to 5 IDs included in summary). Rationale: provides deterministic test data with 50% survival for pipeline validation.
2. **Skip-3 source refs:** Every 3rd iteration also references the artifact from 3 iterations back (in addition to the immediate predecessor). Rationale: ensures DAG depth grows faster than a simple chain, reaching depth >= 5 within 10 iterations.
3. **SpecificationTaskTemplate 20th prompt added:** The initial implementation had only 19 prompts. Added a compliance verification matrix prompt (REQ mapping) as the 20th. [Rule 4 — missing component]

### Deviations from Plan

**1. [Rule 1 - Code bug] Boundary capture test expected wrong surviving count**

- **Found during:** Task 1 (test_capture_produces_boundary)
- **Issue:** Test summary text contained both artifact IDs in a source_ref line, but test expected only 1 survivor
- **Fix:** Changed test summary to truly lose one ID (no mention in text)
- **Files modified:** tools/test_genuine_compaction_runner.py
- **Verification:** Test passes; boundary correctly identifies 1 surviving + 1 lost
- **Committed in:** f4a075c (Task 1 commit)

**2. [Rule 4 - Missing component] SpecificationTaskTemplate had only 19 prompts**

- **Found during:** Task 2 (test_20_distinct_prompts)
- **Issue:** The prompts list had 19 entries instead of the required 20
- **Fix:** Added 20th prompt (compliance verification matrix) covering requirement traceability
- **Files modified:** tools/task_templates.py
- **Verification:** All 33 tests pass; 20 distinct prompts confirmed
- **Committed in:** fd0cc56 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 code bug, 1 missing component)
**Impact on plan:** No impact. Both were caught by tests and fixed before commit.

## Open Questions

- Will live API mode produce different compaction behavior than expected? (Only live trials can answer — Plan 03)
- Are the task templates sufficiently diverse to trigger different compaction strategies? (Will be tested in Track C ablation — Plan 05)
- Is the token estimation accurate enough to reliably trigger compaction in 15-20 iterations? (Depends on model response length — monitor in Plan 03)

## Self-Check: PASSED

- [x] tools/genuine_compaction_runner.py exists
- [x] tools/test_genuine_compaction_runner.py exists
- [x] tools/task_templates.py exists
- [x] tools/test_task_templates.py exists
- [x] Commit f4a075c exists (Task 1)
- [x] Commit fd0cc56 exists (Task 2)
- [x] All 63 new tests pass
- [x] Full regression suite: 699 passed, 4 skipped
- [x] Convention consistency: artifact ID format matches CONVENTIONS.md #5
- [x] JSONL schema validates with json.loads()
- [x] End-to-end dry-run produces valid output
- [x] Import chain clean (no circular imports)
- [x] All contract IDs covered in contract_results
- [x] All forbidden proxies explicitly rejected with evidence
- [x] All must-surface references have completed actions

---

_Phase: 06-genuine-compaction, Plan: 02_
_Completed: 2026-03-28_
