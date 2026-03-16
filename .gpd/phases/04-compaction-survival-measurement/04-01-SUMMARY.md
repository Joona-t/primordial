---
phase: 04-compaction-survival-measurement
plan: 01
depth: full
one-liner: "Built compaction measurement harness with three-tier ref classification, BFS reachability, simulated LLM compaction, and violation regression; 49/49 tests pass"
subsystem: [numerics, validation]
tags: [compaction, reachability, BFS, provenance, measurement-harness, fault-injection]

requires:
  - phase: 02-integration-and-baseline-establishment
    provides: Forge adapter, sealed chambers, baseline reachability=1.0, depth=21, compression=1.18x
  - phase: 03-violation-detection-campaign
    provides: Fault injector D1-D9, detection campaign results (D1/D2/D5/D9 at 100%)

provides:
  - CompactionSnapshot dataclass for pre/post LLM compaction comparison
  - Three-tier ref classification (resolved/degraded/broken) with structural_reachability and semantic_fidelity metrics
  - BFS reachability measurement (stdlib-only, no networkx)
  - Simulated LLM compaction via programmatic oldest-first stage deletion
  - Violation regression harness for D1/D2/D5/D9 detection confirmation
  - Anchor comparison against MockLM ceiling, Phase 2 baseline, and backtracking threshold
  - Full measurement pipeline orchestrating all components
  - Bootstrap CI integration (reuses existing baseline_measurement.py and fault_injector.py functions)

affects: [04-compaction-survival-measurement/plan-02, 05-synthesis]

methods:
  added: [BFS reachability on provenance DAG, three-tier ref classification, simulated LLM compaction via oldest-first deletion]
  patterns: [CompactionSnapshot.from_chamber() for pre/post comparison, classify_refs() for three-tier analysis, run_compaction_measurement() as pipeline orchestrator]

key-files:
  created:
    - tools/compaction_harness.py
    - tools/test_compaction_harness.py

key-decisions:
  - "BFS reachability measures internal connectivity of remaining artifacts, not completeness of original provenance chain. For linear chains, deletion of oldest stages creates a new root (first remaining stage), so BFS reachability stays 1.0. The three-tier ref classification (structural_reachability) captures provenance breakage instead."
  - "Simulated LLM compaction uses oldest-first deletion (not random) because stages are chronologically ordered and LLM compaction typically drops oldest context. This provides a LOWER BOUND on reachability."
  - "Violation regression tests only D1/D2/D5/D9 (Phase 3 detected at 100%) by default. D3/D4/D6/D7/D8 gaps are known findings, not regressions to test."

patterns-established:
  - "CompactionSnapshot.from_chamber() for capturing artifact state at a point in time"
  - "classify_refs(pre, post) for measuring provenance degradation"
  - "simulate_compaction(chamber, fraction) as lower-bound proxy for LLM context-window compaction"

conventions:
  - "All 'compaction' uses qualified: LLM compaction (lossy semantic) vs forge trace compression (lossless structural)"
  - "Hash: SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True)"
  - "CI: Bootstrap 95% (B=10000, seed=42) for interior; Clopper-Pearson for boundary (0/n, n/n)"
  - "BFS: stdlib collections.deque only (no networkx)"

