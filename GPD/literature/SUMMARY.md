# Research Summary: Primordial v3.0 "Live Validation"

**Project:** Primordial Computing — Typed Absence and Provenance in Agentic Systems
**Domain:** LLM agent reliability — live compaction fidelity (RQ3b), live violation rates (RQ2b), instrumentation overhead (RQ5)
**Researched:** 2026-06-12 (synthesis of METHODS.md, PRIOR-WORK.md, COMPUTATIONAL.md, PITFALLS.md)
**Confidence:** HIGH overall — all four inputs are unusually well-grounded (official docs fetched, local transcripts inspected, statistics recomputed exactly); residual MEDIUM items are flagged per-finding

> Provenance note: synthesized by gpd-research-synthesizer (run 2026-06-12); the subagent's file write was blocked by a harness restriction, so the orchestrator materialized this file verbatim from the agent's typed return.

## Unified Notation and Conventions

| Term / Symbol | Meaning | Binding Convention |
| --- | --- | --- |
| compaction | context-reduction event | NEVER unqualified: `llm_` (lossy semantic, Claude Code native) vs `forge_` (lossless hash-verified). Extend the existing lint to all live-harness output paths. |
| SPF | Semantic Provenance Fidelity | Three-layer stack: SPF_jaccard/SPF_weighted (token), SPF_embedding (cosine), SPF_entailment (NLI, NEW). Position explicitly relative to AAR "provenance coverage/soundness" (arXiv:2602.13855) in the paper milestone. |
| p_U | zero-event 95% CP upper bound | **CONFLICT RESOLVED below.** One-sided: p_U = 1 − 0.05^(1/n). Two-sided (project-historical): p_U = 1 − 0.025^(1/n). Every table must state which. |
| trial / session / run | unit definitions | trial = one task attempt; session = one CLI session UUID; a trial spans sessions only via documented `--resume` (stratified, never silently mixed); compaction events counted per event |
| `llm_compaction_occurred` | row-level boolean gate | A run contributes to compaction metrics ONLY if its transcript contains a verified `compact_boundary` record (fp-short-tasks gate) |
| hash verification | integrity claim | Permitted ONLY over forge-layer artifacts (deterministic, self-generated). No code path may compute an expected hash over LLM-generated content (live non-determinism). |
| trigger | compaction cause stratum | `auto` / `manual` / `refusal` (third class observed on disk, undocumented) — always recorded, always stratified |
| token accounting | usage measurement | CLI usage-event fields only (input / output / cache-read / cache-write, all four buckets); local tokenizer estimates are pre-run sizing only |
| controlled vs observational | claim type | API-track (`pause_after_compaction`, controlled) and live-track (Claude Code, observational) answer different questions and are NEVER pooled (resolves Pitfall M2) |

### Resolved Contradiction 1: Clopper-Pearson sidedness (convention conflict, found during synthesis)

METHODS.md computes one-sided 95% upper bounds (0/30 → 9.50%, 0/59 → 4.95%, 0/211 → 1.41%). PITFALLS.md and ALL published v1.0/v2.0 numbers use the two-sided 95% CI upper limit (0/30 → 11.6%, 0/211 → 1.73%, 0/321 → 1.14%). Both are arithmetically correct (recomputed this session, both formulas verified); they are different conventions, and METHODS switched without flagging it. **Resolution: pre-register the one-sided bound as primary for v3.0** — the claims are inherently one-sided ("rate < X"), and one-sided is what Hanley & Lippman-Hand's rule of three approximates. Restate mock baselines under it (0/211 → 1.41% one-sided; 1.73% is the historical two-sided value) via a mandatory dual-convention mapping row; add a conventions-ledger entry. Sample-size consequences under each convention: "<10%" claim needs n=29 (one-sided) or n=36 (two-sided); "<5%" needs n=59 or n=72. If the pre-registration phase instead prioritizes continuity with published numbers, choose two-sided and resize accordingly — but choose exactly one and state it in every table. [CONFIDENCE: HIGH for the resolution; the choice itself is a pre-registration decision]

### Resolved Contradiction 2: auto-compact trigger threshold

