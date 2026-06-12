# Bugs & Iterations

## : |2026-03-16|||compute(03-02): execute D1-D9 injection campaign and clean campaign on real data

**Problem:** |2026-03-16|||compute(03-02): execute D1-D9 injection campaign and clean campaign on real data
**Details:** - 90 injections (9 types x 10 each) with three-tier comparison
- Forge detects 4/9 types: D1 (null collapse), D2 (broken provenance),
  D5 (missing state label), D9 (post-seal registration)
- 5 gaps: D3 (hash), D4 (ref correctness), D6 (transition), D7 (trace
  compression data loss), D8 (context pressure truncation)
**Files:** data/campaign/campaign-report.json,data/campaign/clean-results.json,data/campaign/injection-results.json,tools/run_campaign.py
**Commit:** 0c07e35

## : |2026-03-15|||setup(01-02): install hypothesis/mutmut and create test skeleton

**Problem:** |2026-03-15|||setup(01-02): install hypothesis/mutmut and create test skeleton
**Details:** - hypothesis 6.151.9 and mutmut 3.5.0 installed for Python 3.14
- test_forge_ontology.py skeleton with correct imports verified
- All 103 existing tests still pass (verified before changes)
**Files:** tools/test_forge_ontology.py
**Commit:** 1e320be

## : |2026-03-15|||docs(01-01): complete ontology formalization plan summary

**Problem:** |2026-03-15|||docs(01-01): complete ontology formalization plan summary
**Details:** - 64-entry transition table with 45 legal, 19 illegal transitions
- validate_transition() function with ValueError for invalid states
- Documentation discrepancy resolved (CC-001)
- FORM-03 decisions documented (CC-002, CC-003)
- All 103 tests pass, all contract claims satisfied
**Files:** GPD/phases/01-ontology-formalization-and-verification/01-01-SUMMARY.md
**Commit:** 336312c

## : |2026-03-16|||validate(05-01): add synthesis test suite with 39 tests, all passing

**Problem:** |2026-03-16|||validate(05-01): add synthesis test suite with 39 tests, all passing
**Details:** - tools/test_synthesis.py: 6 test classes covering data loading,
  table completeness, consistency, anchors, gap arithmetic, integration
- Data loading: structure validation for all 3 JSON sources,
  error handling for missing/corrupt files (5 + 3 + 3 + 2 = 13 tests)
- Table completeness: 12 rows, no None values, all 9 columns present,
**Files:** tools/test_synthesis.py
**Commit:** 3dfff7f

## : |2026-03-16|||validate(04-01): add 49 unit tests for compaction measurement harness

**Problem:** |2026-03-16|||validate(04-01): add 49 unit tests for compaction measurement harness
**Details:** Test coverage across 9 categories (7 required + 2 bonus):
1. Snapshot construction (6): empty, Phase 2, hash determinism, refs, IDs
2. BFS reachability (8): pre-compaction=1.0 (Phase 2 anchor confirmed),
   single root, linear chain, diamond DAG, empty chamber, depth, bounds
3. Three-tier ref classification (6): all-resolved, degraded, broken,
**Files:** tools/test_compaction_harness.py
**Commit:** 60bdbc9

## : |2026-03-16|||document(02-01): resolve Zarathustra identity as OpenClaw on separate VM

**Problem:** |2026-03-16|||document(02-01): resolve Zarathustra identity as OpenClaw on separate VM
**Details:** - Decision CC-005: Zarathustra IS OpenClaw, confirmed by user
- Runtime is queue-based task processor (not conversational LLM session)
- Pure Python stdlib, directly importable for adapter wrapping
- Integration samples from commit 028d235 provide ground truth
**Files:** docs/zarathustra-identity.md
**Commit:** 71f12be

## : |2026-03-15|||docs(01-01): resolve FORM-03 open questions with documented rationale

**Problem:** |2026-03-15|||docs(01-01): resolve FORM-03 open questions with documented rationale
**Details:** - Mark FORM-03 Q1 as RESOLVED: timed_out/interrupted NOT added as
  distinct states; use metadata enrichment instead (CC-002)
- Mark FORM-03 Q2 as RESOLVED: recoverability stays binary for
  Phase 1; graded deferred to Phase 4 as metadata (CC-003)
- Update convention #3 from skeleton to complete (delivered)
**Files:** GPD/CONVENTIONS.md
**Commit:** 8975287

## : |2026-03-16|||docs(05-02): complete cross-reference synthesis plan with SUMMARY

**Problem:** |2026-03-16|||docs(05-02): complete cross-reference synthesis plan with SUMMARY
**Details:** - RQ verdicts rendered: RQ1=PASS, RQ2=PARTIAL, RQ3=PARTIAL
- All gaps explained, forbidden proxy audit honest (fp-short-tasks=unresolved)
- Stop/rethink evaluated: none triggered, compaction inconclusive
- Researcher approved at checkpoint gate
**Files:** GPD/phases/05-cross-reference-and-synthesis/05-02-SUMMARY.md
**Commit:** 8c9d724

## : |2026-03-15|||docs(01-01): reconcile resolved/not_generated discrepancy