plan_contract_ref: ".gpd/phases/04-compaction-survival-measurement/04-01-PLAN.md#/contract"
contract_results:
  claims:
    claim-compaction-survival:
      status: partial
      summary: "Harness built and validated. Measurement infrastructure ready for Plan 02 (actual LLM compaction data). Pre-compaction reachability=1.0 confirmed. Simulated deletion produces measurable degradation."
      linked_ids: [deliv-compaction-harness, deliv-harness-tests, test-harness-validated, ref-mock-experiment]
      evidence:
        - verifier: pytest
          method: unit-test-suite
          confidence: high
          claim_id: claim-compaction-survival
          deliverable_id: deliv-compaction-harness
          acceptance_test_id: test-harness-validated
          reference_id: ref-mock-experiment
          evidence_path: "tools/test_compaction_harness.py (49/49 pass)"
  deliverables:
    deliv-compaction-harness:
      status: passed
      path: "tools/compaction_harness.py"
      summary: "Complete measurement harness with CompactionSnapshot, classify_refs, measure_reachability, simulate_compaction, violation_regression, compare_against_anchors, run_compaction_measurement"
      linked_ids: [claim-compaction-survival, test-harness-validated]
    deliv-harness-tests:
      status: passed
      path: "tools/test_compaction_harness.py"
      summary: "49 unit tests across 9 categories, all passing"
      linked_ids: [claim-compaction-survival, test-harness-validated]
  acceptance_tests:
    test-harness-validated:
      status: passed
      summary: "All 49 tests pass. Pre-compaction reachability=1.0 matches Phase 2 baseline. Simulated deletion reduces structural_reachability monotonically. D1/D2/D5/D9 regression passed."
      linked_ids: [claim-compaction-survival, deliv-compaction-harness, deliv-harness-tests, ref-mock-experiment]
  references:
    ref-mock-experiment:
      status: completed
      completed_actions: [read, compare]
      missing_actions: []
      summary: "MockLM ceiling (reachability=1.0, compression=87%) used as anchor in compare_against_anchors(). Pre-compaction reachability matches ceiling."
  forbidden_proxies:
    fp-short-tasks:
      status: rejected
      notes: "Harness built for deep traces (depth=21 from Phase 2). Simulated deletion operates on full trace depth. Full rejection requires Plan 02 execution with actual long tasks."
    fp-shallow-traces:
      status: rejected
      notes: "Test chambers match Phase 2 structure (21 stages, 40+ stages in real traces). Harness validated on deep linear chains and diamond DAGs."
  uncertainty_markers:
    weakest_anchors:
      - "Simulated deletion is a LOWER BOUND on real LLM compaction -- actual reachability may be higher (intelligent summarization preserves more than random deletion)"
      - "BFS reachability on linear chains stays 1.0 after deletion (sub-chain is self-contained); structural_reachability from classify_refs is the sensitive metric"
    unvalidated_assumptions:
      - "Real LLM context-window compaction events will be capturable by the harness snapshot mechanism"
    competing_explanations: []
    disconfirming_observations:
      - "Linear chain BFS reachability=1.0 even after 50% deletion -- DAG structure is inherently resilient for linear chains. This matches uncertainty_markers.disconfirming_observations in the PLAN."

duration: 7min
completed: 2026-03-16
---

# Phase 4 Plan 01: Compaction Measurement Harness Summary

**Built compaction measurement harness with three-tier ref classification, BFS reachability, simulated LLM compaction, and violation regression; 49/49 tests pass**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-16T02:53:11Z
- **Completed:** 2026-03-16T02:59:44Z
- **Tasks:** 2
- **Files modified:** 2

## Key Results

- Pre-compaction reachability = 1.0 confirmed on Phase 2-like chambers (matches Phase 2 baseline and MockLM ceiling) [CONFIDENCE: HIGH]
- Three-tier ref classification correctly separates structural from semantic fidelity: structural_reachability >= semantic_fidelity verified across all test scenarios [CONFIDENCE: HIGH]
- Simulated LLM compaction produces monotonically decreasing structural_reachability as deletion fraction increases (verified at 0.0, 0.1, 0.3, 0.5, 0.7, 0.9) [CONFIDENCE: HIGH]
- Violation regression D1/D2/D5/D9: all 4 fault types still detected (100% regression pass) [CONFIDENCE: HIGH]
- BFS reachability on linear chains remains 1.0 even after deletion -- this is correct behavior (sub-chain is self-contained), not a bug. The ref classification metric captures provenance breakage instead. [CONFIDENCE: HIGH]

## Task Commits

Each task was committed atomically:

