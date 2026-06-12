---
phase: 07-adversarial-tasks
plan: 02
depth: full
one-liner: "Built 20 adversarial task templates across 9 categories with full D1-D9 coverage and a 7-channel instrumented campaign runner"
subsystem: validation
tags: [adversarial-testing, violation-detection, chaos-engineering, campaign-infrastructure]

requires:
  - phase: 07-adversarial-tasks
    provides: [07-RESEARCH.md task taxonomy, D-type mapping, statistical power analysis, instrumentation spec]
provides:
  - 20 adversarial task templates (TASK-A1a through TASK-C9c) with workspace generators
  - 17 control variants for Tier A/B tasks
  - ReliabilityBench epsilon/lambda stress calibration at 4 levels
  - Corpus manifest with 201 planned runs and D-type coverage matrix
  - Campaign runner with 7-channel instrumentation and dry-run/resume support
  - MockLM backend for end-to-end pipeline testing
affects: [07-03 campaign execution, 07-04 statistical analysis]

methods:
  added: [ReliabilityBench epsilon/lambda stress calibration, graduated task difficulty tiers]
  patterns: [adversarial task template pattern, 7-channel instrumentation schema, resume-capable campaign execution]

key-files:
  created:
    - tools/adversarial_corpus.py
    - tools/test_adversarial_corpus.py
    - tools/campaign_runner.py
    - tools/test_campaign_runner.py
    - data/campaign/corpus_manifest.json

key-decisions:
  - "Added D4 to TaskA4a (Deploy-Then-Rollback) to ensure D4 is targeted by >= 2 categories (A3 + A4)"
  - "Control variants implemented as separate classes (not parameterized) for clarity and independent workspace generation"
  - "MockLM backend generates structurally valid forge chambers with real artifact registration, not stub dicts"

patterns-established:
  - "AdversarialTask ABC: task_id, category, tier, target_dtypes, generate_workspace(), generate_prompt(level), get_stress_config(level), check_success(result)"
  - "7-channel run result schema: chamber, transcript, tool_call_log, compaction_events, token_count, wall_clock_seconds, framework_version"
  - "Resume pattern: persist each run to disk immediately, scan on restart, skip completed run_ids"

conventions:
  - "violation_classification = structural only (CONVENTIONS.md #8)"
  - "d_type_taxonomy = D1-D9 per CONVENTIONS.md"
  - "compaction_disambiguation = forge compaction (lossless) vs LLM compaction (lossy)"
  - "all_metrics_dimensionless = True"