**Problem:** |2026-03-15|||docs(01-01): reconcile resolved/not_generated discrepancy
**Details:** - Update PROJECT.md absence state list: replace 'resolved' with
  'not_generated' to match forge_nulls.py V1_ABSENCE_STATES
- Document semantic distinction: absence states (value absence
  reasons) vs ref states (source_ref link status) are orthogonal
- Mark CONVENTIONS.md known discrepancy as RESOLVED (CC-001)
**Files:** GPD/CONVENTIONS.md,GPD/PROJECT.md
**Commit:** 904d65b

## : |2026-03-16|||docs(05-02): write cross-reference report with RQ verdicts, gap analysis, proxy audit, stop/rethink evaluation

**Problem:** |2026-03-16|||docs(05-02): write cross-reference report with RQ verdicts, gap analysis, proxy audit, stop/rethink evaluation
**Details:** - RQ1 Ontology Formalization: PASS (8 states, 10K+ Hypothesis, 99% mutation score)
- RQ2 Violation Detection: PARTIAL (44.4% on injected, 0 natural violations)
- RQ3 Compaction Survival: PARTIAL (simulated LLM compaction only, genuine pending)
- Gap analysis: D1-D6 gap architectural (3 types, post-hoc vs registration-time)
- Forbidden proxy audit: fp-synthetic-only avoided, fp-short-tasks UNRESOLVED, fp-shallow-traces avoided
**Files:** docs/cross-reference-report.md
**Commit:** 9d92d5d

## : |2026-03-15|||validate(01-02): Hypothesis RuleBasedStateMachine + negative transition tests

**Problem:** |2026-03-15|||validate(01-02): Hypothesis RuleBasedStateMachine + negative transition tests
**Details:** - AbsenceStateMachine: 10K examples x 30 steps = 300K+ transition attempts
  - 5 invariants: state validity, no illegal accepted, terminal respected,
    initial unreachable, transition log consistency
- LegalTransitionExplorer: 5K examples x 50 steps for reachability
- 19 parametrized illegal transition tests (all correctly rejected)
**Files:** tools/test_forge_ontology.py
**Commit:** abb3b12

## : |2026-03-16|||compute(05-02): produce machine-readable RQ verdict JSON

**Problem:** |2026-03-16|||compute(05-02): produce machine-readable RQ verdict JSON
**Details:** - rq1: PASS (HIGH confidence) - ontology formalization complete
- rq2: PARTIAL (HIGH confidence) - mechanism validated, 0 natural violations
- rq3: PARTIAL (MEDIUM confidence) - simulated LLM compaction only
- Forbidden proxy audit: fp-short-tasks = unresolved (honest)
- Stop/rethink: NOT_TRIGGERED, NOT_TRIGGERED, INCONCLUSIVE
**Files:** data/synthesis/rq-verdicts.json
**Commit:** f145c1c

## : |2026-03-16|||implement(04-01): build compaction measurement harness

**Problem:** |2026-03-16|||implement(04-01): build compaction measurement harness
**Details:** - CompactionSnapshot dataclass: from_chamber() captures artifact IDs,
  SHA-256 content hashes, and ref_graph from forge chambers
- Three-tier ref classification: resolved/degraded/broken based on
  content hash comparison pre/post LLM compaction
- BFS reachability: stdlib collections.deque, no networkx dependency.
**Files:** tools/compaction_harness.py
**Commit:** f9d902a

## 2026-06-12: ITER — Migrate legacy .gpd/ layout to GPD/ and repair project contract for GPD v1.2.2

**Problem:** GPD tooling (now v1.2.2) no longer recognized the project: `init new-milestone` reported `project_exists: false`, blocking the v3.0 milestone kickoff.
**Root cause:** The project was scaffolded under the legacy `.gpd/` planning directory; GPD v1.2.2 canonicalized `PLANNING_DIR_NAME = "GPD"` with no auto-migration from `.gpd/`. Additionally the stored project contract failed new semantic integrity gates: (a) the anchor string "6/6 violations" matched the path-like heuristic (slash regex) and failed file resolution; (b) `ref-mock-experiment` had a prose locator instead of a concrete artifact path.
**Fix:** `git mv .gpd GPD` (history-preserving); swept `.gpd/` → `GPD/` references in planning docs, `docs/research-v2.md`, `BUGS_AND_ITERATIONS.md`, `tools/seed_ledger.py` (left `data/` untouched — historical refs inside hash-relevant records); repaired `GPD/state.json` contract: slash-free anchor prose with corrected Convention-7 metrics (compression_ratio ~1.096x, ~87% smaller vs vanilla — not "87% compression ratio"), `ref-mock-experiment.locator` → `tools/experiment_results.json`, `must_include_prior_outputs` → `tools/`-prefixed resolvable paths, added `data/baselines/baseline-report.json` to known-good baselines. Contract gate now `authoritative: true`, validation `valid: true`.

<!-- Format:
## YYYY-MM-DD: Short Title

**Problem:** What went wrong or needed changing
**Root cause:** Why it happened
**Fix:** What was done to resolve it
-->
