# Computational Approaches: Driving Real Claude Code Sessions Programmatically (Subscription-Only)

**Surveyed:** 2026-06-12
**Domain:** Agent reliability / live LLM validation infrastructure (Primordial v3.0 "Live Validation")
**Confidence:** HIGH (CLI surface, transcript schema, hook events, SDK auth, credit model — all verified against installed CLI v2.1.170, on-disk transcripts, and official docs fetched 2026-06-12). MEDIUM/LOW items flagged inline.

### Scope Boundary

This file covers the computational substrate only: how to invoke, observe, and budget real Claude Code sessions on a subscription with **no paid API key**. Experimental design (which RQs, which metrics) lives in METHODS.md; prior results in PRIOR-WORK.md.

---

## Recommended Stack

Use the **Python Agent SDK (`claude-agent-sdk`)** as the primary session driver, with **raw `claude -p --output-format stream-json` subprocess** as the fallback/cross-check path. Both authenticate through the locally installed Claude Code CLI's existing subscription login (verified: the SDK spawns the CLI as a subprocess and inherits its OAuth credentials; no `ANTHROPIC_API_KEY` required — https://code.claude.com/docs/en/agent-sdk/python). Detect compaction with a **three-signal belt-and-suspenders scheme**: (1) `PreCompact`/`PostCompact` hooks, (2) transcript JSONL polling for `{"type":"system","subtype":"compact_boundary"}` records, (3) `--include-hook-events` in the stream. Force compaction cheaply with the **official env vars `CLAUDE_CODE_AUTO_COMPACT_WINDOW` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`** (verified at https://code.claude.com/docs/en/env-vars), which let auto-compaction fire at ~30–60K tokens instead of ~190K/~950K — this is the single highest-leverage finding for campaign cost.

**The old path is dead for this project:** `genuine_compaction_runner.py`'s `_run_live()` uses the Messages API `compact_20260112` beta. That API still exists and still supports `pause_after_compaction` (verified at https://platform.claude.com/docs/en/build-with-claude/compaction, beta header `compact-2026-01-12`), but it requires an `x-api-key` — and the CLI's `--betas` flag is explicitly "(API key users only)" (verified in `claude --help`, v2.1.170). Under the no-paid-API constraint, v3.0 must instrument **Claude Code's own auto-compaction** instead. There is no `pause_after_compaction` equivalent in Claude Code; the `PreCompact` hook + transcript snapshots replace it (and `PreCompact` *can* block compaction via exit 2, though we should not — see Anti-Approaches).

## Verified Invocation Surface (claude CLI v2.1.170, checked locally 2026-06-12)

All flags below verified verbatim from `claude --help` on the installed binary:

