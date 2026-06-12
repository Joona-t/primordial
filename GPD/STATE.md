# Research State

## Project Reference

See: GPD/PROJECT.md (updated 2026-03-28)

**Machine-readable scoping contract:** `GPD/state.json` field `project_contract`

**Core research question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?
**Current focus:** v3.0 Live Validation — Phase 9 (Free-Corpus Harness Construction) ready to plan

## Current Position

**Milestones completed:** v1.0 (2026-03-16), v2.0 (2026-03-28)
**Active Milestone:** v3.0 Live Validation (Phases 9-14)
**Current Phase:** 9 (Free-Corpus Harness Construction)
**Total Phases:** 14 (5 in v1.0, 3 in v2.0, 6 in v3.0)
**Total Plans:** 25 complete (12 in v1.0, 13 in v2.0); v3.0 plans TBD
**Status:** Ready to plan
**Last Activity:** 2026-06-12 — v3.0 roadmap created (Phases 9-14, 10/10 objectives mapped, contract coverage validated)

**Progress (v3.0):** [░░░░░░░░░░] 0% (v1.0 + v2.0 complete; v3.0 not started)

**Next:** `gpd:plan-phase 9` (zero live spend). Phase 10 additionally requires the Agent SDK monthly credit opt-in (user action, effective 2026-06-15).

## Intermediate Results

### v1.0 Results (archived)
See `GPD/milestones/v1.0/RESEARCH-DIGEST.md` for complete v1.0 results.
**Verdicts:** RQ1 PASS | RQ2 PARTIAL | RQ3 PARTIAL

### v2.0 Results (archived)
See `GPD/milestones/v2.0/RESEARCH-DIGEST.md` for complete v2.0 results.
**Verdicts:** RQ2b NEGATIVE-STRONG | RQ3b PARTIAL | RQ4 POSITIVE (all pipeline-validated, pending live validation)

### Cumulative Research Position
- 8-state absence ontology: formally sound, 300K adversarial transitions, 99% mutation score
- Detection: 9/9 D-types at 100% on injected faults; 0/321 natural violations (CP upper 1.14%)
- Compaction: simulated reachability 0.93→0.25; genuine pipeline built but untested
- Cross-architecture: 3 frameworks (OpenClaw, AG2, LangGraph), equivalent metrics
- CC-015 triggered: reframe detection → structural prevention
- All mock-backend results carry "pipeline-validated, pending live validation" qualifier

## Open Questions

- Is the Agent SDK monthly credit opted in on this account? (HIGH — external prerequisite gating Phase 10; user action, $200/mo on Max 20x, effective 2026-06-15)
- Empirical tokens-to-trigger and practical AUTO_COMPACT_WINDOW floor on the pinned CLI version? (HIGH — Phase 10 resolves; blocks Phase 12 sizing; Resolved Contradiction 2 residue)
- CP sidedness pre-registration choice — one-sided recommended; all published v1.0/v2.0 numbers are two-sided? (HIGH — Phase 11 decision; dual-convention mapping table mandatory)
- Does the 0/321 mock zero-violation finding transfer to live sessions? (HIGH — Phase 12 core question)
- Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured on live data? (HIGH — SPF-02/COMP-05, Phase 12)
- Can forge overhead stay below 20% of baseline task completion time? (MEDIUM — RQ5, Phase 13)
- Is wall-clock sigma_d small enough to resolve the 20% threshold, or does token-primary stand alone? (MEDIUM — Phase 13 pilot)
- `/compact [instructions]` inside `-p` mode? `refusal`-trigger semantics + calibration-corpus count reconciliation (10 auto/manual vs ~10 refusal records)? (MEDIUM — Phases 9-10)
- Does run_queue.py use session-layer LLM compaction during task execution? (carried from v1.0; LOW for v3.0 — live track targets Claude Code sessions directly)
- What is the queue file rotation/deletion policy in production? (carried from v1.0; LOW for v3.0)

## Accumulated Context

### Decisions

Full decision log: see `GPD/PROJECT.md` Key Decisions table (CC-001 through CC-021).
- [Phase 0]: Started milestone v3.0: Live Validation — New milestone cycle: convert v2.0 pipeline-validated verdicts to live results via Claude Code CLI subprocess (no paid API)
- [v3.0 roadmap]: 6 phases (9-14) derived from the 10 objectives + literature synthesis phase suggestions — Pre-registration kept as a standalone gate phase (11) because it gates both campaigns (12 and 13); CP sidedness decision deferred to Phase 11 per Resolved Contradiction 1; live track framed observational, never pooled with mock, per Resolved Contradiction 3; official ~95% trigger used as planning prior only per Resolved Contradiction 2 (empirical measurement in Phase 10); fp-short-tasks gate built in 9, calibrated in 10, committed in 11, enforced in 12

### Active Approximations

None (formal systems, no approximations needed).

### Convention Lock

All conventions from v1.0 carry forward unchanged. See `GPD/CONVENTIONS.md`.

### Blockers/Concerns

- External prerequisite (gates Phase 10, NOT Phase 9): Agent SDK monthly credit opt-in — one-time user action; $200/mo on Max 20x, effective 2026-06-15; hard stop when depleted. Phase 9 is zero live spend and can proceed immediately.
- Format drift concern (Phases 10-13): stream-json and transcript schemas are undocumented and the CLI auto-updates — mitigated by pinning the CLI (`DISABLE_AUTOUPDATER=1`) and archiving raw transcripts verbatim before parsing (parser bug costs a re-parse, not a re-run).

## Session Continuity

**Last session:** none
**Stopped at:** none
**Resume file:** none
**Last result ID:** none
**Hostname:** none
**Platform:** none