Three values circulate: ~83%/166K (community: claudefa.st, TurboAI, GitHub issue #31806; cited in PITFALLS), ~89% formula (Vaughan practitioner series; cited in PRIOR-WORK), ~95% (official env-vars docs; cited in COMPUTATIONAL, and consistent with the on-disk 1M-window event compacting at 97%). All sources agree the override is **lower-only**. **Resolution: use the official ~95% as the planning prior; the community figures are version-sensitive and possibly window-size-dependent; the empirical value on the pinned CLI version is a mandatory Phase 1 pilot measurement** (both PRIOR-WORK and PITFALLS independently flag this; COMPUTATIONAL's validation plan includes it). Planning never hard-codes any of the three figures. Note from this synthesis's verification: GitHub issue #63186 reports `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in a settings.json `env` block being silently ignored — set it in the actual process environment and verify firing in the pilot. [Unresolved residue → Phase 1]

### Resolved Contradiction 3: prior protocol rejected Claude Code transcripts (Pitfall M2)

`docs/phase-2.1-genuine-compaction-protocol.md` §3.3 rejected Claude Code transcripts ("cannot control compaction timing, cannot pause at boundary, cannot reproduce"); v3.0 builds on exactly that substrate. **Resolution: reframe up front in the roadmap — the live track is observational/ecological validation, a different claim type from the API-track controlled design; results are reported in separate sections and never pooled.** Add a conventions-ledger cross-reference row. The three-signal detection scheme (PreCompact/PostCompact hooks + transcript poll + stream events) substitutes for `pause_after_compaction` at observational fidelity.

## Executive Summary

v3.0's task is to convert v2.0's "pipeline-validated, pending live validation" verdicts into live results by driving real Claude Code sessions through the user's subscription (Agent SDK / `claude -p` subprocess — no paid API key anywhere). The literature position is strikingly favorable: the survey confirms (searched 2026-06-12) that **nobody has published per-pass semantic fidelity through a coding agent's native compaction** (Zahn & Chana measured their own summarization pipeline — 60% fact loss, 54% cascading constraint erosion, independently verified this session; Vaughan documented mechanics without fidelity numbers), **no typed-violation rate on live agent runs exists** (Datadog measures only explicit errors; Liu measures aggregate entropy; Khanal et al. measure meltdown heuristically), and **the flagship provenance paper (PROV-AGENT) explicitly omits overhead measurement** — RQ3b, RQ2b-live, and RQ5 each fill a verified, stated gap.

The recommended approach is fully specified and largely de-risked by direct local evidence: drive sessions via the Python Agent SDK (subprocess fallback as cross-check), force genuine auto-compaction cheaply with the official `CLAUDE_CODE_AUTO_COMPACT_WINDOW` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env vars (~$0.50–2.00/session vs $5–15 organic — the single highest-leverage cost finding, web-verified), detect via transcript-poll-primary three-signal scheme (`compact_boundary` schema verified on disk), and measure SPF with a three-layer stack adding MiniCheck-Flan-T5-Large NLI scoring (GPT-4-level grounding checks at 770M params, ~400× cheaper, verified) to close cosine similarity's blindness to negation/number flips. A free calibration corpus of 10 genuine local compaction events (plus ~10 undocumented `refusal`-trigger events to bin separately) lets the entire parser/metric pipeline be built and validated at zero live spend.

The principal risks are (1) fp-short-tasks — the project's own registered forbidden proxy — neutralized by the hard `llm_compaction_occurred` row-level gate; (2) the budget gate — the Agent SDK monthly credit ($200/mo on Max 20x, effective 2026-06-15, **one-time user opt-in required**, hard stop when depleted) caps campaign size and is a Phase 1 blocker until opted in; (3) overclaiming precision — a live n=30 supports "<10%" (one-sided), not the mock campaign's 1.41%/1.73%; matching mock precision requires 211 live runs and must not be claimed from a subset; and (4) contamination — evaluation-aware Claude models plus auto-loaded CLAUDE.md memory demand hermetic workspaces and canary audits from the pilot onward. The strategic framing risk is Khanal et al.'s "memory scaffold never helps" result: v3.0 must draw the instrumentation-vs-augmentation distinction explicitly (forge tracks typed state without injecting summaries into context), and RQ5's overhead data is exactly the evidence that distinction needs.

## Critical Claim Verification

| # | Claim | Source | Verification | Result |
|---|-------|--------|--------------|--------|
| 1 | Agent SDK monthly credit: $200/mo Max 20x, effective 2026-06-15, one-time opt-in, drains first, hard stop without usage credits | COMPUTATIONAL | WebSearch → support.claude.com article 15036540 + multiple independent 2026-06 secondary sources | CONFIRMED |
| 2 | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` + `CLAUDE_CODE_AUTO_COMPACT_WINDOW` exist; override is lower-only | COMPUTATIONAL, PITFALLS | WebSearch → official docs + GitHub issues #31806, #36381, #63186 | CONFIRMED (plus new caveat: settings.json env block silently ignored, #63186) |
| 3 | CP bound arithmetic (n=30/59/211 tables) | METHODS, PITFALLS | Executed Python recomputation this session | CONFIRMED — but two different sidedness conventions detected (Contradiction 1) |
| 4 | MiniCheck-Flan-T5-Large: GPT-4-parity grounding verification, ~400× cheaper, EMNLP 2024 | METHODS | WebSearch → ACL Anthology 2024.emnlp-main.499, HF model card, repo | CONFIRMED |
| 5 | Zahn & Chana arXiv:2603.17781: 60% fact loss per summarization pass, 54% cascading constraint erosion, 100% in-context ceiling to 7,000 facts, KO 252× cheaper | PRIOR-WORK, METHODS | WebSearch → arXiv abstract + alphaXiv | CONFIRMED |
| 6 | Auto-compact default threshold ~95% (official) vs ~83% (community) | COMPUTATIONAL vs PITFALLS | WebSearch surfaced both figures persisting | CONFLICTING — resolved as Contradiction 2 (pilot recalibration mandatory) |
| 7 | Transcript `compact_boundary` schema, 9-section summary template, trigger values {auto, manual, refusal} | METHODS, COMPUTATIONAL | Both researchers independently inspected the same local disk data and agree | CONFIRMED (internal cross-check; re-validate per CLI version) |

## Key Findings

### Methods (from METHODS.md)

- **Three-layer SPF stack** [HIGH]: keep token-overlap and embedding layers; add MiniCheck-Flan-T5-Large entailment scoring (summary claim → original artifact direction) to catch factual flips cosine misses. Backend: `all-MiniLM-L6-v2` on CPU (symmetric STS task, no prefix discipline needed, fits M1 Pro); `bge-small-en-v1.5` as quality fallback. The 0.9/0.7 tier thresholds are synthetic-calibrated and **not transferable across backends — recalibrate on the 10 local genuine summaries**. Never report one layer alone.
- **Zero-event statistics** [HIGH]: primary live target **n = 30 sessions** ("<10%" one-sided claim if clean), pre-registered escalation **n = 59** ("<5%"). **Session-level binary outcome** for the CP bound (refs within a session share one compaction event — per-ref Bernoulli counting fabricates sample size); per-ref rates via cluster bootstrap resampling sessions. Fixed pre-registered n; early stopping on a violation is free (the violation becomes the finding); Bayesian Beta posterior reported alongside per v2.0 convention.
- **Overhead (RQ5)** [HIGH on design, LOW on pre-pilot variance]: token overhead is the primary metric (deterministic); wall-clock secondary via paired, randomized-order, interleaved A/B, analyzed as log-scale geometric-mean ratio with bootstrap CI; decision rule = 95% CI upper bound < 1.20. **5-pair pilot first** to estimate σ_d; expect ~12–23 pairs; if σ_d > 0.5 wall-clock cannot resolve 20% and token-primary stands alone. Task success is co-primary (overhead is uninterpretable if instrumentation changes success rates).
- **Transcript forensics** [HIGH — verified on disk]: parse `~/.claude/projects/<munged-cwd>/<session>.jsonl` for `compact_boundary` + `isCompactSummary`; anchor summary segmentation on the exact 9 known section headers (generic numbered-header regex produces false positives — observed); `compactMetadata.preTokens/postTokens/durationMs` give compression ratio and compaction latency for free.

### Prior Work (from PRIOR-WORK.md)

- **Niche confirmed open** [HIGH]: no published measurement of fact/constraint survival through Claude Code's actual auto-compact (RQ3b); no typed-violation rate on live runs (RQ2b); no peer-reviewed provenance-capture overhead in agentic settings (RQ5 — PROV-AGENT verified to omit it; Flowcept's <5% is vendor docs).
- **Must-engage counterargument** [HIGH]: Khanal et al. (arXiv:2603.29231) — "the memory scaffold never helps" (6/10 models hurt). Distinction to hold: their scaffold injects retrieved summaries into context; forge tracks typed state out-of-band. If overhead/interference data blurs this, the project claim weakens.
- **Framing counter-position** [MEDIUM]: Liu (arXiv:2606.08162) claims silent failure is intrinsic/inevitable (entropy model; quantitative details unaudited — single-author preprint days old). CC-015's structural-prevention reframe is the natural counter-thesis; a clean live zero-violation bound is direct evidence against inevitability at the typed-violation level.
- **Benchmark anchors**: Zahn & Chana 60%/54% (upper-bound analogue — their pipeline, not native compaction); zero-compaction control = SPF ≈ 1 expected (in-context ceiling 100% to 7,000 facts) — if sub-trigger sessions show SPF < 1, the instrumentation itself is confounding; Datadog 2–5% explicit-error floor — live violations must be separated from mundane API-error background; Khanal 13–19% meltdown base rate at very-long horizons sets expected behavioral noise.
- **Do NOT cite**: "65% of enterprise AI failures traced to context degradation" — SEO-grade claim, no primary source found.

### Computational Approaches (from COMPUTATIONAL.md)

- **Stack** [HIGH — verified against installed CLI v2.1.170 + official docs]: Python `claude-agent-sdk` primary (in-process hooks, `fork_session`, `total_cost_usd`, `RateLimitEvent`), raw `claude -p --output-format stream-json` subprocess as cross-check. Subscription OAuth inherited from the CLI; never `--bare` (breaks subscription auth), never `--no-session-persistence` (destroys the measurement artifact), `--session-id` pins the transcript path a priori.
- **Forced compaction** [HIGH]: env-var threshold lowering (e.g., window 50K × 60% ⇒ trigger ≈30K tokens) makes genuine auto-compaction ~10× cheaper than organic 190K buildup. Token pressure via model/user text, not giant tool outputs (possible microcompaction deflation, MEDIUM). The old API-track `_run_live()` (`compact_20260112` beta) is dead under the no-API rule — `--betas` is API-key-only, verified.
- **Budget model** [HIGH]: $200/mo Agent SDK credit (opt-in!) ⇒ forced-compaction sessions ~$0.50–2.00 each; a 50-session campaign ≈ $25–100 fits one monthly credit; 200 sessions may span two. Budget-guarded campaign loop reading `total_cost_usd` per session is mandatory.
- **Integration is mostly reuse** [HIGH]: `summary_parser`, `embedding_similarity`, `semantic_provenance_fidelity` unchanged (summary is plain text); `capture_boundary()`/`TrialResult` reused; new ~150-line `tools/claude_code_transcript.py`; `campaign_runner.py` claude-code backend stub implemented to the existing result-dict contract; exact `preTokens/postTokens` replaces the word-count compression estimate.

### Pitfalls (from PITFALLS.md — top items by severity)

1. **fp-short-tasks (Critical)** — runs that never compact must not count toward compaction metrics. Hard gate: transcript-verified `llm_compaction_occurred` as row-level inclusion criterion; two-tier reporting (runs-with-compaction vs runs-total); pilot threshold calibration; report the override value as an experimental parameter.
2. **Contamination (Critical)** — evaluation-aware models + auto-loaded CLAUDE.md memory describing this very experiment. Hermetic temp-dir workspaces outside the repo tree, out-of-band instrumentation, canary nonces, automated post-run transcript audit — **before the pilot**, since pilot contamination mis-calibrates everything downstream.
3. **Non-determinism vs hashes (Critical)** — no temperature/seed control exists (verified); temp-0 is non-deterministic anyway. Partition the hash domain: hashes verify forge-layer artifacts only; lint/assertion that no expected-hash is computed over LLM content.
4. **Format drift (Critical)** — stream-json and transcript schemas are explicitly undocumented; CLI auto-updates. Pin CLI version (`DISABLE_AUTOUPDATER=1`), archive raw transcripts verbatim before parsing (highest-leverage rule: parser bug costs a re-parse, not a re-run), tolerant schema-validating parser with campaign-halting unknown-event counter, canary parse preflight per batch.
5. **Small-n traps (Critical)** — pre-register task subset, n, exclusions, and the claim table before run 1; phrase live claims at live precision; clustered SEs (20 tasks reused across runs ⇒ up to 3× naive-SE inflation, Miller 2024); failed/interrupted runs are typed data (`rate_limited`, `no_compaction_triggered`, ...), never silent discards.
6. **Overhead confounds / rate limits (Critical)** — cache-TTL and limit policy changed provider-side mid-2026 without announcement; decompose (direct forge timing + tokens) rather than difference wall-clocks; schedule across 5-hour windows with ≥30% headroom; stratify by cache telemetry.
7. **M1 curve conflation (Moderate)** — the simulated 0.93→0.25 reachability curve is uniform deletion; live summarization is salience-biased. Pre-register it as a harness validation anchor only; live curves are new findings, not replication tests.

## Approximation Landscape

| Method / Shortcut | Valid Regime | Breaks Down When | Controlled? | Complements |
| --- | --- | --- | --- | --- |
| Env-var lowered trigger (~30K) | Campaign bulk; disclosed parameter | Pre-compaction context unrepresentative of 190K production; floor unknown | Yes — override value reported, held constant | Small organic-trigger stratum if budget allows |
| Manual `/compact` | Pipeline dev/calibration only | Counted runs (compresses tiny context → inflated survival) | Yes — `trigger` stratification | Auto-trigger for headline campaign |
| SPF_embedding (cosine) | Topical similarity | Negation/number flips embed close | No | SPF_entailment (MiniCheck) |
| SPF_entailment (NLI) | Claim-level grounding | Long-input chunking; M1 latency 1–5 s/claim | Partially (validated vs 30 hand-labeled claims, ≥80% pre-registered) | Token + embedding layers |
| Session-level CP at n=30 | "<10%" one-sided claims | Claiming mock-equivalent (1.41%) precision | Yes — exact bound | n=59 escalation; Bayesian posterior |
| Token-overhead primary | Deterministic, load-independent | Doesn't capture latency UX | Yes | Direct forge-call timing; paired wall-clock descriptive |
| Simulated deletion curve | Harness regression anchor | Read as live prediction (different generating process) | N/A | Live curve measured fresh |
| LLM-as-judge via `claude -p` | Labeled exploratory annex only | Primary metric (Claude judging Claude's compaction — circular) | No | MiniCheck primary |

**Coverage gap:** no method measures semantic fidelity of *microcompaction* (tool-output offloading) — officially undocumented, no transcript marker; v3.0 sidesteps by delivering token pressure via text (disclosed design limitation).

## Theoretical Connections

1. **fp-short-tasks gate ↔ zero-compaction control arm** [Established]: sub-trigger runs are forbidden as compaction evidence but are exactly the SPF ≈ 1 control (Zahn & Chana in-context ceiling). One design element serves both integrity and calibration.
2. **Typed absence applied to the campaign itself** [Established, internal]: the typed interruption taxonomy (`completed`/`rate_limited`/`no_compaction_triggered`/...) is the project's own ontology used as experimental hygiene — silent run-dropping would be ideologically incoherent and statistically biased.
3. **Instrumentation ≠ memory augmentation** [Conjectured — RQ5 tests it]: forge avoids Khanal's scaffold penalty because it injects nothing into context. Overhead data near the ecosystem floor (<5% Flowcept claim) would make this sharp; >20% would be a real negative result.
4. **Structural prevention vs entropy inevitability** [Conjectured]: CC-015's reframe directly opposes Liu's inevitability thesis at the typed-violation level; the live zero-event bound is the discriminating observable.
5. **Compression ratio unification** [Established]: `preTokens/postTokens` from `compactMetadata` gives the exact llm_compaction compression measurement, replacing estimates and cross-referencing the forge_compaction ratio (1.18x v1.0; MockLM ~1.096x) — always with qualifiers.

## Cross-Validation Matrix

| | Transcript poll | Hooks/stream | Mock pipeline | External anchor |
|---|---|---|---|---|
| SDK driver path | identical transcript ⇒ identical BoundaryCapture | in-process hook callbacks | dry-run with 9-section synthetic summaries | — |
| Subprocess path | same | sentinel-file hooks | same | — |
| SPF stack (3 layers) | inputs from verified boundaries | — | recalibrated on 10 local events | Zahn & Chana 60% single-pass loss |
| Live violation rate | `llm_compaction_occurred` gate | — | hierarchical vs 0/211 mock (coarser bound, never pooled) | Datadog explicit-error floor 2–5% |
| Overhead (tokens) | usage fields | — | dry-run recovers injected 20% synthetic overhead | OTel/Flowcept <1–5% claims (vendor) |

No recommended method lacks an independent cross-check. The weakest-anchored method is wall-clock overhead (noise may be unresolvable — pilot σ_d decides; token-primary is the hedge).

## Input Quality → Roadmap Impact

| Input File | Quality | Affected Recommendations | Impact if Wrong |
|------------|---------|------------------------|-----------------|
| METHODS.md | good (exact arithmetic, local data) | SPF stack, n targets, overhead design | Re-size campaign; CP sidedness already caught and resolved |
| PRIOR-WORK.md | good (sources fetched this session) | Niche claims, benchmark anchors, paper positioning | Niche could close if a competing paper lands — re-search at paper milestone |
| COMPUTATIONAL.md | good (CLI + docs + disk verified) | Driver stack, forcing mechanism, budget | Env vars failing on pinned version ⇒ fall back to organic sessions (10× cost, campaign shrinks) |
| PITFALLS.md | good (repo-grounded, citations) | Gates and pre-registration in every phase | Blind spots — mitigated by gates being cheap relative to campaign cost |

## Implications for Roadmap

### Suggested Phase Structure

**Phase 0 — Free-corpus harness construction (zero live spend).** Build `claude_code_transcript.py` + tolerant parser; validate on the 10 local genuine compaction events (10/10 boundary recall) and bin the ~10 `refusal`-trigger events separately; recalibrate SPF tier thresholds per backend on real summaries; pilot MiniCheck on the 9 local summaries vs 30 hand-labeled claims; hash-domain partition assertion + compaction-qualifier lint extended to live paths; hermetic workspace + canary + audit tooling; metrics venv (torch wheel check for Python 3.14, fall back to 3.12). *Delivers:* validated measurement pipeline before any credit is spent. *Avoids:* Pitfalls 2, 3, 7. *Risk: LOW. No new research needed.*

**Phase 1 — Live pilot and calibration (5–10 sessions; BLOCKED until Agent SDK credit opt-in).** Empirically measure tokens-to-trigger on the pinned CLI version (Contradiction 2); bisect the practical `AUTO_COMPACT_WINDOW` floor; verify env vars fire from process environment (issue #63186 caveat); dump hook stdin; test `/compact` in `-p` mode; measure $/session from `total_cost_usd` and latency σ_d; run the contamination audit live. *Delivers:* every number campaign sizing depends on. *Avoids:* Pitfalls 1, 4 (calibration halves). *Risk: MEDIUM (external dependencies). No new research needed — open questions are empirical, listed in COMPUTATIONAL.*

**Phase 2 — Pre-registration gate.** Committed protocol doc: task subset from the 20-task corpus, n=30 primary / n=59 escalation, **CP sidedness decision (Contradiction 1) with dual-convention mapping table**, exclusion rules, typed termination taxonomy, claim table per n, simulated 0.93→0.25 curve labeled harness-anchor-only, observational-vs-controlled reframing entered in the conventions ledger. *Avoids:* Pitfalls 5, M1, M2. *Risk: LOW.*

**Phase 3 — Live compaction campaign (RQ3b + RQ2b share sessions).** n=30 forced-compaction sessions over marker-dense corpus tasks in hermetic workspaces; `llm_compaction_occurred` gate; three-layer SPF on real summaries; structural + semantic reachability; session-level CP bound + cluster bootstrap; recovery probes via `--resume`/`--fork-session`; compare SPF against Zahn & Chana 60% and reachability against MockLM anchor (gaps explained, per the acceptance test). Escalate to n=59 only if clean and budgeted. *Cost:* ~$15–60 (+$15–60 escalation) of the $200/mo credit. *Risk: HIGH — genuinely open outcome (this is the science).* Flag for `gpd:research-phase` only if Phase 1 invalidates the forcing mechanism.

**Phase 4 — RQ5 overhead campaign.** 5-pair pilot → σ_d → 12–23 paired, randomized, interleaved A/B runs; token-overhead primary with CI-based decision rule (<1.20 upper bound), direct forge-call timing second, wall-clock descriptive; co-primary task success. Can interleave with Phase 3 scheduling across rate-limit windows; budget-gate sequencing if credit is tight. *Avoids:* Pitfall 4. *Risk: MEDIUM.*

**Phase 5 — Synthesis and verdict regeneration.** Regenerate `data/synthesis/rq-verdicts.json` removing mock-backend qualifiers exactly where live evidence lands; hierarchical claim phrasing (mock = tight bound under controlled conditions; live = coarser bound on the real substrate); full termination-state denominator table; violation and compaction reports per the contract deliverables. *Risk: LOW.*

### Phase Ordering Rationale

Free local data before paid sessions (Phase 0 → 1); calibration before pre-registration (n and thresholds need pilot numbers); pre-registration before any counted run (Pitfall 5 is unrecoverable post hoc); RQ3b/RQ2b share the same forced-compaction sessions (one campaign, two verdicts); RQ5 needs its own paired design but the same harness.

### Research Flags

- **Well-established procedure (skip extra research):** Phases 0, 2, 5 — fully specified by the input files.
- **Empirical unknowns resolved in-phase:** Phase 1 (trigger threshold, env-var floor, `/compact` in `-p`, refusal semantics, σ_d).
- **Genuinely open outcomes:** Phase 3 (does the 0-violation finding transfer live? what is real SPF through native compaction?) and Phase 4 (does overhead clear 20%?). These are the milestone's scientific content — uncertainty here is the point, not a planning defect.

## Confidence Assessment

| Area | Confidence | Notes |
| --- | --- | --- |
| Methods | HIGH | Exact arithmetic recomputed; SPF stack peer-reviewed components; weakest anchor = pre-pilot σ_d (LOW) and MiniCheck M1 latency (MEDIUM) |
| Prior Work | HIGH | Core papers verified against primary pages this session; Liu quantitative claims MEDIUM pending full-text audit |
| Computational | HIGH | CLI surface, schema, env vars, credit model all verified against installed binary, disk, and official docs; microcompaction MEDIUM |
| Pitfalls | HIGH | Repo-grounded + multiply-sourced; experience-based heuristics explicitly marked |

**Overall confidence: HIGH.** Gaps: empirical trigger behavior on pinned CLI version (Phase 1); Agent SDK opt-in state (user action); whether the niche stays open until the paper milestone (re-search then).

## Open Questions

1. Is the Agent SDK credit opted in on this account? [HIGH — blocks Phase 1; user action before 2026-06-15 start]
2. Empirical tokens-to-trigger and `AUTO_COMPACT_WINDOW` floor on pinned CLI? [HIGH — blocks Phase 3 sizing; Phase 1 resolves]
3. Does the mock 0-violation finding transfer to live sessions? [HIGH — Phase 3's core question]
4. CP sidedness pre-registration choice (one-sided recommended)? [HIGH — Phase 2 decision]
5. Can wall-clock resolve a 20% threshold (σ_d), or is token-primary alone? [MEDIUM — Phase 4 pilot]
6. `/compact [instructions]` inside `-p` mode? [MEDIUM — would restore instruction-bearing compaction]
7. `refusal` trigger semantics; calibration-corpus count reconciliation (METHODS: 10 events 8 auto/2 manual; COMPUTATIONAL trigger inventory adds 10 refusal records) [MEDIUM — Phase 0 inspection]
8. Microcompaction interference with tool-heavy pressure tasks? [MEDIUM — one A/B in Phase 1]
9. torch wheels for Python 3.14? [LOW — 3.12 venv fallback exists]

## Sources

Aggregated from the four research files; per-claim confidence in the source files. Highlights verified during this synthesis: support.claude.com article 15036540 (Agent SDK credit); code.claude.com env-vars/hooks/headless/agent-sdk docs; arXiv:2603.17781 (Zahn & Chana); ACL 2024.emnlp-main.499 + github.com/Liyan06/MiniCheck; anthropics/claude-code issues #31806, #36381, #63186; exact CP recomputation (this session). Key literature: arXiv:2603.29231 (Khanal et al.), arXiv:2606.08162 (Liu), arXiv:2508.02866 (PROV-AGENT), arXiv:2602.13855 (AAR), arXiv:2411.00640 (Miller), arXiv:2602.07150 (agentic eval randomness), Thinking Machines nondeterminism (2025), Vaughan compaction series (practitioner, MEDIUM), Datadog State of AI Engineering 2026. Primary local ground truth: `~/.claude/projects/**/*.jsonl` (10 compaction events, CC 2.1.121–2.1.170), installed CLI v2.1.170, repo tools and reports.

```yaml
# --- ROADMAP INPUT (machine-readable, consumed by gpd-roadmapper) ---
synthesis_meta:
  project_title: "Primordial Computing: Typed Absence and Provenance in Agentic Systems — v3.0 Live Validation"
  synthesis_date: "2026-06-12"
  input_files: [METHODS.md, PRIOR-WORK.md, COMPUTATIONAL.md, PITFALLS.md]
  input_quality: {METHODS: good, PRIOR-WORK: good, COMPUTATIONAL: good, PITFALLS: good}

conventions:
  unit_system: "N/A (software/formal-systems research); tokens and USD as resource units"
  compaction_qualifier: "llm_ vs forge_ prefix mandatory; unqualified 'compaction' forbidden"
  cp_bound_convention: "PRE-REGISTER in Phase 2: one-sided 1-0.05^(1/n) RECOMMENDED; historical project numbers are two-sided 1-0.025^(1/n); dual-convention mapping table mandatory; never mix in one table"
  unit_of_analysis: "session-level binary outcome for CP; per-ref via cluster bootstrap (resample sessions)"
  claim_types: "API-track controlled vs live-track observational — never pooled"
  hash_semantics: "hash verification claims only over forge-layer artifacts, never LLM content"

methods_ranked:
  - name: "Agent SDK / claude -p session driving with env-var forced compaction"
    regime: "subscription auth, forced trigger ~30K tokens, $0.50-2.00/session"
    confidence: HIGH
    cost: "~$25-100 per 50-session campaign vs $200/mo credit"
    complements: "raw subprocess path as observation-perturbation cross-check"
  - name: "Transcript JSONL boundary parsing (three-signal detection, poll primary)"
    regime: "pinned CLI version; schema verified 2.1.121-2.1.170"
    confidence: HIGH
    cost: "trivial, offline"
    complements: "PreCompact/PostCompact hooks + stream events as live signals"
  - name: "Three-layer SPF stack (token overlap + MiniLM cosine + MiniCheck NLI)"
    regime: "local CPU, M1 Pro 16GB; thresholds recalibrated per backend on real summaries"
    confidence: HIGH
    cost: "<1 s/pair embedding; 1-5 s/claim NLI"
    complements: "layers cross-validate; LLM-judge only as labeled exploratory annex"
  - name: "Session-level Clopper-Pearson zero-event bounds + cluster bootstrap"
    regime: "n=30 primary ('<10%' one-sided), n=59 escalation ('<5%')"
    confidence: HIGH
    cost: "negligible"
    complements: "Bayesian Beta posterior (stopping-rule-insensitive)"
  - name: "Token-primary paired interleaved overhead design"
    regime: "5-pair pilot then 12-23 pairs; CI upper bound < 1.20 decision rule"
    confidence: HIGH
    cost: "~2x campaign runtime for paired arms"
    complements: "direct forge-call timing; wall-clock descriptive only"
  - name: "Hermetic workspace + canary contamination audit"
    regime: "every live run, from pilot onward"
    confidence: HIGH
    cost: "negligible vs invalidated batches"
    complements: "post-run transcript audit as standing gate"

phase_suggestions:
  - name: "Free-corpus harness construction"
    goal: "Validated parser + recalibrated SPF stack + contamination tooling at zero live spend, using 10 local genuine compaction events"
    methods: ["Transcript JSONL boundary parsing (three-signal detection, poll primary)", "Three-layer SPF stack (token overlap + MiniLM cosine + MiniCheck NLI)", "Hermetic workspace + canary contamination audit"]
    depends_on: []
    needs_research: false
    risk: LOW
    pitfalls: ["P2-hash-nondeterminism", "P3-format-drift", "P7-contamination"]
  - name: "Live pilot and calibration"
    goal: "Empirical trigger threshold, env-var floor, cost/session, latency variance on pinned CLI; BLOCKED on Agent SDK credit opt-in (user action)"
    methods: ["Agent SDK / claude -p session driving with env-var forced compaction", "Transcript JSONL boundary parsing (three-signal detection, poll primary)"]
    depends_on: ["Free-corpus harness construction"]
    needs_research: false
    risk: MEDIUM
    pitfalls: ["P1-fp-short-tasks", "P4-overhead-confounds", "P6-rate-limits"]
  - name: "Pre-registration gate"
    goal: "Committed protocol: task subset, n, CP sidedness, exclusions, claim table, observational-vs-controlled reframing"
    methods: ["Session-level Clopper-Pearson zero-event bounds + cluster bootstrap"]
    depends_on: ["Live pilot and calibration"]
    needs_research: false
    risk: LOW
    pitfalls: ["P5-small-n", "M1-curve-conflation", "M2-prior-protocol"]
  - name: "Live compaction campaign (RQ3b + RQ2b)"
    goal: "SPF and reachability on real Claude Code compaction summaries plus live violation CP bound, n=30 (escalation 59)"
    methods: ["Agent SDK / claude -p session driving with env-var forced compaction", "Three-layer SPF stack (token overlap + MiniLM cosine + MiniCheck NLI)", "Session-level Clopper-Pearson zero-event bounds + cluster bootstrap", "Hermetic workspace + canary contamination audit"]
    depends_on: ["Pre-registration gate"]
    needs_research: false
    risk: HIGH
    pitfalls: ["P1-fp-short-tasks", "P5-small-n", "P6-rate-limits", "P7-contamination", "M3-model-drift"]
  - name: "RQ5 overhead campaign"
    goal: "Instrumentation overhead measured token-primary with 95% CI upper bound vs <20% target"
    methods: ["Token-primary paired interleaved overhead design", "Agent SDK / claude -p session driving with env-var forced compaction"]
    depends_on: ["Pre-registration gate"]
    needs_research: false
    risk: MEDIUM
    pitfalls: ["P4-overhead-confounds", "P6-rate-limits", "M4-token-accounting"]
  - name: "Synthesis and verdict regeneration"
    goal: "rq-verdicts.json regenerated with mock qualifiers removed where live evidence lands; hierarchical claim reports"
    methods: ["Session-level Clopper-Pearson zero-event bounds + cluster bootstrap"]
    depends_on: ["Live compaction campaign (RQ3b + RQ2b)", "RQ5 overhead campaign"]
    needs_research: false
    risk: LOW
    pitfalls: ["P5-small-n", "publication-precision-language"]

critical_benchmarks:
  - quantity: "MockLM ceiling (provenance reachability / violations / compression)"
    value: "100% / 6 of 6 / ~1.096x"
    source: "ref-mock-experiment (tools/experiment_results.json)"
    confidence: HIGH
  - quantity: "Mock campaign zero-violation bound (0/211)"
    value: "1.73% two-sided = 1.41% one-sided (95% CP upper)"
    source: "docs/violation-campaign-report.md; recomputed this session"
    confidence: HIGH
  - quantity: "Single-pass summarization fact loss (external anchor, authors' own pipeline)"
    value: "~60% (54% constraint erosion under cascading)"
    source: "Zahn & Chana, arXiv:2603.17781 (verified)"
    confidence: HIGH
  - quantity: "Simulated deletion reachability curve (harness anchor ONLY, not live prediction)"
    value: "0.93 at 10% deletion to 0.25 at 90%"
    source: "docs/compaction-report.md (v1.0)"
    confidence: HIGH
  - quantity: "Observed genuine compaction event (local)"
    value: "preTokens 970893 -> postTokens 13915, durationMs 125246"
    source: "~/.claude/projects transcript, CC 2.1.128"
    confidence: HIGH
  - quantity: "Zero-compaction control expectation"
    value: "SPF ~ 1 for sub-trigger sessions (in-context ceiling 100% to 7,000 facts)"
    source: "Zahn & Chana, arXiv:2603.17781"
    confidence: HIGH

open_questions:
  - question: "Agent SDK credit opt-in completed on this account?"
    priority: HIGH
    blocks_phase: "Live pilot and calibration"
  - question: "Empirical tokens-to-trigger and AUTO_COMPACT_WINDOW floor on pinned CLI version?"
    priority: HIGH
    blocks_phase: "Live compaction campaign (RQ3b + RQ2b)"
  - question: "Does the 0/321 mock zero-violation finding transfer to live sessions?"
    priority: HIGH
    blocks_phase: "none"
  - question: "CP sidedness pre-registration choice (one-sided recommended)"
    priority: HIGH
    blocks_phase: "Live compaction campaign (RQ3b + RQ2b)"
  - question: "Wall-clock sigma_d resolvable for 20% threshold, or token-primary alone?"
    priority: MEDIUM
    blocks_phase: "RQ5 overhead campaign"
  - question: "/compact [instructions] inside -p mode?"
    priority: MEDIUM
    blocks_phase: "none"
  - question: "refusal trigger semantics + calibration corpus count reconciliation (10 auto/manual vs +10 refusal records)"
    priority: MEDIUM
    blocks_phase: "none"

contradictions_unresolved:
  - claim_a: "Auto-compact default trigger ~95% of capacity"
    claim_b: "Auto-compact default trigger ~83% (community) / ~89% formula (Vaughan)"
    source_a: "code.claude.com/docs/en/env-vars (official, fetched 2026-06-12); on-disk 1M event at 97%"
    source_b: "claudefa.st / TurboAI / GitHub #31806 (community); codex.danielvaughan.com"
    investigation_needed: "Phase 1 pilot: measure tokens-to-trigger empirically on the pinned CLI version and window size; plan with the official figure, hard-code none"
```

---

_Research synthesis completed: 2026-06-12_
_Ready for research plan: yes (Phase 1 carries an external prerequisite — Agent SDK credit opt-in)_