| Flag | Role in v3.0 runner |
|------|---------------------|
| `-p, --print` | Non-interactive mode; transcript persistence is ON by default (a `--no-session-persistence` flag exists to disable it — we must NOT use it) |
| `--output-format stream-json` | NDJSON event stream: `system/init`, `assistant`, `user`, `result`, `system/api_retry`, plus `stream_event` with `--include-partial-messages` |
| `--include-hook-events` | "Include all hook lifecycle events in the output stream (only works with --output-format=stream-json)" — surfaces PreCompact/PostCompact in-stream |
| `--session-id <uuid>` | Pin the session UUID so the transcript path is known *a priori* |
| `-r, --resume <id>` / `--fork-session` / `-c, --continue` | Post-compaction probing: resume the session after a detected compaction and test artifact-ref recovery |
| `--model <alias>` | Pin `sonnet` for campaign cost control |
| `--allowedTools`, `--permission-mode`, `--dangerously-skip-permissions` | Unattended tool approval (existing `live_agent_experiment.py` already uses `--dangerously-skip-permissions`) |
| `--settings <file-or-json>` | Inject campaign-only hook config without touching `~/.claude/settings.json` |
| `--max-budget-usd <amount>` | Per-session spend guard (print mode only) |
| `--json-schema <schema>` | Structured final output for task-success grading |
| `--betas <betas...>` | **"(API key users only)"** — confirms API-beta compaction is out of reach on subscription |
| `--bare` | **DO NOT USE**: "Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper... OAuth and keychain are never read" — bare mode breaks subscription auth (also verified at https://code.claude.com/docs/en/headless) |

`claude -p "Start" --output-format json | jq -r '.session_id'` then `claude -p "..." --resume "$session_id"` is the documented multi-session pattern; session lookup is scoped to the invoking directory (https://code.claude.com/docs/en/headless).

## Verified Compaction Behavior (mid-2026)

### Trigger

- **Auto-compaction triggers at ~95% of context capacity by default** (official: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` docs state "By default, auto-compaction triggers at approximately 95% capacity", https://code.claude.com/docs/en/env-vars). Third-party sources claim ~83.5%/33K-token buffer ([claude-code-examples](https://claude-code-examples.vercel.app/claude-code-context-compaction/), [claudefa.st](https://claudefa.st/blog/guide/mechanics/context-buffer-management)) — treat the official 95% figure as authoritative and calibrate empirically in Phase 0.
- **On-disk evidence (this machine):** a 1M-context session compacted at `preTokens: 970893 → postTokens: 13915` (97% of 1M), `durationMs: 125246`. Consistent with a ~95% threshold checked between turns.
- **Manual trigger:** `/compact [instructions]` in interactive mode. Whether `/compact` expands inside a `-p` prompt is **UNVERIFIED** — docs say custom/user-invoked commands expand in `-p` mode but interactive-dialog builtins do not; `/compact` is neither category explicitly. **Flag: needs a single runtime test.**
- **Observed trigger values in `compactMetadata.trigger` across local transcripts:** `"auto"` (8), `"manual"` (2), and `"refusal"` (10). The `refusal` trigger is undocumented — a compaction-and-retry path after API refusals. Treat as a third event class the detector must not choke on.
- **Microcompaction** (large tool results offloaded to disk, path-reference left in context) is reported by multiple third-party sources ([Decode Claude](https://decodeclaude.com/compaction-deep-dive/), [codex.danielvaughan.com](https://codex.danielvaughan.com/2026/04/14/context-compaction-deep-dive-codex-cli-claude-code-opencode/)) but does not appear in the official env-vars or hooks pages I fetched, and no `microcompact` marker exists in any local transcript. **Confidence: MEDIUM.** Design implication regardless: token pressure delivered via giant tool outputs may be silently deflated; deliver pressure via assistant-generated text and user-message content instead.

### Compaction summary format (verified on disk)

The post-compaction summary is a **plain-text user message** beginning "This session is being continued from a previous conversation that ran out of context..." followed by a **nine-section numbered structure** (extracted verbatim from a local transcript, CLI 2.1.128; ~13K chars in the observed case):

1. Primary Request and Intent · 2. Key Technical Concepts · 3. Files and Code Sections · 4. Errors and fixes · 5. Problem Solving · 6. All user messages · 7. Pending Tasks · 8. Current Work · 9. Optional Next Step

This is plain text — `summary_parser.extract_artifact_ids()` / `parse_summary_provenance()` apply **unchanged** (the `artifact:<run>:stage:<seat>:r<N>` regex is format-agnostic).

### Transcript location and schema (verified on disk)

- **Path:** `~/.claude/projects/<munged-cwd>/<session-id>.jsonl`, where `<munged-cwd>` is the absolute cwd with `/` (and most non-alphanumerics) replaced by `-` (e.g. `/Users/darkfire/forge/primordial` → `-Users-darkfire-forge-primordial`). With `--session-id <uuid>` the full path is known before launch.
- **Record types observed:** `user`, `assistant`, `system`, `attachment`, `queue-operation`, `custom-title`, `last-prompt`, `mode`. Common fields: `uuid`, `parentUuid`, `sessionId`, `timestamp`, `cwd`, `gitBranch`, `version`, `slug`, `type`, `userType`, `isSidechain`.
- **Compaction boundary record (exact, from disk):**

```json
{"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted",
 "logicalParentUuid": "<uuid of last pre-compaction record>",
 "compactMetadata": {"trigger": "auto", "preTokens": 970893, "postTokens": 13915,
                     "preCompactDiscoveredTools": ["..."], "durationMs": 125246}, ...}
```

- **Immediately followed by** a `{"type":"user", "isCompactSummary": true, "isVisibleInTranscriptOnly": ..., "message": {"role":"user","content":"<nine-section summary>"}}` record whose `parentUuid` points at the boundary record. Everything *before* `logicalParentUuid` is the pre-compaction conversation — the pre-state snapshot is free.

### Hook surface (verified at https://code.claude.com/docs/en/hooks, fetched 2026-06-12)

| Hook | Fires | Matchers | Can block? |
|------|-------|----------|-----------|
| `PreCompact` | Before context compaction | `manual` / `auto` | **Yes** (exit 2 / `{"decision":"block"}`) |
| `PostCompact` | After context compaction completes | `manual` / `auto` | No |
| `SessionStart` | Session begin/resume | incl. `compact` ("Auto or manual compaction") | — |
| `SessionEnd` | Session terminates | reasons: `clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` | — |

All hooks receive `session_id`, `transcript_path`, `cwd`, `hook_event_name` on stdin; `PreCompact` additionally receives `trigger`. Whether `PreCompact` also receives a `custom_instructions` field (the `/compact` argument) could not be confirmed — the docs page was truncated at that section across two fetches. **Flag: verify at runtime by dumping hook stdin.** The full 30-event hook list was extracted; `PostCompact` is confirmed to exist (not an extraction artifact — it appears in lifecycle, matcher, and decision-control tables).

## Core Algorithms

| Algorithm | Problem | Mechanism | Cost per session | Key Reference |
|-----------|---------|-----------|------------------|---------------|
| Threshold-lowered forced compaction | Force a genuine auto-compaction in a bounded task | `CLAUDE_CODE_AUTO_COMPACT_WINDOW=50000` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60` → trigger ≈30K tokens | ~$0.5–2 API-rate-equivalent (see Resource Estimates) | code.claude.com/docs/en/env-vars |
| Three-signal compaction detection | Reliably snapshot pre/post states | PostCompact hook (primary) + transcript poll for `compact_boundary` (authoritative) + `--include-hook-events` stream (live) | negligible | code.claude.com/docs/en/hooks |
| Transcript-replay boundary capture | Feed existing SPF pipeline | Parse JSONL up to `logicalParentUuid` = pre-state; `isCompactSummary` content = summary; reuse `capture_boundary()` | offline, free | on-disk schema (verified) |
| Post-compaction recovery probe | RQ2b live violations / recoverability | `--resume <session-id>` (optionally `--fork-session` for N independent probes from one compaction) and ask the model to resolve artifact refs | 1 cheap turn per probe | code.claude.com/docs/en/headless |
| Budget-guarded campaign loop | 50–200 sessions without credit blowout | Read `total_cost_usd` from each `result` message; stop campaign at configurable credit fraction; `--max-budget-usd` per session | — | code.claude.com/docs/en/headless |

### Forcing compaction (question d) — the decision

**Use the env-var threshold override, not organic 190K-token buildup.**

- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1–100): percentage of capacity at which auto-compact triggers; only *lowering* works ("Values above the default threshold have no effect"); applies to main conversations **and subagents**.
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (tokens): capacity used for the compaction calculation, default = model window (200K standard / 1M extended), capped at the real window. Example from docs: treat a 1M model as 500K.
- Combined example: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=50000` + `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60` ⇒ trigger ≈ 30K tokens. The session still needs ~30K of *genuine* conversation (system prompt + CLAUDE.md baseline is ~15–25K in this repo's cwd; running from a clean scratch cwd lowers baseline and gives the experiment more controlled pressure).
- **No documented floor** on `AUTO_COMPACT_WINDOW` (unlike the API's 50K-token minimum trigger). **Flag: empirically find the practical floor in Phase 0** — if compaction fires before the adversarial task plants its artifact markers, the trial is void.
- Token-pressure content should come from the model's own outputs and injected user content (the 20-task `adversarial_corpus.py` already generates marker-dense work); avoid relying on huge Bash/Read tool outputs for pressure (possible microcompaction deflation, MEDIUM confidence).
- Provenance-aware compaction instructions (the old `instructions` param of `compact_20260112`): Claude Code's auto-compact path exposes **no instruction parameter**. The treatment arm must deliver provenance-preservation instructions via system prompt / CLAUDE.md / `--append-system-prompt` instead — a real experimental-design change vs. the API design, since instructions now compete with task context rather than being injected at summarization time. (`/compact <instructions>` would be a closer analog if it works in `-p` mode — see open questions.)

### Detecting compaction (question c) — the decision

Primary detector: **transcript poll** (authoritative, schema verified on this machine). A watcher tails `~/.claude/projects/<munged-cwd>/<session-uuid>.jsonl` for `type=system, subtype=compact_boundary`; `compactMetadata` gives `trigger`, `preTokens`, `postTokens`, `durationMs` for free (these feed `compression_ratio` directly, replacing the word-count estimate in `_compute_aggregate_metrics()`). Pre-state = all records up to `logicalParentUuid`; post-state = the `isCompactSummary` record + everything after.

Secondary, for live reaction (e.g., pausing the prompt feed to take a stable snapshot): a `PostCompact` command hook registered via `--settings '{"hooks": {"PostCompact": [...]}}'` (campaign-scoped, doesn't pollute user settings), writing a sentinel file the runner watches; or, in the SDK, `hooks={...}` + `include_hook_events=True` surfacing `HookEventMessage` objects in-process. `SessionStart` with `source: "compact"` is a third confirmation signal on resume.

Do **not** rely on a `compact_boundary` event appearing in the `stream-json` stdout stream — only `init`, `api_retry`, and `plugin_install` system subtypes are documented there. **Flag: check empirically; if present, it's a bonus fourth signal.**

## Software Ecosystem

### Primary Tools

| Tool | Version | Purpose | License | Maturity |
|------|---------|---------|---------|----------|
| Claude Code CLI | 2.1.170 installed (transcripts on disk from ≥2.1.128 show stable compaction schema) | Session substrate, auth, compaction engine | proprietary, subscription | stable, fast-moving (re-verify flags per minor version) |
| `claude-agent-sdk` (Python) | latest PyPI at phase start | Primary driver: typed messages, programmatic hooks, session mgmt (`list_sessions`, `get_session_messages`, `fork_session`), `RateLimitEvent` | MIT (per PyPI) — verify on install | stable |
| Python | 3.11+ (project standard) | runner, analysis | PSF | stable |

### Supporting Tools

| Tool | Version | Purpose | When Needed |
|------|---------|---------|-------------|
| `jq` | any | ad-hoc stream-json debugging | development only |
| existing repo tools (see Integration) | n/a | chamber, SPF, parsing, corpus | always |

**SDK vs raw subprocess — recommendation: SDK primary.** Rationale: (1) in-process `PreCompact`/`PostCompact` hook callbacks remove the sentinel-file dance; (2) `get_session_messages()`/`list_sessions()` formalize transcript access the subprocess path does by raw JSONL parsing; (3) `ResultMessage.total_cost_usd` + `RateLimitEvent` give budget/limit telemetry the campaign loop needs; (4) `fork_session=True` enables N independent post-compaction probes from one paid compaction. Keep the subprocess path (a ~40-line extension of `live_agent_experiment.run_agent()`) as a cross-check that SDK-mediated observation doesn't perturb results, and as a hedge against SDK/CLI version skew. Both paths read the same transcript files, so the analysis pipeline is identical.

## Data Flow

```
adversarial_corpus.py task (marker-dense, 20 tasks)
  -> session launcher (SDK ClaudeSDKClient | claude -p --session-id <uuid> --output-format stream-json)
       env: CLAUDE_CODE_AUTO_COMPACT_WINDOW, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
       settings: campaign-scoped PostCompact/PreCompact hooks via --settings JSON
  -> live session runs; runner feeds iteration prompts; forge chamber registers artifacts in parallel
  -> compaction fires (auto, ~30K tokens)
       PreCompact hook: snapshot trigger + transcript offset (observe only)
       PostCompact hook / transcript poll: detect compact_boundary record
  -> boundary extractor: parse JSONL
       pre-state  = records up to logicalParentUuid  (artifact IDs planted so far)
       summary    = isCompactSummary message content (nine-section text)
       metadata   = compactMetadata {trigger, preTokens, postTokens, durationMs}
  -> EXISTING pipeline unchanged:
       summary_parser.parse_summary_provenance() -> surviving/lost IDs, ref graph
       classify_ref_tier() + EmbeddingSimilarity -> resolved/degraded/broken
       SPFMetric.measure_batch() -> SPF scores
       GenuineCompactionRunner.capture_boundary() -> BoundaryCapture -> TrialResult
  -> optional recovery probe: claude -p --resume <uuid> [--fork-session] "resolve artifact:X..."
  -> log_results() -> data/compaction/genuine/*.jsonl -> findings_ledger
```

## Computation Order and Dependencies

| Step | Depends On | Produces | Can Parallelize? |
|------|-----------|----------|-----------------|
| 0. Calibration (5 sessions): verify threshold env vars fire, measure $/session, dump hook stdin, test `/compact` in `-p` | Agent SDK credit opt-in (user action) | empirical trigger floor, cost-per-session, hook field inventory | no (sequential learning) |
| 1. Transcript boundary extractor + tests | step 0 schema confirmation | `transcript_codec` module | yes (pure offline) |
| 2. Claude-code backend for `campaign_runner.py` | steps 0–1 | live backend returning the existing `backend_result` dict shape | — |
| 3. Pilot (10–20 sessions, one corpus task class) | step 2 | variance estimate → power analysis sizing | 2–4 concurrent sessions max |
| 4. Full campaign (50–200 sessions) | step 3 | RQ3b/RQ2b/RQ5 live verdicts | 2–4 concurrent, budget-gated |
| 5. Recovery probes via `--resume`/`--fork-session` | step 4 detections | RQ2b recoverability data | yes, cheap |

## Resource Estimates

**Budget model (verified 2026-06-12, effective 2026-06-15):** Agent SDK + `claude -p` usage on subscription draws from a **monthly Agent SDK credit**: **$200/month on Max 20x** (Pro $20, Max 5x $100); per-user, refreshes monthly, no rollover, **one-time opt-in required**, drains before other sources. When depleted, "Agent SDK requests **stop** until your credit refreshes" unless pay-per-token usage credits are enabled — which this project's no-paid-API rule forbids, so **$200/month is a hard monthly campaign ceiling**. Interactive Claude Code limits (5-hour window + weekly caps) are separate and unaffected. Sources: https://code.claude.com/docs/en/headless (note banner), https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan. Before June 15, `claude -p` shared the interactive 5h/weekly limits (Max 20x ≈ 900 messages/5h per third-party measurement — [TrueFoundry](https://www.truefoundry.com/blog/claude-code-limits-explained), unofficial).

| Computation | Cost (API-rate-equivalent vs $200/mo credit) | Wall time | Assumptions |
|-------------|-----------------------------------------------|-----------|-------------|
| 1 forced-compaction session (threshold ≈30K, Sonnet, 10–25 turns) | ~$0.50–2.00 | 5–15 min | Sonnet pricing $3/$15 per Mtok, cache reads $0.30/Mtok (background knowledge, MEDIUM — recalibrate from measured `total_cost_usd` in step 0) |
| 1 organic compaction session (~190K context, 200K window) | ~$5–15 | 30–90 min | why we don't do this: ≤40 sessions/mo would fit |
| Compaction event itself | included | ~10–125 s (observed `durationMs`: 125 s at 970K→14K; smaller contexts faster) | scales with preTokens |
| Recovery probe (resume + 1 turn) | ~$0.05–0.20 | <1 min | summary-sized context |
| 50-session campaign (forced, Sonnet) | ~$25–100 → fits in one monthly credit | ~8–15 h at 2–4 concurrent | |
| 200-session campaign | ~$100–400 → **may span 2 monthly credits**; plan 100/mo or tighten thresholds | ~30–50 h spread across days | budget gate in runner mandatory |
| Opus instead of Sonnet | ~5× cost | — | avoid for campaign bulk |

Storage: transcripts ~1–10 MB/session → ≤2 GB total; trivial. Memory/CPU: negligible (I/O-bound orchestration).

## Integration with Existing Code

**Input formats:** `adversarial_corpus.py` task templates with `generate_iteration(n)` (unchanged). **Output formats:** `TrialResult.to_dict()` JSONL in `data/compaction/genuine/` (unchanged) — downstream `findings_ledger`, `power_analysis`, report generators keep working.

### `tools/genuine_compaction_runner.py` — replace vs reuse

| Component | Verdict | Notes |
|-----------|---------|-------|
| `_run_live()` (l.407) | **REPLACE** | Messages API + `compact_20260112`; API-key-gated. New `_run_claude_code()` drives a live session and harvests the transcript |
| `_api_call_with_retry()` (l.504) | **REPLACE** | `context_management`/`extra_headers` are API-only. Stream-json already emits `system/api_retry` events; SDK retries internally |
| `RunnerConfig` (l.55) | **ADAPT** | `threshold` → `auto_compact_window` + `autocompact_pct` env values; `pause_after_compaction` → drop; `provenance_aware_instructions` → system-prompt injection (semantics change — document in METHODS) |
| `capture_boundary()` (l.200) | **REUSE** | Feed it `compaction_block={"type":"compaction","text":<isCompactSummary content>}` built from the transcript record |
| `CompactionSnapshot`, `BoundaryCapture`, `TrialResult`, `log_results()` | REUSE unchanged | |
| `_register_artifact()`, `_build_ref_graph()`, `_compute_chamber_hash()`, `_compute_aggregate_metrics()`, `_compute_live_aggregate_metrics()` | REUSE | Improvement: override `compression_ratio` with exact `preTokens/postTokens` from `compactMetadata` |
| `_run_dry()` | REUSE | Extend the synthetic summary generator to mimic the verified nine-section format so dry-run validates the new parser path |
| `is_dry_run` check (l.193: `not os.environ.get("ANTHROPIC_API_KEY")`) | **REPLACE** | Wrong gate for subscription mode — probe `claude --version` / SDK availability instead |

### Other integration points

- `tools/campaign_runner.py` l.330–345: implement the `claude-code` backend stub (currently `raise NotImplementedError`); must return the existing dict shape `{chamber, transcript, tool_call_log, compaction_events, token_count, task_completed, task_success, errors}` consumed at l.403–413. `tool_call_log` comes from stream-json `assistant` messages' tool_use blocks or transcript records.
- `tools/live_agent_experiment.py` `run_agent()` (l.87): the proven subprocess pattern (`claude --print --dangerously-skip-permissions -p ...`). Extend with `--session-id`, `--output-format stream-json`, env-var injection, and per-session `--settings` hooks; its typed-absence handling (timeout → `not_generated`, nonzero exit → `invalid`) carries over as-is.
- `tools/summary_parser.py`, `tools/embedding_similarity.py`, `tools/semantic_provenance_fidelity.py`: **zero changes** — they operate on plain text, and the compact summary is plain text.
- New module (one file, ~150 lines): `tools/claude_code_transcript.py` — locate transcript from (cwd, session_id), parse records, extract boundary triples (pre-records, `compactMetadata`, summary text), handle the `refusal` trigger class.

## Validation Strategy

| Result | Validation Method | Benchmark | Source |
|--------|------------------|-----------|--------|
| Forced compaction fires at configured threshold | Phase-0 run with `AUTO_COMPACT_WINDOW=50000`; check `compactMetadata.preTokens` ≈ window×pct | within ~±20% of target (turn-boundary overshoot expected) | env-vars docs + on-disk overshoot evidence |
| Detector correctness | Replay the 4 historical compaction transcripts already on this machine through the extractor | 100% boundary recall, exact preTokens/postTokens echo | local transcripts (free regression corpus) |
| Hook fires & fields | PreCompact/PostCompact hook dumping stdin JSON to file during calibration | fields ⊇ {session_id, transcript_path, cwd, hook_event_name, trigger} | hooks docs |
| Cost model | `total_cost_usd` from `result` message vs estimate | within 2× of $0.5–2/session band, else re-size campaign | headless docs (`total_cost_usd` field) |
| Subscription auth (no API key) | Run with `ANTHROPIC_API_KEY` unset; session must succeed | success | SDK docs auth model |
| Pipeline equivalence | Same trial through SDK path and subprocess path | identical BoundaryCapture (same transcript) | construction |

## Open Questions

| Question | Why Open | Impact | Approach |
|----------|---------|--------|----------|
| Does `/compact [instructions]` work inside a `-p` prompt? | Docs ambiguous (dialog-builtins excluded; /compact is not a dialog) | Would enable instruction-bearing manual compaction = closest analog to the old `instructions` param | Single calibration run; costs one session |
| Practical floor for `CLAUDE_CODE_AUTO_COMPACT_WINDOW`? | No documented minimum (API had 50K) | Determines cheapest possible trial | Bisect in Phase 0 |
| `custom_instructions` field in PreCompact stdin? | Docs page truncated at that section (2 fetch attempts, 2026-06-12) | Minor — observational metadata | Dump hook stdin in Phase 0 |
| Does `compact_boundary` appear in stream-json stdout? | Not in documented system subtypes | Bonus 4th detection signal | Inspect calibration stream |
| Microcompaction interference with tool-result token pressure | Official docs silent; third-party sources only (MEDIUM) | Could stall forced compaction for tool-heavy tasks | A/B one tool-heavy vs text-heavy pressure task |
| `"refusal"` compaction trigger semantics | Undocumented; observed 10× on disk | Detector must classify, analysis must exclude or bin separately | Inspect those transcripts; treat as separate stratum |
| Agent SDK credit opt-in state on Joona's account | "One-time opt-in" per support article; cannot verify from here | **Campaign blocker if not opted in by start** | User action before Phase 0 (flag to roadmap as prerequisite) |

## Anti-Approaches

| Anti-Approach | Why Avoid | What to Do Instead |
|---------------|-----------|-------------------|
| Messages API `compact_20260112` (`_run_live()` as written) | Requires `x-api-key`; `--betas` is API-key-only; violates no-paid-API rule | Claude Code auto-compaction + env-var thresholds |
| `--bare` mode for the runner | OAuth/keychain never read in bare mode → subscription auth breaks | Plain `-p` from a controlled scratch cwd; `--settings` for isolation |
| Blocking compaction via PreCompact exit 2 to "pause" | Session is at ~95% capacity; blocking risks wedging it at the hard limit; perturbs the phenomenon under study | Observe-only hooks; snapshot via transcript |
| Organic 190K-token compaction sessions | $5–15/session → ceiling of ~13–40 sessions/month on the $200 credit | Threshold-lowered forcing (~10× cheaper) |
| Editing `~/.claude/settings.json` for campaign hooks | Pollutes the user's live environment; CLAUDE.md auto-load inflates baseline context unpredictably | Per-invocation `--settings` JSON + dedicated scratch cwd per session |
| `--no-session-persistence` | Destroys the transcript — the primary measurement artifact | Never set it; pin `--session-id` instead |
| Polling token usage by re-prompting "/context" | Burns turns and perturbs context | Read `usage` from stream-json `result` / SDK `ResultMessage.usage` |

## Sources

- `claude --help`, v2.1.170 installed locally — **full CLI flag surface verified 2026-06-12** (print/stream-json/resume/session-id/include-hook-events/betas/bare/no-session-persistence)
- Local transcripts `~/.claude/projects/*/*.jsonl` — **compact_boundary schema, compactMetadata fields, isCompactSummary record, nine-section summary, trigger values {auto, manual, refusal}, record-type inventory verified on disk 2026-06-12**
- https://code.claude.com/docs/en/headless — `-p` patterns, stream-json event schema (`system/init`, `system/api_retry`), resume/session-id workflow, `total_cost_usd`, `--bare` auth caveat, June 15 credit note (fetched 2026-06-12)
- https://code.claude.com/docs/en/hooks — 30-event hook list, PreCompact (blockable, matchers manual/auto), PostCompact, SessionStart `compact` source, SessionEnd reasons (fetched 2026-06-12; PreCompact input-example section truncated — flagged)
- https://code.claude.com/docs/en/agent-sdk/python — `claude-agent-sdk` package, `query()`/`ClaudeSDKClient`, `ClaudeAgentOptions` (resume/fork_session/hooks/max_budget_usd/include_hook_events), session-management functions, message types incl. `ResultMessage`/`RateLimitEvent`, subscription auth via CLI (fetched 2026-06-12)
- https://code.claude.com/docs/en/env-vars — `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (default ≈95%), `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (fetched 2026-06-12)
- https://platform.claude.com/docs/en/build-with-claude/compaction — `compact_20260112` still beta, header `compact-2026-01-12`, `pause_after_compaction`, 50K min trigger, API-key auth (fetched 2026-06-12)
- https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan — **Agent SDK monthly credit: Pro $20 / Max 5x $100 / Max 20x $200; per-user, no rollover, opt-in, hard stop when depleted without usage credits** (fetched 2026-06-12)
- Third-party (MEDIUM confidence, flagged where used): [Decode Claude compaction deep-dive](https://decodeclaude.com/compaction-deep-dive/), [codex.danielvaughan.com compaction comparison](https://codex.danielvaughan.com/2026/04/14/context-compaction-deep-dive-codex-cli-claude-code-opencode/), [claude-code-examples auto-compact guide](https://claude-code-examples.vercel.app/claude-code-context-compaction/), [claudefa.st context buffer](https://claudefa.st/blog/guide/mechanics/context-buffer-management), [TrueFoundry limits guide](https://www.truefoundry.com/blog/claude-code-limits-explained)
- Existing repo artifacts inspected: `tools/genuine_compaction_runner.py`, `tools/live_agent_experiment.py`, `tools/campaign_runner.py` (l.330–345 backend stub, l.403–413 result contract), `tools/summary_parser.py`
