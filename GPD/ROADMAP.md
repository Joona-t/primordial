# Roadmap: Primordial Computing -- Typed Absence and Provenance in Agentic Systems

## Milestones

- **v1.0 Typed Absence and Provenance Validation** -- Phases 1-5 (completed 2026-03-16)
- **v2.0 The Forgetting Agent** -- Phases 6-8 (completed 2026-03-28)
- **v3.0 Live Validation** -- Phases 9-14 (active, started 2026-06-12)

## Phases

<details>
<summary>v1.0 Typed Absence and Provenance Validation (Phases 1-5) -- COMPLETED 2026-03-16</summary>

- [x] Phase 1: Ontology Formalization and Verification (2/2 plans) -- completed 2026-03-16
- [x] Phase 2: Integration and Baseline Establishment (4/4 plans) -- completed 2026-03-16
- [x] Phase 3: Violation Detection Campaign (2/2 plans) -- completed 2026-03-16
- [x] Phase 4: Compaction Survival Measurement (2/2 plans) -- completed 2026-03-16
- [x] Phase 5: Cross-Reference and Synthesis (2/2 plans) -- completed 2026-03-16

**Results:** RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL

See `GPD/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>v2.0 The Forgetting Agent (Phases 6-8) -- COMPLETED 2026-03-28</summary>

- [x] Phase 6: Genuine Compaction Experiments (5/5 plans) -- completed 2026-03-28
- [x] Phase 7: Adversarial Task Design and Natural Violation Campaign (4/4 plans) -- completed 2026-03-28
- [x] Phase 8: Cross-Architecture Generalization (4/4 plans) -- completed 2026-03-28

**Results:** RQ2b NEGATIVE-STRONG (0/211, CP upper 1.73%) | RQ3b PARTIAL (pipeline-validated, live untested) | RQ4 POSITIVE (0/110 cross-arch, 3 frameworks)

See `GPD/milestones/v2.0-ROADMAP.md` for full phase details.

</details>

### Active: v3.0 Live Validation (Phases 9-14)

**Milestone Goal:** Convert every v2.0 "pipeline-validated, pending live validation" verdict into a live result by driving real Claude Code sessions via local subprocess / Agent SDK on the user's Max subscription (hard rule: no paid LLM API anywhere). Claude Code's native auto-compaction is the genuine `llm_compaction` event RQ3b requires. The live track is **observational** validation -- a different claim type from the dead API-track controlled design -- and live results are never pooled with mock-campaign results (Resolved Contradictions 1-3, literature SUMMARY 2026-06-12).

**Objectives (10/10 mapped):** LIVE-01, LIVE-02, LIVE-03, LIVE-04, SPF-02, PREG-01, COMP-05, VIOL-05, OVER-01, XREF-04

- [ ] **Phase 9: Free-Corpus Harness Construction** - Transcript parser, three-layer SPF stack, and contamination defenses validated on genuine local compaction events at zero live spend
- [ ] **Phase 10: Live Driver, Pilot, and Calibration** - Live session driver operational; every campaign-sizing number measured empirically on the pinned CLI (5-10 sessions). EXTERNAL PREREQUISITE: Agent SDK credit opt-in
- [ ] **Phase 11: Pre-Registration Gate** - Hard, committed protocol artifact fixing task subset, n, CP sidedness, exclusions, and the claim table before any counted run
- [ ] **Phase 12: Live Compaction and Violation Campaign** - SPF + reachability through genuine llm_compaction and the live natural-violation CP bound (n=30, pre-registered escalation 59)
- [ ] **Phase 13: Instrumentation Overhead Campaign** - RQ5 token-primary overhead with 95% CI decision rule against the <20% target
- [ ] **Phase 14: Synthesis and Verdict Regeneration** - rq-verdicts.json and contract reports regenerated; mock qualifiers removed exactly where live evidence lands

#### Contract Overview (v3.0)

| Contract Item | Advanced By Phase(s) | Status |
| ------------- | -------------------- | ------ |
| claim-compaction-survival (test-compaction-provenance) | 9, 10, 11, 12 (decisive), 14 | Planned |
| claim-violation-detection (test-real-violation; under CC-015 structural-prevention framing if zero live events) | 11, 12 (decisive), 14 | Planned |
| deliv-compaction-report (live edition; MockLM cross-reference required) | 12, 14 | Planned |
| deliv-violation-report (live edition; baseline comparison required) | 12, 14 | Planned |
| deliv-formal-ontology | Completed v1.0 (Phase 1) | Complete |
| deliv-baseline (`data/baselines/baseline-report.json`) | Completed v1.0 (Phase 2); reused as comparison input in 12, 13 | Complete (reused) |
| ref-mock-experiment (MockLM anchor, `tools/experiment_results.json`; required action: compare; carry to planning/execution/verification) | 11 (planning), 12 (execution), 14 (verification) | Planned |
| Prior outputs: `tools/forge_nulls.py`, `tools/forge_chamber.py`, `tools/forge_trace_codec.py`, `tools/forge_reversible_summary.py` | 9 (harness integration), 12-13 (instrumented arms) | Planned |
| Crucial input: violation detection is the primary success signal | 12 (VIOL-05) | Planned |
| Crucial input: must survive REAL context-window compaction, not just mock scenarios | 12 (COMP-05 with fp-short-tasks gate) | Planned |
| Context gap: specific real-task corpus for live stress testing not yet locked | Resolved by Phase 11 (PREG-01 task-subset selection from the 20-task adversarial corpus) | Planned |
| fp-short-tasks (forbidden proxy; load-bearing gate) | Gate built 9 (`llm_compaction_occurred` + qualifier lint), calibrated 10, committed 11, enforced row-level 12, denominators reported 14 | Planned |
| fp-shallow-traces (forbidden proxy) | 11 (marker-dense subset selection), 12 (zero-compaction control arm, SPF ~ 1 expected) | Planned |
| fp-synthetic-only (forbidden proxy) | 9 (parser/SPF validated on genuine local events, never synthetic-only), 12 (live natural-violation bound) | Planned |
| External prerequisite: Agent SDK monthly credit opt-in ($200/mo on Max 20x, effective 2026-06-15; one-time user action; hard stop when depleted) | Gates Phase 10 entry (first live-spend phase); Phase 9 is zero-spend | Pending user action |

#### Phase Dependencies (v3.0)

| Phase | Depends On | Enables | Critical Path? |
|-------|-----------|---------|:-:|
| 9 - Free-Corpus Harness Construction | -- | 10 | Yes |
| 10 - Live Driver, Pilot, and Calibration | 9 | 11 | Yes |
| 11 - Pre-Registration Gate | 10 | 12, 13 | Yes |
| 12 - Live Compaction and Violation Campaign | 11 | 14 | Yes |
| 13 - Instrumentation Overhead Campaign | 11 | 14 | No (parallel with 12) |
| 14 - Synthesis and Verdict Regeneration | 12, 13 | -- | Yes |

**Critical path:** 9 -> 10 -> 11 -> 12 -> 14
**Parallelizable:** Phase 13 runs concurrently with Phase 12; the coupling is the shared $200/mo credit and 5-hour rate-limit windows (interleave scheduling, budget-gate sequencing if credit is tight), not a data dependency.
**Ordering rationale:** free local data before paid sessions (9 before 10); calibration before pre-registration (n and thresholds need pilot numbers); pre-registration before any counted run (post-hoc claim sizing is unrecoverable); RQ3b and RQ2b-live share the same forced-compaction sessions (one campaign, two verdicts).

#### Phase Details (v3.0)

##### Phase 9: Free-Corpus Harness Construction

**Goal:** The entire live measurement pipeline -- transcript boundary parsing, three-layer SPF, contamination defenses -- is validated on genuine local compaction data before any live credit is spent.
**Depends on:** Nothing (v3.0 entry point; reuses v2.0 pipeline: `summary_parser`, `embedding_similarity`, `semantic_provenance_fidelity`, `capture_boundary()`/`TrialResult`)
**Requirements:** LIVE-01, LIVE-03, SPF-02
**Contract Coverage:**
- Advances: claim-compaction-survival and claim-violation-detection (builds the validated live measurement instrument both claims depend on)
- Deliverables: `tools/claude_code_transcript.py` (tolerant schema-validating parser); recalibrated three-layer SPF module; contamination tooling (hermetic temp-dir workspaces, canary nonces, automated post-run transcript audit); hash-domain partition assertion; `llm_`/`forge_` qualifier lint extended to all live-harness output paths
- Anchor coverage: local calibration corpus (10 genuine `compact_boundary` events, `~/.claude/projects`, CC 2.1.121-2.1.170); prior outputs reused: `tools/semantic_provenance_fidelity.py`, `embedding_similarity.py`, and the four forge tools (`forge_nulls.py`, `forge_chamber.py`, `forge_trace_codec.py`, `forge_reversible_summary.py`) as the forge layer the harness instruments; MiniCheck (EMNLP 2024); Zahn & Chana fact-loss anchor
- Forbidden proxies: parser validated only on synthetic summaries (registered false progress for LIVE-01); cosine-only fidelity claims (SPF-02 false progress); the fp-short-tasks gate machinery (`llm_compaction_occurred` row-level boolean + lint) is BUILT here
**Success Criteria** (what must be TRUE):

1. `tools/claude_code_transcript.py` achieves 10/10 `compact_boundary` recall on the local calibration corpus with unknown-event counter = 0; `refusal`-trigger events binned separately with the corpus-count reconciliation (10 auto/manual vs ~10 refusal records) documented; raw transcripts archived verbatim before parsing.
2. Three-layer SPF stack operational locally (token overlap + `all-MiniLM-L6-v2` cosine + MiniCheck-Flan-T5-Large NLI); tier thresholds recalibrated on the local genuine-summary corpus (synthetic 0.9/0.7 values retired); no code path reports a single layer alone.
3. MiniCheck validated at >=80% agreement against 30 hand-labeled claims (hand-labeling protocol executed on the local corpus before any live run).
4. Contamination defenses operational and tested before the pilot: hermetic temp-dir workspaces outside the repo tree (no CLAUDE.md leakage), canary nonces, automated post-run transcript audit; hash-domain partition assertion in place (no expected-hash ever computed over LLM-generated content).
5. Metrics venv resolved (torch wheel for Python 3.14 or documented 3.12 fallback); embedding and NLI backends run on the local machine at usable latency.

**Plans:** TBD (run `gpd:plan-phase 9`)

##### Phase 10: Live Driver, Pilot, and Calibration

**Goal:** Real Claude Code sessions can be driven, compaction-forced, and measured reliably, and every number campaign sizing depends on is empirically measured on the pinned CLI version.
**Depends on:** Phase 9 (validated parser and contamination defenses must exist before the first live session)
**External prerequisite:** Agent SDK monthly credit opt-in (user action; $200/mo on Max 20x, effective 2026-06-15). This is the first live-spend phase -- blocked until opted in.
**Requirements:** LIVE-02, LIVE-04
**Contract Coverage:**
- Advances: claim-compaction-survival (the forcing mechanism that makes genuine `llm_compaction` affordable: ~$0.50-2.00/session forced vs $5-15 organic)
- Deliverables: live session driver (Python `claude-agent-sdk` primary with subscription OAuth, PreCompact/PostCompact hooks, `total_cost_usd`, `--session-id` pinning; raw `claude -p --output-format stream-json` subprocess cross-check); pilot calibration report
- Anchor coverage: official ~95% trigger threshold as planning prior only (Resolved Contradiction 2 -- community ~83%/~89% figures never hard-coded); COMPUTATIONAL.md budget model; GitHub #63186 env-var caveat
- Forbidden proxies: hard-coding community threshold figures (LIVE-04 false progress); fp-short-tasks calibration half (empirical trigger floor determines what "long enough to compact" means)
**Success Criteria** (what must be TRUE):

1. Driver operational on both paths with identical `BoundaryCapture` from transcript poll vs hooks/stream signals; CLI version pinned (`DISABLE_AUTOUPDATER=1`); never `--bare`, never `--no-session-persistence`.
2. Forced `llm_compaction` verified firing with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` set in the actual process environment (GitHub #63186 settings.json caveat explicitly tested) on the pinned CLI version.
3. Pilot (5-10 sessions) measures empirical tokens-to-trigger and the practical `AUTO_COMPACT_WINDOW` floor (resolves Contradiction 2 residue), $/session from `total_cost_usd` within +/-20%, and a wall-clock sigma_d estimate for Phase 13 sizing.
4. Hook stdin field dump captured; `/compact`-in-`-p` behavior tested; budget-guarded campaign loop demonstrated reading per-session cost telemetry.
5. Contamination audit run on all pilot transcripts: zero canary leaks, no CLAUDE.md leakage detected (pilot contamination would mis-calibrate everything downstream).

**Plans:** TBD (run `gpd:plan-phase 10`)

##### Phase 11: Pre-Registration Gate

**Goal:** A hard, committed pre-registration artifact fixes every statistical and design decision before the first counted run -- post-hoc claim sizing is unrecoverable.
**Depends on:** Phase 10 (n targets and thresholds need pilot numbers: trigger floor, $/session, sigma_d)
**Requirements:** PREG-01
**Contract Coverage:**
- Advances: claim-violation-detection and claim-compaction-survival (claim phrasing, sidedness, and inclusion rules are fixed here); ref-mock-experiment carry-forward at planning stage (comparison protocol against the MockLM ceiling committed before data)
- Deliverables: committed pre-registration protocol document; `GPD/CONVENTIONS.md` entries (CP sidedness with dual-convention mapping, observational-vs-controlled reframing)
- Anchor coverage: Hanley & Lippman-Hand rule of three; project CP history (mock 0/211 -> 1.41% one-sided / 1.73% two-sided, restated under both conventions); v2.0 statistical conventions; simulated 0.93->0.25 reachability curve
- Forbidden proxies: post-hoc claim sizing (PREG-01 false progress); fp-shallow-traces (subset must be marker-dense); fp-short-tasks gate committed as row-level inclusion criterion; M1 curve-conflation (simulated curve labeled harness-anchor-only, never a live prediction)
**Success Criteria** (what must be TRUE):

1. Committed protocol exists before any counted run: task subset selected from the 20-task adversarial corpus (resolves the open context gap on the live task corpus), n=30 primary / n=59 escalation, exclusion rules.
2. CP sidedness decision committed (one-sided recommended per Resolved Contradiction 1) with the mandatory dual-convention mapping table; no table ever mixes conventions; sample-size consequences stated under the chosen convention.
3. Typed run-termination taxonomy committed (`completed`/`rate_limited`/`no_compaction_triggered`/...) with the claim table per n -- failed/interrupted runs are typed data, never silent discards.
4. Simulated 0.93->0.25 curve labeled harness-anchor-only and the observational-vs-controlled reframing entered in `GPD/CONVENTIONS.md` (Resolved Contradiction 3).

**Plans:** TBD (run `gpd:plan-phase 11`)

##### Phase 12: Live Compaction and Violation Campaign (RQ3b + RQ2b-live)

**Goal:** RQ3b and RQ2b-live are answered on the real substrate: semantic and structural provenance survival measured through genuine Claude Code auto-compaction, and the live natural-violation rate bounded -- this phase is the milestone's scientific content, with a genuinely open outcome.
**Depends on:** Phase 11 (no counted run before the committed pre-registration)
**Requirements:** COMP-05, VIOL-05
**Contract Coverage:**
- Advances: claim-compaction-survival (decisive -- test-compaction-provenance) and claim-violation-detection (decisive -- test-real-violation; if zero live events, reported as a live zero-event upper bound under the CC-015 structural-prevention framing, never as silence)
- Deliverables: live compaction report with three-layer SPF + structural/semantic reachability + per-event `preTokens`/`postTokens` compression (deliv-compaction-report evidence); live violation report with session-level CP bound, cluster bootstrap, Bayesian posterior, full typed-termination denominator table (deliv-violation-report evidence)
- Anchor coverage: ref-mock-experiment COMPARED at execution (MockLM ceiling: 100% reachability, 6/6 violations, ~1.096x compression -- gaps explained per the acceptance test); Zahn & Chana ~60% single-pass fact-loss external anchor; `data/baselines/baseline-report.json` (uninstrumented comparison); mock 0/211 bound compared hierarchically, NEVER pooled (mock = tight bound under controlled conditions, live = coarser bound on the real substrate)
- Forbidden proxies: fp-short-tasks ENFORCED (a run contributes to compaction metrics ONLY with a transcript-verified `compact_boundary` record -- the row-level `llm_compaction_occurred` gate); fp-shallow-traces (marker-dense tasks; zero-compaction control arm doubles as the SPF ~ 1 calibration check); fp-synthetic-only (the live natural bound is the direct antidote); per-ref Bernoulli counting (fabricated n); claiming mock 211-run precision from n=30/59
**Success Criteria** (what must be TRUE):

1. n=30 forced-compaction sessions completed (pre-registered escalation to 59 only if clean and budgeted) over marker-dense corpus tasks in hermetic workspaces, every counted row passing the `llm_compaction_occurred` gate; two-tier reporting (runs-with-compaction vs runs-total); override value reported as an experimental parameter.
2. Three-layer SPF measured on real Claude Code compaction summaries plus structural and semantic reachability on live chambers, with exact `preTokens`/`postTokens` compression recorded per event; the zero-compaction control arm shows SPF ~ 1 (if not, instrumentation itself is confounding -- halt and investigate).
3. Recovery probes executed via `--resume`/`fork_session`; results compared against the Zahn & Chana ~60% anchor and the MockLM ceiling with all gaps explained -- the test-compaction-provenance pass condition (reachability measured and gaps explained; violation detection functional post-compaction).
4. Live natural-violation bound computed: session-level binary outcome at the pre-registered CP sidedness (closed-form recomputation check), per-ref rates via cluster bootstrap (10K resamples), Bayesian Beta posterior alongside; live violations separated from the Datadog-class explicit-error background; claims phrased at live precision only.
5. A verdict on claim-violation-detection is rendered either way: >=1 naturally-occurring violation documented with baseline comparison (test-real-violation pass), or a live zero-event upper bound under CC-015 -- with zero silent run discards (full denominator accounting).

**Plans:** TBD (run `gpd:plan-phase 12`)

##### Phase 13: Instrumentation Overhead Campaign (RQ5)

**Goal:** Forge instrumentation overhead on live sessions is quantified with a CI-based decision against the <20% target, with task success as co-primary -- the evidence the instrumentation-vs-augmentation distinction (vs Khanal et al.) needs.
**Depends on:** Phase 11 (paired design pre-registered); runs parallel with Phase 12 across rate-limit windows
**Requirements:** OVER-01
**Contract Coverage:**
- Advances: the contract's registered disconfirming observation ("forge adds latency/complexity without catching real failures") and stop/rethink condition ("typed absence adds complexity without measurable reliability gains") are directly tested here
- Deliverables: overhead report with CI decision (token-ratio 95% CI upper bound vs 1.20)
- Anchor coverage: instrumented arm uses the four forge prior outputs (`forge_nulls.py`, `forge_chamber.py`, `forge_trace_codec.py`, `forge_reversible_summary.py`); v1.0 three-tier baseline design and `data/baselines/baseline-report.json`; Flowcept/OTel <1-5% ecosystem claims labeled vendor-sourced
- Forbidden proxies: wall-clock-only differencing under LLM latency variance (OVER-01 false progress)
**Success Criteria** (what must be TRUE):

1. 5-pair pilot estimates sigma_d; documented decision whether wall-clock can resolve the 20% threshold or token-primary stands alone (if sigma_d > 0.5, token-primary alone -- pre-registered hedge).
2. 12-23 paired randomized interleaved A/B runs completed; token overhead from all four usage buckets (input/output/cache-read/cache-write) is the primary metric; direct forge-call timing secondary; wall-clock descriptive only.
3. Decision rule applied: 95% CI upper bound of the overhead ratio < 1.20 -> RQ5 verdict; the dry-run harness recovers an injected 20% synthetic overhead before live pairs count.
4. Task success measured as co-primary; overhead declared uninterpretable if instrumentation changes success rates (then the divergence itself is the finding).

**Plans:** TBD (run `gpd:plan-phase 13`)

##### Phase 14: Synthesis and Verdict Regeneration

**Goal:** The project's verdict record reflects exactly the evidence held: mock-backend qualifiers removed precisely where live evidence lands and retained everywhere it does not.
**Depends on:** Phases 12 and 13
**Requirements:** XREF-04
**Contract Coverage:**
- Advances: final contract deliverables -- deliv-violation-report and deliv-compaction-report regenerated with live evidence; ref-mock-experiment comparison surfaced at verification (required action: compare, third carry-forward stage)
- Deliverables: regenerated `data/synthesis/rq-verdicts.json` (schema-valid against synthesis.v1); regenerated violation and compaction reports with hierarchical claim phrasing and full termination-state denominators
- Anchor coverage: pre-stated criteria matrix (v1.0 convention); MockLM ceiling and mock 0/211 bound restated with qualifiers per the Phase 11 dual-convention table
- Forbidden proxies: removing mock qualifiers where only mock evidence exists (XREF-04 false progress); publication-precision language (live claims never borrow mock precision)
**Success Criteria** (what must be TRUE):

1. `data/synthesis/rq-verdicts.json` regenerated and schema-valid; the mock-backend qualifier is removed for exactly the claims where live evidence landed and retained for all others (per-claim evidence provenance check).
2. Violation and compaction reports carry hierarchical claim phrasing (mock = tight bound under controlled conditions; live = coarser bound on the real substrate) and the full typed-termination denominator table; MockLM comparison included per both contract acceptance tests.
3. Entire existing test suite (~537 tests) green plus the new harness tests (full pytest run).
4. RQ3b, RQ2b-live, and RQ5 verdicts rendered against the pre-stated criteria; contract stop/rethink conditions explicitly evaluated and the outcome documented.

**Plans:** TBD (run `gpd:plan-phase 14`)

#### Risk Register (v3.0)

| Phase | Top Risk | Probability | Impact | Mitigation |
|-------|---------|:-:|:-:|-----------|
| 9 | torch wheel unavailable for Python 3.14 | LOW | LOW | 3.12 venv fallback (pre-identified) |
| 10 | Agent SDK credit not opted in, or env-var forcing fails on pinned CLI (#63186) | MEDIUM | HIGH | External prerequisite flagged at phase entry; env vars set in process environment and firing verified in pilot; fallback: organic-trigger sessions (~10x cost) with campaign resized in Phase 11 |
| 11 | CP sidedness choice fragments comparability with published v1.0/v2.0 numbers | LOW | MEDIUM | Mandatory dual-convention mapping table; exactly one convention per table |
| 12 | Contamination (evaluation-aware model + CLAUDE.md leakage) invalidates counted runs | MEDIUM | HIGH | Hermetic workspaces + canary nonces + automated post-run audit from pilot onward; batch invalidation rule (mid-phase checkpoint, not just boundary) |
| 12 | Rate limits / provider-side policy drift mid-campaign | MEDIUM | MEDIUM | Budget-guarded loop on `total_cost_usd`; schedule across 5-hour windows with >=30% headroom; `rate_limited` is a typed termination row, never a discard |
| 13 | Wall-clock noise (sigma_d > 0.5) cannot resolve the 20% threshold | MEDIUM | MEDIUM | Token-primary metric stands alone (pre-registered hedge); decomposed measurement (direct forge timing + tokens) instead of wall-clock differencing |
| 14 | Mock qualifier removed where only mock evidence exists | LOW | HIGH | Per-claim evidence provenance check; schema validation + full test suite as gates |

#### Backtracking Triggers (v3.0)

- **Phase 10 -> 9:** unknown-event counter > 0 on pilot transcripts (schema drift on the pinned version) -- extend the parser against archived raw transcripts before any campaign run (re-parse, not re-run).
- **Phase 12 -> 10:** forced-compaction firing rate or $/session deviates >2x from pilot calibration -- halt the campaign and re-calibrate before more counted runs.
- **Phase 12 -> 9/10:** canary leak detected in any counted batch -- invalidate the batch, harden contamination tooling, resume only after a clean audit.
- **Phase 12 (internal):** zero-compaction control arm shows SPF substantially < 1 -- instrumentation itself is confounding; halt and investigate before trusting any SPF number.
- **Phase 13 (internal):** instrumented vs uninstrumented task success rates diverge materially -- overhead ratios uninterpretable; revisit design before claiming RQ5.
- **Milestone stop/rethink (contract):** typed absence adds complexity without measurable reliability gains (e.g., RQ5 CI upper bound >= 1.20 combined with no live detection value); provenance chains fail systematically under real compaction (claim-compaction-survival fails -- document honestly, do not soften); compaction grounding too brittle for meaningful return paths.

#### Coverage (v3.0)

| Objective | Phase | Status |
| --------- | ----- | ------ |
| LIVE-01 | Phase 9 | Pending |
| LIVE-03 | Phase 9 | Pending |
| SPF-02 | Phase 9 | Pending |
| LIVE-02 | Phase 10 | Pending |
| LIVE-04 | Phase 10 | Pending |
| PREG-01 | Phase 11 | Pending |
| COMP-05 | Phase 12 | Pending |
| VIOL-05 | Phase 12 | Pending |
| OVER-01 | Phase 13 | Pending |
| XREF-04 | Phase 14 | Pending |

10/10 objectives mapped, no orphans, no duplicates. All contract-critical items (2 claims, 2 live deliverables, 1 must-read anchor, 4 prior outputs, 1 known-good baseline, 3 forbidden proxies, 3 crucial inputs, 1 context gap) surfaced in at least one phase's contract coverage.

## Progress

| Milestone | Phases | Plans | Status | Completed |
| --- | --- | --- | --- | --- |
| v1.0 Typed Absence and Provenance Validation | 5 | 12 | Complete | 2026-03-16 |
| v2.0 The Forgetting Agent | 3 | 13 | Complete | 2026-03-28 |
| v3.0 Live Validation | 6 (9-14) | TBD | Not started | - |

### v3.0 Phase Progress

**Execution order:** 9 -> 10 -> 11 -> {12 parallel with 13} -> 14

| Phase | Plans Complete | Status | Completed |
| ----- | -------------- | ------ | --------- |
| 9. Free-Corpus Harness Construction | 0/TBD | Not started | - |
| 10. Live Driver, Pilot, and Calibration | 0/TBD | Not started (external prerequisite: Agent SDK credit opt-in) | - |
| 11. Pre-Registration Gate | 0/TBD | Not started | - |
| 12. Live Compaction and Violation Campaign | 0/TBD | Not started | - |
| 13. Instrumentation Overhead Campaign | 0/TBD | Not started | - |
| 14. Synthesis and Verdict Regeneration | 0/TBD | Not started | - |