plan_contract_ref: "GPD/phases/07-adversarial-tasks/07-02-PLAN.md#/contract"
contract_results:
  claims:
    claim-corpus-coverage:
      status: passed
      summary: "20 task templates across 9 categories collectively stress all 9 D-types, with each D-type targeted by >= 2 independent task categories. D4 required adding to TaskA4a (A3+A4 now cover it)."
      linked_ids: [deliv-corpus, deliv-manifest, test-dtype-coverage, test-corpus-executability, ref-research-taxonomy, ref-reliabilitybench]
    claim-runner-instrumentation:
      status: passed
      summary: "Campaign runner records all 7 required instrumentation channels for every run. Dry-run on 3 representative tasks (SHORT/MEDIUM/LONG) confirms all channels present with correct types."
      linked_ids: [deliv-runner, deliv-runner-tests, test-runner-dry-run, ref-research-instrumentation]
  deliverables:
    deliv-corpus:
      status: passed
      path: "tools/adversarial_corpus.py"
      summary: "20 task template classes with workspace generators, prompt generators, stress calibration, success checkers, and 17 control variants"
      linked_ids: [claim-corpus-coverage, test-dtype-coverage, test-corpus-executability]
    deliv-manifest:
      status: passed
      path: "data/campaign/corpus_manifest.json"
      summary: "Machine-readable manifest: 20 tasks, 201 planned runs, D-type coverage matrix, tier distribution, stress level configs"
      linked_ids: [claim-corpus-coverage, test-dtype-coverage]
    deliv-runner:
      status: passed
      path: "tools/campaign_runner.py"
      summary: "Campaign execution engine with MockLM backend, resume support, timeout handling, 7-channel output schema"
      linked_ids: [claim-runner-instrumentation, test-runner-dry-run]
    deliv-runner-tests:
      status: passed
      path: "tools/test_campaign_runner.py"
      summary: "59 tests covering dry-run, resume, timeout, schema consistency, campaign status, mock backend"
      linked_ids: [claim-runner-instrumentation, test-runner-dry-run]
  acceptance_tests:
    test-dtype-coverage:
      status: passed
      summary: "D-type coverage matrix verified: all 9 D-types covered by >= 2 categories. Total unique (task, D-type) pairs = 42 (>= 30 required)."
      linked_ids: [claim-corpus-coverage, deliv-manifest]
    test-corpus-executability:
      status: passed
      summary: "20/20 templates generate valid workspaces (files, tools, constraints). 80/80 stress configs valid (20 tasks x 4 levels)."
      linked_ids: [claim-corpus-coverage, deliv-corpus]
    test-runner-dry-run:
      status: passed
      summary: "3/3 dry runs complete (TASK-C9a SHORT, TASK-B5a MEDIUM, TASK-A1a LONG). Each output contains all 7 channels with correct types: chamber (non-empty dict with stages), transcript (list of role/content/tokens), tool_call_log (list with tool/call_id/input/output/duration_ms), compaction_events (list, non-empty for LONG), token_count (cumulative int > 0), wall_clock_seconds (float > 0), framework_version (string)."
      linked_ids: [claim-runner-instrumentation, deliv-runner, deliv-runner-tests]
  references:
    ref-research-taxonomy:
      status: completed
      completed_actions: [read, use]
      missing_actions: []
      summary: "07-RESEARCH.md Section 2 task-to-D-type mapping used to design all 20 templates and assign target D-types"
    ref-reliabilitybench:
      status: completed
      completed_actions: [cite, use]
      missing_actions: []
      summary: "ReliabilityBench epsilon/lambda stress calibration framework used for 4 graduated stress levels (control/mild/moderate/heavy)"
    ref-research-instrumentation:
      status: completed
      completed_actions: [read, use]
      missing_actions: []
      summary: "07-RESEARCH.md Section 5.4 instrumentation spec used to define all 7 required channels in run result schema"
  forbidden_proxies:
    fp-short-task-only:
      status: rejected
      notes: "Corpus includes MEDIUM (7), LONG (7), and EXTREME (1) tasks alongside SHORT (5). LONG/EXTREME tasks trigger LLM compaction events in MockLM."
    fp-single-category:
      status: rejected
      notes: "9 distinct categories implemented: A1-A4, B5-B8, C9. Categories include code review, deployment, data analysis, research synthesis, encoding, and codebase exploration."
    fp-no-controls:
      status: rejected
      notes: "17 control variants implemented for all 14 Tier A and B primary tasks, plus 3 C9 tasks that are themselves controls."
    fp-shallow-instrumentation:
      status: rejected
      notes: "All 7 channels recorded: chamber + transcript + tool_call_log + compaction_events + token_count + wall_clock + framework_version."
  uncertainty_markers:
    weakest_anchors: ["Task difficulty calibration is theoretical -- actual token counts and retry rates will differ from estimates when run with real LLMs"]
    unvalidated_assumptions: ["MockLM chambers are structurally valid but simpler than real agent sessions; instrumentation validation may be vacuous for rare edge cases"]
    competing_explanations: []
    disconfirming_observations: []

duration: 18min
completed: 2026-03-28
---

# Plan 02: Adversarial Task Corpus and Campaign Runner

**Built 20 adversarial task templates across 9 categories with full D1-D9 coverage and a 7-channel instrumented campaign runner**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-28T06:09:30Z
- **Completed:** 2026-03-28T06:27:00Z
- **Tasks:** 2
- **Files created:** 5
- **Tests added:** 489 (430 corpus + 59 runner)

## Key Results

- 20 task templates covering 9 categories (A1-A4, B5-B8, C9) with 42 unique (task, D-type) pairs
- D-type coverage matrix: every D-type D1-D9 targeted by >= 2 independent categories
- Corpus manifest documents 201 planned runs across 4 tiers (SHORT:5, MEDIUM:7, LONG:7, EXTREME:1)
- Campaign runner produces structurally valid 7-channel output in dry-run mode for all 3 representative tiers
- Resume support verified: completed runs skipped, no duplicates on restart

## Task Commits

Each task was committed atomically:

1. **Task 1: Build adversarial task corpus** - `481e68f` (implement)
2. **Task 2: Build campaign runner** - `49e70e8` (implement)

## Files Created/Modified

- `tools/adversarial_corpus.py` - 20 task templates (AdversarialTask ABC) + 17 control variants + AdversarialCorpus container
- `tools/test_adversarial_corpus.py` - 430 tests for corpus validation
- `tools/campaign_runner.py` - CampaignRunner + MockLMBackend + validate_run_result
- `tools/test_campaign_runner.py` - 59 tests for runner validation
- `data/campaign/corpus_manifest.json` - Machine-readable manifest (201 runs, D-type matrix)

## Validations Completed

- D-type coverage: all 9 types covered by >= 2 categories (verified by test_each_dtype_by_at_least_2_categories)
- Tier distribution: SHORT >= 3, MEDIUM >= 4, LONG >= 5, EXTREME >= 1 (verified)
- Category distribution: A1:3, A2:3, A3:2, A4:2, B5:2, B6:2, B7:2, B8:1, C9:3 (matches RESEARCH 5.1)
- Total planned runs: 201 (matches target)
- All 20 tasks instantiate and produce valid workspaces (430 tests)
- All 4 stress levels produce valid configs for each task (80/80)
- Control variants exist for all Tier A and B tasks (17 controls)
- Dry-run validates all 7 channels present with correct types (3 representative tasks)
- Resume skips completed runs correctly
- Timeout/crash handling produces partial results (not exceptions)

## Decisions Made

- **D4 coverage fix:** Added D4 to TaskA4a target_dtypes. The Deploy-Then-Rollback task can produce duplicate artifact IDs when re-registering in a sealed context, making D4 a natural target. This ensures D4 is covered by both A3 (parallel coordination) and A4 (error recovery).
- **Control variant design:** Implemented as separate classes (TaskA1aControl, etc.) rather than parameterized modes of the primary class. This allows controls to have independently generated workspaces and different tier classifications.
- **MockLM chamber generation:** Uses real forge_chamber.create_chamber/register_stage/seal_chamber instead of stub dicts, ensuring the mock output is structurally identical to real runs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - Missing Component] D4 had insufficient category coverage**

- **Found during:** Task 1 (test_each_dtype_by_at_least_2_categories)
- **Issue:** D4 (duplicate artifact ID) was only targeted by category A3 (parallel coordination). Required >= 2 categories.
- **Fix:** Added D4 to TaskA4a target_dtypes (A4 error recovery -- re-registration can produce duplicate IDs)
- **Files modified:** tools/adversarial_corpus.py
- **Verification:** Test passes after fix; D4 now targeted by A3 + A4
- **Committed in:** 481e68f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing component)
**Impact on plan:** Essential for claim-corpus-coverage. No scope creep.

## Issues Encountered

None.

## Contract Coverage

- Claim IDs advanced: claim-corpus-coverage -> passed, claim-runner-instrumentation -> passed
- Deliverable IDs produced: deliv-corpus -> tools/adversarial_corpus.py, deliv-manifest -> data/campaign/corpus_manifest.json, deliv-runner -> tools/campaign_runner.py, deliv-runner-tests -> tools/test_campaign_runner.py
- Acceptance test IDs run: test-dtype-coverage -> passed, test-corpus-executability -> passed, test-runner-dry-run -> passed
- Reference IDs surfaced: ref-research-taxonomy -> [read, use], ref-reliabilitybench -> [cite, use], ref-research-instrumentation -> [read, use]
- Forbidden proxies rejected: fp-short-task-only -> rejected, fp-single-category -> rejected, fp-no-controls -> rejected, fp-shallow-instrumentation -> rejected

## Next Phase Readiness

- Adversarial corpus ready for Plan 03 (campaign execution): 201 runs across 20 tasks at 4 stress levels
- Campaign runner ready: dry-run validated, resume-capable, timeout-safe
- Corpus manifest provides machine-readable task metadata for automated dispatch
- Real backend (openclaw/claude-code) integration is the remaining step before live campaign

## Open Questions

- What is the actual token count distribution when running with real LLMs? (MockLM estimates are theoretical)
- Will the resume mechanism handle partial JSON files from hard crashes gracefully? (Currently relies on valid JSON)

---

_Phase: 07-adversarial-tasks_
_Completed: 2026-03-28_