1. **Task 1: Build compaction measurement harness** - `f9d902a` (implement)
2. **Task 2: Unit tests for compaction harness** - `60bdbc9` (validate)

## Files Created/Modified

- `tools/compaction_harness.py` - Complete measurement harness (734 lines): CompactionSnapshot, classify_refs, measure_reachability, simulate_compaction, violation_regression, compare_against_anchors, run_compaction_measurement, compute_reachability_ci
- `tools/test_compaction_harness.py` - 49 unit tests across 9 categories (785 lines)

## Next Phase Readiness

- Measurement harness ready for Plan 02: actual LLM compaction measurement campaign
- Key functions available for Plan 02: `run_compaction_measurement()` orchestrates the full pipeline, `CompactionSnapshot.from_chamber()` for pre/post comparison, `classify_refs()` for three-tier analysis
- Anchor comparison built in: MockLM ceiling, Phase 2 baseline, backtracking threshold all included in pipeline output

## Contract Coverage

- Claim IDs advanced: claim-compaction-survival -> partial (harness built, awaiting Plan 02 for real data)
- Deliverable IDs produced: deliv-compaction-harness -> passed, deliv-harness-tests -> passed
- Acceptance test IDs run: test-harness-validated -> passed
- Reference IDs surfaced: ref-mock-experiment -> completed (read, compare)
- Forbidden proxies rejected: fp-short-tasks -> rejected (deep traces used), fp-shallow-traces -> rejected (21-stage chambers used)
- Decisive comparison verdicts: N/A (no decisive comparison required at this plan level; Plan 02 provides the decisive data)

## Validations Completed

- Pre-compaction reachability = 1.0 on 21-stage chamber (Phase 2 anchor)
- Full deletion = 0 artifacts remaining (empty chamber limit)
- Zero deletion = reachability unchanged (identity operation)
- structural_reachability >= semantic_fidelity across all test scenarios
- resolved + degraded + broken == total (exhaustiveness) for all deletion fractions
- Deletion monotonicity: higher fraction -> lower structural_reachability
- Hash determinism: same content -> same SHA-256 hash
- Violation regression: D1/D2/D5/D9 all detected after harness changes
- No _fake_count_tokens usage (forbidden by research)
- No networkx dependency (BFS uses stdlib collections.deque)

## Decisions Made

- **BFS vs ref classification:** BFS reachability measures internal connectivity of remaining artifacts. For linear chains, this stays 1.0 after deletion because the sub-chain is self-contained. The three-tier ref classification (structural_reachability) is the metric that captures provenance breakage. Both metrics are reported; downstream analysis should use structural_reachability for measuring LLM compaction damage.
- **Oldest-first deletion:** Simulated deletion removes oldest stages first (not random) because stages are chronologically ordered and LLM compaction typically drops oldest context. This is a conservative lower bound.
- **D1/D2/D5/D9 regression scope:** Only the 4 fault types Phase 3 detected at 100% are included in default regression. The 5 gap types (D3/D4/D6/D7/D8) are known architectural gaps, not regressions to test.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Open Questions

- Will real LLM context-window compaction events be capturable by the snapshot mechanism? (Depends on Plan 02 execution)
- For non-linear DAGs (diamond, tree), does BFS reachability show deletion-induced degradation? (Partially explored: diamond DAG with 50% deletion still shows 1.0 BFS reachability because remaining nodes form a connected sub-graph)

## Self-Check: PASSED

- [x] tools/compaction_harness.py exists
- [x] tools/test_compaction_harness.py exists
- [x] Commit f9d902a exists (Task 1)
- [x] Commit 60bdbc9 exists (Task 2)
- [x] 49/49 tests pass
- [x] Pre-compaction reachability=1.0 confirmed
- [x] No _fake_count_tokens usage
- [x] No networkx dependency
- [x] All 'compaction' uses qualified

---

_Phase: 04-compaction-survival-measurement_
_Plan: 01_
_Completed: 2026-03-16_
