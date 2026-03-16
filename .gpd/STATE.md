# Research State

## Project Reference

See: .gpd/PROJECT.md

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** Phase 3 complete. Ready for verification then Phase 4.

## Current Position

**Current Phase:** 3 (complete)
**Current Phase Name:** Violation Detection Campaign
**Total Phases:** 5
**Current Plan:** 2/2 (all complete)
**Total Plans in Phase:** 2
**Status:** Phase 3 complete
**Last Activity:** 2026-03-16 — Phase 3 execution complete (both plans passed, campaign results approved)

**Progress:** [██████░░░░] 60%

## Active Calculations

None (Phase 3 complete, Phase 4 not started).

## Intermediate Results

- **TRANSITION_TABLE:** 64 entries (45 legal, 19 illegal) — tools/forge_nulls.py
- **validate_transition():** function returning bool, ValueError for invalid states — tools/forge_nulls.py
- **Hypothesis verification:** 10K examples x 30 steps = 300K transitions, 0 invariant violations
- **Mutation score:** 99.0% adjusted (103/110 killed, 6 equivalent, 1 low-value)
- **Total test count:** 354 (103 existing + 198 ontology + 53 adapter)
- **Forge adapter:** tools/openclaw_adapter.py — 4 interception points, post-hoc JSONL primary
- **Baseline measurements (ledger sample):** uninstrumented reachability=0.0, forge reachability=1.0, forge depth=21, compression=1.18x, cursor resets=6
- **Measurement framework:** tools/baseline_measurement.py — 5 canonical metrics + bootstrap 95% CIs
- **Fault injector:** tools/fault_injector.py — 9 injection methods (D1-D9) + verify_injection()
- **Campaign orchestrator:** tools/detection_campaign.py — 90+ injections, three-tier comparison, CI framework
- **Post-hoc forge detection:** 4/9 types detected (D1, D2, D5, D9); 5 gaps (D3, D4, D6, D7, D8)
- **D1-D6 vs MockLM:** 3/6 = 50% post-hoc (gap: D3 hash, D4 ref correctness, D6 transition legality)
- **Clean FPR:** 0.0 (0/5 runs)
- **Total test count:** 404 (354 existing + 50 new fault injector/campaign tests)
- **Campaign detection:** 40/90 = 44.4% aggregate [CI: 0.344, 0.544]; D1/D2/D5/D9 at 100%, D3/D4/D6/D7/D8 at 0%
- **Natural violations:** 0 (0/30 clean runs, CP upper bound 11.6%) — negative finding, honestly reported
- **FPR:** 0.0% (0/30, CP upper bound 11.6%)
- **Differential:** forge - uninstrumented = +0.444, CI excludes zero
- **Three-tier ordering:** holds for all 9 fault types

## Open Questions

- Does run_queue.py use session-layer LLM compaction during task execution? (HIGH, affects Phase 3/4 adapter scope)
- What is the queue file rotation/deletion policy in production? (MEDIUM, affects long-term source_ref resolvability)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured? (HIGH, blocks Phase 4)

## Performance Metrics

| Label | Duration | Tasks | Files |
| ----- | -------- | ----- | ----- |
| Plan 01-01 | ~5 min | 3 | 4 |
| Plan 01-02 | ~20 min | 3 | 7 |

## Accumulated Context

### Decisions

