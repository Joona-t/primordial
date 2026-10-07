# Requirements: Primordial v3.0 "Live Validation"

**Defined:** 2026-06-12
**Core Research Question:** Can typed absence, explicit provenance, and recoverable compaction prevent silent state loss in real long-running autonomous agents?

**Milestone goal:** Convert every v2.0 "pipeline-validated, pending live validation" verdict into a live result using real Claude Code sessions driven via local subprocess / Agent SDK on the user's subscription (hard rule: no paid API key anywhere). Claude Code's native auto-compaction is the genuine `llm_compaction` event RQ3b requires. The live track is **observational** (vs the dead API-track controlled design) — claim types are never pooled.

## Primary Requirements

### Live Harness (LIVE)

- [ ] **LIVE-01**: Build `tools/claude_code_transcript.py` — transcript JSONL extractor + tolerant schema-validating boundary parser; validated at 10/10 `compact_boundary` recall on the local calibration corpus (~/.claude/projects, CC 2.1.121–2.1.170); `refusal`-trigger events binned separately; raw transcripts archived verbatim before parsing.
- [ ] **LIVE-02**: Build the live session driver — Python `claude-agent-sdk` primary (subscription OAuth, in-process PreCompact/PostCompact hooks, `total_cost_usd`, `--session-id` pinning), raw `claude -p --output-format stream-json` subprocess as cross-check; forced `llm_compaction` via `CLAUDE_CODE_AUTO_COMPACT_WINDOW` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` set in the process environment; budget-guarded campaign loop; CLI version pinned (`DISABLE_AUTOUPDATER=1`); never `--bare`, never `--no-session-persistence`.
- [ ] **LIVE-03**: Contamination defenses operational **before** the pilot — hermetic temp-dir workspaces outside the repo tree (no CLAUDE.md leakage), canary nonces, automated post-run transcript audit; hash-domain partition assertion (no expected-hash over LLM content); `llm_`/`forge_` compaction-qualifier lint extended to all live-harness output paths.
- [ ] **LIVE-04**: Live pilot calibration (5–10 sessions): empirical tokens-to-trigger on the pinned CLI version, practical `AUTO_COMPACT_WINDOW` floor, env-var firing verification (GitHub #63186 caveat), hook stdin field dump, `/compact`-in-`-p` test, $/session from `total_cost_usd`, wall-clock σ_d estimate. **External prerequisite: Agent SDK monthly credit opt-in (user action; $200/mo on Max 20x, effective 2026-06-15).**

### Semantic Provenance Fidelity (SPF)

- [ ] **SPF-02**: Three-layer SPF stack operational locally — token overlap (existing), `all-MiniLM-L6-v2` cosine embedding backend, NEW MiniCheck-Flan-T5-Large NLI entailment layer (summary claim → original artifact); tier thresholds recalibrated on the local genuine-summary corpus (synthetic 0.9/0.7 values retired); MiniCheck validated ≥80% agreement against 30 hand-labeled claims; metrics venv resolved (torch wheel for Python 3.14 or 3.12 fallback). No single layer ever reported alone.

### Pre-Registration (PREG)

- [ ] **PREG-01**: Committed pre-registration protocol before any counted live run — task subset from the 20-task adversarial corpus, n=30 primary / n=59 escalation, CP sidedness decision (one-sided recommended) with mandatory dual-convention mapping table, exclusion rules, typed run-termination taxonomy (`completed`/`rate_limited`/`no_compaction_triggered`/…), claim table per n, simulated 0.93→0.25 curve labeled harness-anchor-only, observational-vs-controlled reframing entered in `GPD/CONVENTIONS.md`.

### Live Compaction Campaign (COMP)

- [ ] **COMP-05**: Live `llm_compaction` campaign — n=30 forced-compaction sessions (pre-registered escalation to 59) over marker-dense corpus tasks in hermetic workspaces; row-level `llm_compaction_occurred` gate (fp-short-tasks); three-layer SPF measured on real Claude Code compaction summaries; structural + semantic reachability on live chambers; recovery probes via `--resume`/`fork_session`; results compared against Zahn & Chana single-pass anchor (~60% fact loss) and the MockLM ceiling with gaps explained. Resolves COMP-01/COMP-04 partials at observational claim level. Exact `preTokens`/`postTokens` compression recorded per event.

### Live Violation Bound (VIOL)

- [ ] **VIOL-05**: Live natural-violation bound from the same campaign sessions — session-level binary outcome for the Clopper-Pearson bound, per-ref rates via cluster bootstrap (resampling sessions), Bayesian Beta posterior alongside; live claims phrased at live precision (never the mock 211-run precision); typed termination taxonomy with full denominator table; live violations separated from the Datadog-class explicit-error background.

### Overhead (OVER)

- [ ] **OVER-01**: RQ5 instrumentation overhead — token overhead as primary metric (all four usage buckets), 5-pair pilot to estimate σ_d, then 12–23 paired randomized interleaved A/B runs; decision rule: 95% CI upper bound of the overhead ratio < 1.20; direct forge-call timing secondary, wall-clock descriptive only; task success co-primary.

### Synthesis (XREF)

- [ ] **XREF-04**: Regenerate `data/synthesis/rq-verdicts.json` and the violation/compaction reports — mock-backend qualifiers removed exactly where live evidence lands, hierarchical claim phrasing (mock = tight bound under controlled conditions; live = coarser bound on the real substrate), full termination-state denominators; entire existing test suite (~537 tests) still green plus new harness tests.

## Follow-up Requirements

Deferred to future work. Tracked but not in the v3.0 roadmap.

### Paper

- **PAPER-01**: Workshop paper submission (AGENT 2026, MemAgents, or arXiv) — next milestone; SPF must be positioned against AAR provenance coverage/soundness (arXiv:2602.13855); must engage Khanal et al. "memory scaffold never helps" (instrumentation-vs-augmentation distinction) and Liu's inevitability thesis (CC-015 counter).

### Extensions

- **LIVE-05**: Organic-trigger stratum (sessions reaching the unmodified ~95% threshold) — only if budget allows after the forced-trigger campaign.
- **XARCH-02**: CrewAI adapter port (P2 from v2.0 analysis).
- **PROD-01**: `forge` package extraction + MCP provenance-memory server — separate engineering track outside this research repo (approved plan Phase 3).

## Out of Scope

| Topic | Reason |
| ----- | ------ |
| API-track controlled compaction experiments (`compact_20260112`, `pause_after_compaction`) | API-key-only (`--betas` verified API-key-only on CLI v2.1.170); dead under the no-paid-API rule. Live observational track replaces it as a different claim type. |
| Microcompaction (tool-output offloading) fidelity | Officially undocumented, no transcript marker; sidestepped by delivering token pressure via text — disclosed design limitation. |
| Matching mock-campaign precision (0/211 → 1.41%/1.73%) from the live subset | Requires 211 live runs; claiming it from n=30/59 is a registered small-n trap. |
| LLM-as-judge as a primary SPF metric | Claude judging Claude's compaction is circular; exploratory annex only. |
| Production deployment of forge | v3.0 measures deployability signals (RQ5); deployment itself is future work. |

## Accuracy and Validation Criteria

| Requirement | Accuracy Target | Validation Method |
| ----------- | --------------- | ----------------- |
| LIVE-01 | 10/10 boundary recall on calibration corpus | Parser run against all local compaction events; unknown-event counter = 0 |
| LIVE-04 | $/session and trigger threshold measured ±20% | `total_cost_usd` telemetry; bisection on `AUTO_COMPACT_WINDOW` |
| SPF-02 | ≥80% MiniCheck agreement vs 30 hand-labeled claims (pre-registered) | Hand-labeling protocol on local corpus before live runs |
| COMP-05 | SPF reported with all three layers + per-event compression | Cross-layer consistency check; zero-compaction control arm SPF ≈ 1 |
| VIOL-05 | Exact CP bound at the pre-registered sidedness | Closed-form recomputation; cluster bootstrap 10K resamples |
| OVER-01 | Token-ratio CI from ≥12 pairs; decision at CI UB < 1.20 | Bootstrap CI; dry-run recovers injected 20% synthetic overhead |
| XREF-04 | All ~537 existing tests pass; verdict JSON schema-valid | pytest full run; JSON schema check against synthesis.v1 |

## Contract Coverage

| Requirement | Decisive Output / Deliverable | Anchor / Benchmark / Reference | Prior Inputs / Baselines | False Progress To Reject |
| ----------- | ----------------------------- | ------------------------------ | ------------------------ | ------------------------ |
| LIVE-01/02/03 | Live harness + archived raw transcripts | Local calibration corpus (10 events) | tools/live_agent_experiment.py, genuine_compaction_runner.py | Parser validated only on synthetic summaries |
| LIVE-04 | Pilot calibration report | Official ~95% trigger prior (Contradiction 2) | COMPUTATIONAL.md budget model | Hard-coding community threshold figures |
| SPF-02 | Recalibrated three-layer SPF module | MiniCheck EMNLP 2024; Zahn & Chana anchor | tools/semantic_provenance_fidelity.py, embedding_similarity.py | Cosine-only fidelity claims |
| PREG-01 | Committed pre-registration doc | Hanley & Lippman-Hand; project CP history | v2.0 statistical conventions | Post-hoc claim sizing |
| COMP-05 | Live compaction report w/ SPF + reachability | MockLM ceiling (tools/experiment_results.json); Zahn & Chana 60% | data/baselines/baseline-report.json; simulated curve (anchor-only) | fp-short-tasks (runs without verified compact_boundary) |
| VIOL-05 | Live violation report w/ CP bound | Mock 0/211 bound (never pooled) | data/campaign/ runs | Per-ref Bernoulli counting (fabricated n); silent run discards |
| OVER-01 | Overhead report w/ CI decision | <20% target; Flowcept/OTel ecosystem claims (vendor) | Three-tier baseline design (v1.0) | Wall-clock-only differencing under LLM latency variance |
| XREF-04 | Regenerated rq-verdicts.json + reports | Pre-stated criteria matrix (v1.0 convention) | data/synthesis/rq-verdicts.json | Removing mock qualifiers where only mock evidence exists |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| LIVE-01 | Phase 9 — Free-Corpus Harness Construction | Pending |
| LIVE-02 | Phase 10 — Live Driver, Pilot, and Calibration | Pending |
| LIVE-03 | Phase 9 — Free-Corpus Harness Construction | Pending |
| LIVE-04 | Phase 10 — Live Driver, Pilot, and Calibration | Pending |
| SPF-02 | Phase 9 — Free-Corpus Harness Construction | Pending |
| PREG-01 | Phase 11 — Pre-Registration Gate | Pending |
| COMP-05 | Phase 12 — Live Compaction and Violation Campaign | Pending |
| VIOL-05 | Phase 12 — Live Compaction and Violation Campaign | Pending |
| OVER-01 | Phase 13 — Instrumentation Overhead Campaign | Pending |
| XREF-04 | Phase 14 — Synthesis and Verdict Regeneration | Pending |

**Coverage:**

- Primary requirements: 10 total
- Mapped to phases: 10/10 (each to exactly one primary phase; no orphans, no duplicates)
- Unmapped: 0

**Mapping notes:**

- LIVE-02 maps to Phase 10 (not 9) because the driver's acceptance behaviors (env-var firing, hook callbacks, session pinning) are only verifiable on live sessions — the pilot phase is where they are exercised.
- Phase 10 carries the external prerequisite: Agent SDK monthly credit opt-in (user action; $200/mo on Max 20x, effective 2026-06-15). Phase 9 is zero live spend.
- The open context gap (live task subset not yet locked) is resolved inside PREG-01 / Phase 11 via task-subset selection from the 20-task adversarial corpus.

---

_Requirements defined: 2026-06-12_
_Last updated: 2026-06-12 — traceability mapped at v3.0 roadmap creation (Phases 9-14)_