- **CC-001:** resolved is a REF state, not an absence state; not_generated is the correct 8th absence state (Phase 1 Plan 01 Task 1)
- **CC-002:** timed_out/interrupted NOT added as distinct absence states — identical transition rules to existing states; metadata enrichment sufficient (Phase 1 Plan 01 Task 3)
- **CC-003:** Recoverability stays binary for Phase 1 — does not change transition rules; no empirical compaction data yet; YAGNI (Phase 1 Plan 01 Task 3)
- **CC-004:** Custom AST mutation testing over mutmut (Python 3.14 incompatibility) (Phase 1 Plan 02 Task 3)
- [Phase 2]: CC-005: Zarathustra IS OpenClaw on separate VM (user confirmed). Pure Python stdlib queue worker, directly importable. — Environmental investigation found no local OpenClaw installation. User confirmed OpenClaw runs on separate VM and pushed integration samples (commit 028d235).
- [Phase 2]: CC-006: Task corpus domain = coding/patching (real Zarathustra workflows) — Ledger data confirms OpenClaw does patch propose/validate/apply workflows. User directed: stay with what it actually does.
- [Phase 2]: CC-007: Task corpus scope = 3 short + 3 long, expandable — Option C scope with Option A domain. Budget is session time (subscription), not per-token.
- [Phase 2]: CC-008: Benchmark source = real Zarathustra tasks, NOT SWE-bench — User directed: test on this agent's actual failure modes, not external benchmarks.
- [Phase 3]: CC-009: Post-hoc injection approach reveals architectural gap vs MockLM registration-time detection (3/6 D1-D6 vs 6/6). Gap is real, not a bug.
- [Phase 3]: CC-010: D7/D8 gaps are findings about forge coverage limitations, not test failures. D7 may be fundamentally undetectable by structural validation.
- [Phase 3]: CC-011: Accepted negative finding on natural violations. Forge mechanism proven on injected faults; natural violations are zero on this sample (0/30 clean runs, CP upper bound 11.6%).

### Active Approximations

None (formal systems, no approximations needed).

**Convention Lock:**

- Metric signature: N/A
- Fourier convention: N/A
- Natural units: N/A
- Gauge choice: N/A
- Regularization scheme: N/A
- Renormalization scheme: N/A
- Coordinate system: N/A
- Spin basis: N/A
- State normalization: N/A
- Coupling convention: N/A
- Index positioning: N/A
- Time ordering: N/A
- Commutation convention: N/A
- Levi-Civita sign: N/A
- Generator normalization: N/A
- Covariant derivative sign: N/A
- Gamma matrix convention: N/A
- Creation/annihilation order: N/A

*Custom conventions:*
- Absence State Ontology: 8 states: not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable. Deprecated alias: pruned -> pruned_recoverable. FORMALIZED in Phase 1 FORM-01.
- Absence Object Form: Canonical v1: {value: null, state: <AbsenceState>}. Legacy ingress: {value: null, absence_state: <AbsenceState>} accepted and normalized. Sibling pattern: {field: null, field_state: <AbsenceState>}.
- State Transition Legality: 8x8 matrix (64 entries). 45 legal, 19 illegal. TRANSITION_TABLE in forge_nulls.py is source of truth. validate_transition() enforces. Initial states (not_invoked, not_generated) have no incoming. Terminal state (deleted) has no outgoing. Self-transitions always legal.
- Provenance Reference Format: Lightweight parent_id + source_refs list. Not full W3C PROV. Empty refs valid. Unresolvable ref = REF.REF_UNRESOLVED error.
- Artifact Id Format: Colon-separated hierarchical. Artifacts: artifact:<run>:stage:<seat>:<revision>. Chambers: chamber:<seg1>:<seg2>[:<segN>]. Regex validated.
- Compaction Disambiguation: TWO meanings, always qualified. Forge compaction = lossless hash-verified dedup. LLM compaction = lossy semantic summarization. Unqualified 'compaction' FORBIDDEN.
- Metrics Definitions: reachability_fraction=(reachable/total via BFS). compression_ratio=original/encoded. vs_vanilla_pct=(forge-vanilla)/vanilla*100. All dimensionless. MockLM anchors: reach=1.0, detect=6/6, compress=87%.
- Violation Classification: Structural only: illegal state transitions or missing metadata. NOT hallucination, NOT fault, NOT semantic error. Fault taxonomy D1-D9.
- Unit System Project: N/A -- formal systems research. All metrics dimensionless ratios or counts. No physical units.
- Hash Integrity: SHA-256 on canonical JSON: json.dumps(obj, sort_keys=True, ensure_ascii=True). Round-trip verification for forge trace compression.
- Protocol Versioning: schema_version=forge.internal.v1 (chambers/artifacts). encoding=forge.trace.v1 (trace codec). Legacy pre-v1 accepted at ingress, normalized.

### Propagated Uncertainties

None yet.

### Pending Todos

None yet.

### Blockers/Concerns

None

## Session Continuity

**Last session:** 2026-03-16
**Stopped at:** Phase 3 complete. Ready for Phase 4.
**Resume file:** —
