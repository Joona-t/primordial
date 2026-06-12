# Methods Research: Primordial v3.0 "Live Validation"

**Project:** Primordial Computing — typed absence + provenance + recoverable compaction
**Domain:** LLM agent reliability measurement (semantic fidelity metrics, zero-event statistics, instrumentation overhead, transcript forensics)
**Researched:** 2026-06-12
**Mode:** Literature survey (subsequent-milestone, methods-only)
**Confidence:** HIGH overall (section d grounded in direct inspection of local data; sections a-c grounded in verified literature + exact arithmetic)

### Scope Boundary

This file covers ONLY methods needed for the NEW v3.0 work: live measurement on real
Claude Code session transcripts and compaction summaries. Existing v1.0-v2.0 methods are
taken as given and NOT re-derived: SPF_jaccard / SPF_weighted / SPF_embedding,
Clopper-Pearson + Bayesian zero-violation bounds, bootstrap CIs for differential
detection, three-tier baseline design, BFS structural reachability with
resolved/degraded/broken classification.

**Hard constraint honored throughout:** no paid LLM API. All model inference is local
(sentence-transformers / HF models on Apple Silicon) or routed through the user's
existing `claude` CLI subscription via subprocess.

**Measured local environment (2026-06-12):** Apple M1 Pro, 16 GB RAM, Python 3.14.5,
scipy 1.17.1 present, torch and sentence-transformers ABSENT. This constrains model
size (≤1B params comfortable) and flags a possible Python-3.14 wheel-availability issue
for torch (see Installation).

---

## Recommended Methods (summary)

| # | Question | Recommended Method | Cost (local) | Confidence |
|---|----------|--------------------|--------------|------------|
| a1 | SPF embedding backend | sentence-transformers `all-MiniLM-L6-v2` (primary), `bge-small-en-v1.5` (quality fallback) | ~80-130 MB model, <1 s/pair on M1 CPU | HIGH |
| a2 | Factual-consistency layer (NEW) | MiniCheck-Flan-T5-Large (770 M) entailment scoring, original→summary-claim direction | ~3 GB RAM fp32, ~1-5 s/claim on M1 | HIGH (method) / MEDIUM (M1 latency) |
| b1 | Live zero-event bound | Clopper-Pearson exact at pre-registered fixed n; **n = 30 sessions primary target** (UB 9.5%), escalation tier n = 59 (UB 4.95%) | n × (session runtime) | HIGH |
| b2 | Unit of analysis | Session-level binary outcome for CP bound; per-ref rates via cluster bootstrap (resample sessions) | negligible | HIGH |
| b3 | Sequential option | Bayesian Beta posterior reported alongside (stopping-rule-insensitive); confidence sequences only if true anytime monitoring needed | negligible | HIGH / MEDIUM |
| c1 | Overhead design | Paired, randomized-order, interleaved A/B; token overhead as primary (deterministic), wall-clock as secondary (log-scale geometric-mean ratio) | ~2× campaign runtime | HIGH |
| c2 | Overhead sample size | Pilot 5 pairs to estimate σ_d; expect ~12-23 pairs for 80% power at 20% threshold | pilot + main | HIGH (arithmetic) / LOW (σ_d guess until pilot) |
| d1 | Compaction detection | Parse `~/.claude/projects/<dir>/<session>.jsonl` for `subtype:"compact_boundary"` + `isCompactSummary:true` entries | trivial | HIGH (verified on disk) |
| d2 | Summary segmentation | Anchor on the fixed 9-section header template (verified across 9 real summaries) | trivial | HIGH (verified on disk) |

---

## (a) Semantic fidelity between originals and LLM compaction summaries — no paid API

### Recommended architecture: three-layer metric stack

Keep the existing layers and add one new layer. Each layer answers a different question;
no single metric is sufficient (see Known Failure Modes).

```
Layer 0 (existing, keep): token overlap — SPF_jaccard, SPF_weighted
    answers: "are the original tokens literally present?"
Layer 1 (existing module, NEW backend): embedding cosine — SPF_embedding
    answers: "is the recovered text about the same thing?"
Layer 2 (NEW for v3.0): NLI factual consistency — SPF_entailment
    answers: "are the claims in the summary actually supported by the original?"
```

### Layer 1: Embedding backend selection

**Recommendation: `sentence-transformers/all-MiniLM-L6-v2` as the default backend.**

Rationale specific to this project:

1. **Symmetric similarity is the right objective.** SPF compares original artifact
   content against recovered summary excerpts — a symmetric semantic-textual-similarity
   task, not asymmetric query→document retrieval. MiniLM-L6-v2 is trained on
   paraphrase/similarity pairs and needs **no instruction prefixes**. Retrieval-tuned
   models (E5 family, BGE with query instruction, nomic-embed with task prefixes)
   require correct prefix discipline ("query: ", "passage: ",
   "search_document: ") and silently degrade when prefixes are wrong — a real
   integration pitfall for a metric module.
2. **Size fits the machine.** ~22.7 M params, 384-dim output, ~80 MB download. Runs
   comfortably on M1 Pro CPU; no GPU required. [CONFIDENCE: HIGH — standard model-card
   facts]
3. **Drop-in for the existing module.** `embedding_similarity.py` already defines the
   sentence-transformers primary backend with token-overlap fallback; only the model
   name needs pinning.

**Quality fallback / upgrade path: `BAAI/bge-small-en-v1.5`** (33 M params, 384-dim).
Slightly stronger on English MTEB tasks; for symmetric similarity use NO instruction
prefix (the BGE query instruction is for short-query retrieval only). If artifact
contents exceed ~256 word-piece tokens (MiniLM's effective max length), either
chunk-and-mean-pool, or switch to `nomic-ai/nomic-embed-text-v1.5` (137 M params,
8192-token context, requires task prefixes). [CONFIDENCE: MEDIUM-HIGH — model families
verified current in 2026 surveys (Milvus 2026 RAG embedding comparison, KnowledgeSDK
MTEB guide); exact MTEB rank deltas are blog-tier, treat as indicative not exact]

**Apple Silicon execution notes** (verified via 2025-2026 community/benchmark sources):

- sentence-transformers auto-detects device (CUDA → MPS → CPU). For small batches
  (the SPF case: pairs of short texts), **CPU is often faster than MPS** because
  CPU↔GPU transfer overhead dominates at small batch sizes; one mining benchmark
  measured MPS ~2× slower wall-clock on small-batch embedding workloads while cutting
  CPU utilization ~12×. Set `device="cpu"` explicitly for the metric path; benchmark
  once and record. [CONFIDENCE: MEDIUM — single-source benchmark, direction consistent
  with PyTorch MPS known behavior]
- If MPS is used: `PYTORCH_ENABLE_MPS_FALLBACK=1` covers unsupported ops.
- **Python 3.14 risk:** system Python is 3.14.5; torch wheels may lag the newest
  CPython. If `pip install torch` fails, create a dedicated 3.11/3.12 venv for the
  metric pipeline. [CONFIDENCE: MEDIUM — wheel availability not verified for current
  torch release; check at install time]

### Layer 2 (NEW): NLI-based factual consistency, run locally

**Recommendation: MiniCheck-Flan-T5-Large** (Tang, Laban & Durrett, EMNLP 2024;
arXiv:2404.10774; github.com/Liyan06/MiniCheck).

- **What it does:** classifies whether a claim sentence is grounded in (entailed by) a
  source document. Built exactly for "is this LLM output supported by the grounding
  text" — which is the provenance-fidelity question stated directionally.
- **Why this one:** the 770 M-param Flan-T5-Large variant reaches GPT-4-level accuracy
  on the LLM-AggreFact benchmark at ~400× lower cost than LLM-judge approaches, and is
  small enough for the M1 Pro (fp32 ≈ 3 GB RAM). It was benchmarked directly against
  the two main alternatives (SummaC, AlignScore) and outperforms systems of comparable
  size. [CONFIDENCE: HIGH — peer-reviewed EMNLP 2024 + verified repo]
- **Direction matters:** score each summary claim against the original artifact
  (original = grounding doc, summary sentence = claim). This detects fabricated or
  flipped facts that cosine similarity misses.
- **Do NOT use Bespoke-MiniCheck-7B** on this machine: 7B fp16 ≈ 14 GB, too tight on
  16 GB RAM alongside the session driver.
- **License caveat:** some MiniCheck variants are trained on GPT-4-generated data with
  commercial-use restrictions noted in the repo; fine for this research use, but record
  the variant + license in the campaign metadata. [CONFIDENCE: MEDIUM — repo README
  caveat, not independently audited]

**Alternatives verified and considered:**

| Method | Reference | Why not primary |
|---|---|---|
| SummaC-Conv | Laban et al., TACL 2022, arXiv:2111.09525 | Solid NLI-pair aggregation method (74.4% balanced acc. on SummaC benchmark) but superseded by MiniCheck on the aggregate LLM-AggreFact benchmark; keep as cross-check if MiniCheck install fails |
| AlignScore | Zha et al., ACL 2023, arXiv:2305.16739 | Unified alignment function trained on 4.7 M examples across 7 tasks; strong, but older toolchain and MiniCheck outperforms at similar size |
| BERTScore | Zhang et al., ICLR 2020, arXiv:1904.09675 | Token-level contextual-embedding F1; adds little over sentence-embedding cosine for this use and does not detect factual flips either |
| ROUGE / BLEU | Lin 2004 / Papineni et al. 2002 | n-gram overlap ≈ Layer 0 already covers this; known weak correlation with factual consistency |
| LLM-as-judge via local `claude -p` | — | No-API-cost path exists, BUT judging Claude's compaction with Claude is circular for the primary metric. Acceptable only as a labeled exploratory annex. |

**Known failure modes of the stack (document in PITFALLS later):**

- **Cosine blindness to negation/number flips:** "tests pass" vs "tests fail" embed
  close together. This is the gap Layer 2 closes. A 2024 critical evaluation found
  automatic factuality metrics themselves have blind spots and can be gamed by
  superficial edits (arXiv:2411.16638) — so report all three layers, never one.
- **Length asymmetry:** compaction summaries are ~13 K chars covering ~1 M tokens of
  history (measured locally); comparing a 200-token artifact against the whole summary
  depresses cosine. Compare artifact against the *retrieved relevant span* (section or
  sentence window), not the whole summary.
- **Threshold provenance:** the 0.9/0.7 resolved/degraded/broken thresholds in
  `embedding_similarity.py` are provisional and calibrated on synthetic pairs. They are
  NOT transferable across embedding models — recalibrate per backend on the genuine
  local summaries (10 events available on this machine, see section d) plus synthetic
  perturbation pairs (entity swap, negation, number change).

**Empirical anchor for expected effect sizes:** Zahn & Chana, "Facts as First Class
Objects: Knowledge Objects for Persistent LLM Memory" (March 2026, arXiv:2603.17781)
report ~60% fact loss from a summarization pass and ~54% project-constraint erosion
under cascading compaction. (This is the citation already embedded in
`embedding_similarity.py`; now independently verified.) Expect many refs in
degraded/broken tiers — the metric stack must discriminate within the low end, another
reason cosine alone is insufficient. [CONFIDENCE: MEDIUM — single recent preprint, but
matches the project's own v2.0 mock observations]

---

## (b) Zero-event inference for a live subset of the 211-run campaign

### The governing arithmetic (exact, computed 2026-06-12 with scipy 1.17.1)

With x = 0 violations in n independent trials, the one-sided 95% Clopper-Pearson upper
bound is:

```
p_U = 1 − 0.05^(1/n)        (exact; "rule of three" 3/n is the first-order approx)
n required for p_U ≤ p_max:   n = ⌈ ln(0.05) / ln(1 − p_max) ⌉  ≈ 3/p_max
```

(Clopper & Pearson, Biometrika 1934; rule of three: Hanley & Lippman-Hand, JAMA 1983,
"If nothing goes wrong, is everything all right?")

| n (sessions, 0 events) | CP 95% UB | rule-of-3 | Bayes UB, uniform prior | Bayes UB, Jeffreys |
|---|---|---|---|---|
| 10  | 25.89% | 30.0% | 23.84% | 17.08% |
| 20  | 13.91% | 15.0% | 13.29% |  9.05% |
| 30  |  9.50% | 10.0% |  9.21% |  6.15% |
| 50  |  5.82% |  6.0% |  5.70% |  3.75% |
| 59  |  4.95% |  5.1% |  —     |  —     |
| 100 |  2.95% |  3.0% |  2.92% |  1.90% |
| 211 |  1.41% |  1.4% |  1.40% |  0.91% |

| Target claim (95%) | n required at 0 events |
|---|---|
| violation rate < 20% | 14 |
| < 15% | 19 |
| < 10% | **29** |
| < 5%  | **59** |
| < 2%  | 149 |
| < 1.41% (match mock campaign) | 211 |
| < 1%  | 299 |

### Recommendation

1. **Primary live target: n = 30 sessions** → certifies violation rate < 9.5% at 95%
   if zero violations. This is the smallest n that supports a "<10%" headline claim.
2. **Pre-registered escalation tier: n = 59** → "<5%" claim, run only if the first 30
   are clean and budget allows.
3. **Do NOT claim mock-campaign-equivalent bounds from a subset.** The 211-run mock
   bound (1.41%) requires 211 live runs. The honest framing: the live subset *validates
   the mock pipeline's transferability* at a coarser bound; the mock campaign retains
   the tight bound, explicitly labeled as mock.
4. **Report the Bayesian Beta posterior alongside** (uniform → Beta(1, n+1); Jeffreys →
   Beta(0.5, n+0.5)), consistent with the existing v2.0 dual-reporting convention.

### Unit-of-analysis correction (critical, easy to get wrong)

Refs within one session share a single compaction event — they are NOT independent
Bernoulli trials. Counting per-ref trials would fabricate sample size (a 30-session
campaign with 40 refs each is not n = 1200). **Method:**

- **CP bound on session-level binary outcome:** session counts as a violation if ANY
  ref in it violates. Conservative, defensible, and matches how the claim will be read
  ("a session survives compaction intact").
- **Per-ref rates reported descriptively** with a **cluster bootstrap** (resample
  sessions with replacement, recompute the per-ref rate; percentile CI). This reuses
  the project's existing bootstrap machinery with the resampling unit changed to the
  session. [CONFIDENCE: HIGH — standard clustered-binary practice]

### Sequential / grouped designs

- **Default: fixed pre-registered n, run in operational batches of 10.** Batches are
  for checkpointing and failure triage only; the confidence bound is computed once at
  the pre-registered n. Stopping early *because* results look clean and then quoting
  the CP bound at the smaller n is optional-stopping bias — the realized coverage is no
  longer 95%.
- **Early stopping on a violation is free:** the design's purpose is the zero-event
  bound; once a violation occurs the zero-event claim is dead regardless, and the
  violation itself becomes the (more interesting) finding. Pre-register this asymmetry.
- **If true anytime-valid monitoring is wanted** (peek at every session, stop whenever):
  use time-uniform confidence sequences (Howard, Ramdas, McAuliffe & Sekhon, Ann.
  Statist. 2021, arXiv:1810.08240). They cost roughly a constant-factor widening of the
  bound. Recommended only if the campaign becomes open-ended; overkill for n = 30.
  The Bayesian posterior is insensitive to stopping rules under the likelihood
  principle and already serves as the informal "peeking-safe" summary.
  [CONFIDENCE: HIGH for the method's existence and validity; MEDIUM that it is worth
  the complexity here — recommendation is to skip it]

---

## (c) Overhead measurement methodology (RQ5: instrumentation overhead < 20%)

### Decompose overhead into deterministic and stochastic components

| Component | Measurement | Noise level |
|---|---|---|
| **Token overhead** (instrumentation prompt text, extra tool definitions, provenance markers) | Exact, from transcript `usage` fields and `compactMetadata.preTokens/postTokens` | Near-deterministic given fixed trajectory |
| **Turn/tool-call overhead** | Exact count from transcript | Low-moderate (behavioral) |
| **Wall-clock overhead** | End-to-end session timer | HIGH — API load, time-of-day, stochastic output length |
| **Compaction latency** | `compactMetadata.durationMs` — directly logged per event (125 s observed in one real local event) | Moderate |

**Make token overhead the primary RQ5 metric and wall-clock secondary.** Two verified
reasons wall-clock is noisy beyond server load: (1) LLM outputs are highly
non-deterministic across identical prompts even at fixed settings (Ouyang, Zhang,
Harman & Wang, TOSEM 2025, arXiv:2308.02828); (2) even "deterministic" settings
(temperature 0) do not produce deterministic outputs in practice (arXiv:2408.04667).
Output-length variance propagates directly into wall-clock variance.

### Design: paired, randomized, interleaved

1. **Paired tasks:** each task instance runs once instrumented (forge) and once
   uninstrumented (or per the existing three-tier baseline), same prompt, same model.
2. **Randomize within-pair order and interleave pairs in time** (A-B, B-A alternating
   blocks) so time-of-day API-load drift cancels in the paired difference. Do NOT run
   all instrumented sessions first.
3. **Pin everything pinnable:** model ID, Claude Code version (schema AND behavior
   change across versions — five versions observed in local transcripts), permission
   mode, working directory state (fresh git checkout per run).
4. **Pre-register exclusion/covariate rules** for retries, rate-limit throttling, and
   network errors (log all; exclude pairs with throttling events, or model as
   covariate — choose before running).
5. **Exclude a warm-up run** per condition.
6. **Co-primary outcome: task success.** Instrumentation that "costs nothing" by
   making the agent fail faster must not score as low overhead. Overhead is only
   interpretable conditional on comparable success rates.
7. **Accept trajectory divergence.** Instrumentation changes token counts → changes
   compaction timing → changes the trajectory. The comparison is between
   *distributions of task completions*, not token-identical traces. This is exactly
   why pairing + randomization is required rather than a single exemplar diff.

### Analysis

- Wall-clock and token totals are right-skewed: **analyze on the log scale**. The
  paired difference of logs gives the **ratio of geometric means** — the natural
  estimand for a relative "<20%" target. Bootstrap CI on that ratio (existing project
  machinery); Wilcoxon signed-rank as the nonparametric confirmation.
- Report median and p90, not just means (standard LLM-serving practice: TTFT/ITL/E2E
  with p50/p95/p99 percentile reporting, per LLMPerf/Anyscale benchmarking
  methodology). For batch agent sessions, end-to-end wall time is the relevant latency
  metric; TTFT/ITL are not.
- **Decision rule:** RQ5 passes if the upper bound of the 95% CI on the
  geometric-mean overhead ratio is < 1.20 (not merely the point estimate).

### Sample size (exact arithmetic, one-sided α = 0.05, power = 0.80, δ = ln 1.20 = 0.182)

n_pairs = ((z_α + z_β) · σ_d / δ)², where σ_d = SD of within-pair log-ratio:

| σ_d (log-ratio) | n pairs |
|---|---|
| 0.15 | 5 |
| 0.25 | 12 |
| 0.35 | 23 |
| 0.50 | 47 |
| 0.70 | 92 |

σ_d is unknown until measured — **run a 5-pair pilot first**, estimate σ_d from it,
then size the main experiment from the table. If σ_d > 0.5, wall-clock cannot
practically resolve a 20% threshold at this budget; fall back to the token-overhead
primary metric, which needs far fewer pairs because its variance is behavioral only.
[CONFIDENCE: HIGH for the arithmetic; LOW for any pre-pilot σ_d guess — that is the
weakest anchor in this section]

---

## (d) Detecting and segmenting compaction events in Claude Code transcripts

**This section is grounded in direct inspection of real transcripts on this machine
(10 genuine compaction events across 4 sessions, Claude Code versions 2.1.121-2.1.170,
8 auto / 2 manual triggers). Confidence: HIGH for the observed versions; the schema is
undocumented and internal — re-validate per Claude Code version.**

### Where the data lives

```
~/.claude/projects/<munged-cwd>/<session-uuid>.jsonl     # one JSON object per line
~/.claude/projects/<munged-cwd>/<session-uuid>/subagents/agent-*.jsonl  # subagent sidechains
```

### Detection: two adjacent markers per compaction event (verified structure)

**Marker 1 — boundary record:**

```json
{
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "logicalParentUuid": "<uuid of last pre-compaction entry>",
  "uuid": "<boundary uuid>",
  "compactMetadata": {
    "trigger": "auto",            // or "manual" (/compact) — both observed locally
    "preTokens": 970893,           // context size before compaction
    "postTokens": 13915,           // context size after
    "durationMs": 125246,          // compaction wall time
    "preCompactDiscoveredTools": ["..."]
  },
  "version": "2.1.128", "sessionId": "...", "timestamp": "..."
}
```

`preTokens/postTokens` give the compression ratio for free (69.8× in this observed
event) and `durationMs` feeds the RQ5 overhead analysis directly.

**Marker 2 — summary record (immediately after, `parentUuid` = boundary uuid):**

```json
{
  "type": "user",
  "isCompactSummary": true,
  "isVisibleInTranscriptOnly": true,
  "message": { "role": "user", "content": "This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.\n\nSummary:\n1. Primary Request and Intent: ..." }
}
```

The opening sentinel string is fixed across all 9 locally observed summaries.

### Summary internal structure (verified across 9 real summaries)

Stable 9-section numbered template:

```
1. Primary Request and Intent
2. Key Technical Concepts
3. Files and Code Sections
4. Errors and fixes          (capitalization varies: "Errors and Fixes" also observed)
5. Problem Solving
6. All user messages         ("All User Messages" also observed)
7. Pending Tasks
8. Current Work
9. Optional Next Step
```

**Parsing rule (pitfall observed during this research):** anchor `summary_parser.py`
section splitting on the exact known header strings (case-insensitive match), NOT on a
generic `^\d+\. [A-Z]...:` regex — numbered lists inside section bodies produce false
positive headers (two observed in the local corpus). Mean summary length ≈ 13 K chars.

### Segmentation algorithm

```python
# Split a session JSONL into compaction epochs
events = [json.loads(l) for l in open(path)]          # tolerate non-JSON lines
boundaries = [i for i, e in enumerate(events)
              if e.get("type") == "system"
              and e.get("subtype") == "compact_boundary"]
# epoch k = entries between boundary k-1 (exclusive) and boundary k (inclusive of summary)
# pre-compaction content of epoch k: entries up to events[boundaries[k]]
#   (chain check: boundary.logicalParentUuid == last pre-entry uuid)
# summary of epoch k: next entry with isCompactSummary == True
#   (chain check: summary.parentUuid == boundary.uuid)
# SPF inputs: originals = artifacts injected during epoch k's pre-segment;
#             recovered = matching spans in epoch k's summary
```

Handle **multiple boundaries per session** — cascading compaction is the high-value
case (Zahn & Chana measure 54% constraint erosion across cascades; arXiv:2603.17781).

### Driving sessions vs harvesting transcripts

- **SDK/CLI stream surface:** the Agent SDK emits `type:"system",
  subtype:"compact_boundary"` with `compact_metadata: {trigger, pre_tokens}` in the
  message stream (TypeScript `SDKCompactBoundaryMessage`; Python `SystemMessage`)
  — verified against the official Agent SDK docs. **The on-disk transcript is
  strictly richer** (`postTokens`, `durationMs`, `preCompactDiscoveredTools` are
  absent from the documented SDK surface). [CONFIDENCE: HIGH]
- **Recommendation:** drive sessions via `claude -p`/Agent SDK (subscription auth,
  rule #10 compliant), use the stream's `compact_boundary` for live detection/pausing,
  then **harvest the disk JSONL as the ground-truth record** for all metrics.
- **Triggering compaction deliberately:** `trigger:"manual"` (/compact or SDK
  equivalent) gives controlled, cheap compaction events with the identical transcript
  schema (verified: same structure for both trigger values locally). Auto-trigger
  requires filling the context window — slower and costlier but is the genuine
  production phenomenon. Use manual for pipeline development/calibration, auto for the
  headline campaign; report `trigger` as a stratification variable.
- **Schema drift gate:** the format is undocumented and internal. Stable across
  2.1.121→2.1.170 as observed, but pin the Claude Code version per campaign, record it
  (it is in every transcript line), and add a schema-validation check that fails loudly
  on unknown structure rather than silently mis-parsing.

### Free calibration corpus

10 genuine compaction events (8 auto, 2 manual) already exist on this machine. Use them
to (1) develop and test the segmentation parser before any live campaign, (2)
recalibrate the 0.9/0.7 tier thresholds per embedding backend, (3) pilot the Layer 2
NLI scoring. Zero campaign cost.

---

## Computational Tools

| Tool | Version | Purpose | Why |
|---|---|---|---|
| sentence-transformers | latest (pin at install) | SPF_embedding backend | Already the designed primary backend in `embedding_similarity.py`; auto device selection |
| torch | latest with CPU/MPS | backend for above | Required by sentence-transformers; check Python 3.14 wheel availability, else 3.11/3.12 venv |
| MiniCheck (github.com/Liyan06/MiniCheck) | repo main, pin commit | Layer 2 factual consistency | EMNLP 2024, GPT-4-level grounding checks at 770 M params, runs locally |
| scipy | 1.17.1 (present) | Beta quantiles for Jeffreys bounds; Wilcoxon | Already installed and used by v2.0 stats |
| claude CLI / Agent SDK | pin per campaign | session driver, subscription auth | Rule #10: no paid API; compact_boundary stream events |
| Python stdlib json/re | 3.14.5 | transcript parsing | Zero-dependency parsing path stays dependency-free |

## Installation / Setup

```bash
# Commands for a later permission-gated setup step — not silently installed.
# If torch lacks Python 3.14 wheels, create the venv with python3.12.
python3 -m venv .venv-metrics && source .venv-metrics/bin/activate
pip install torch sentence-transformers scipy
pip install "minicheck @ git+https://github.com/Liyan06/MiniCheck.git"   # verify exact extra per repo README at install time
# Model downloads on first use: all-MiniLM-L6-v2 (~80 MB), bge-small-en-v1.5 (~130 MB),
# MiniCheck flan-t5-large (~3 GB)
```

## What NOT to Use

| Avoid | Why | Use Instead |
|---|---|---|
| Paid embedding/judge APIs (OpenAI, Voyage, Anthropic API key) | Hard project rule #10; also breaks reproducibility-without-spend | Local sentence-transformers + MiniCheck |
| Bespoke-MiniCheck-7B locally | ~14 GB fp16 on a 16 GB machine — swap death | MiniCheck-Flan-T5-Large (770 M) |
| Per-ref Bernoulli counting for the CP bound | Refs cluster within sessions; fabricates sample size | Session-level outcome + cluster bootstrap |
| Quoting CP bound at an early-stopped n | Optional-stopping bias; realized coverage < 95% | Pre-registered fixed n (or confidence sequences) |
| Mean wall-clock comparison, unpaired | LLM latency heavy-tailed + non-deterministic outputs (arXiv:2308.02828, 2408.04667) | Paired log-scale geometric-mean ratio, median/p90 |
| Generic numbered-header regex on summaries | False positives observed in real local data | Exact-header anchored parsing, case-insensitive |
| LLM-as-judge (`claude -p`) as primary fidelity metric | Circular: Claude judging Claude's compaction | MiniCheck primary; LLM-judge only as labeled exploratory annex |

## Validation Strategy

| Check | Expected Result | Tolerance | Reference |
|---|---|---|---|
| Parser on 10 local genuine compaction events | 10/10 boundaries + summaries detected, chain UUIDs consistent | exact | local data, verified 2026-06-12 |
| Embedding backend on synthetic perturbation pairs (identity / paraphrase / entity-swap / negation) | identity ≈ 1.0 > paraphrase > entity-swap > negation ordering | monotone ordering must hold | standard STS sanity check |
| Token-overlap vs embedding agreement on calibration set | rank correlation positive; disagreements manually triaged | Spearman ρ > 0.5 expected, investigate below | internal consistency |
| MiniCheck on hand-labeled claims from the 9 local summaries | ≥ 80% agreement with manual labels on a 30-claim sample | pre-registered | LLM-AggreFact reported accuracy range |
| CP implementation vs scipy `beta.ppf` cross-check | bounds match closed form 1−0.05^(1/n) | 1e-12 | Clopper-Pearson 1934 |
| Overhead pipeline dry-run on mock timings | recovers injected 20% synthetic overhead | CI covers truth | internal |

## Sources

**Verified via search/inspection this session:**

- Tang, Laban, Durrett — "MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents", EMNLP 2024, arXiv:2404.10774; repo github.com/Liyan06/MiniCheck [HIGH]
- Laban et al. — "SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization", TACL 2022, arXiv:2111.09525 [HIGH]
- Zha et al. — "AlignScore: Evaluating Factual Consistency with a Unified Alignment Function", ACL 2023, arXiv:2305.16739 [HIGH]
- Zahn & Chana — "Facts as First Class Objects: Knowledge Objects for Persistent LLM Memory", arXiv:2603.17781 (Mar 2026) — 60% fact loss / 54% cascading erosion [MEDIUM — recent preprint]
- Ouyang, Zhang, Harman, Wang — "An Empirical Study of the Non-determinism of ChatGPT in Code Generation", TOSEM 34(2) 2025, arXiv:2308.02828 [HIGH]
- "Non-Determinism of 'Deterministic' LLM Settings", arXiv:2408.04667 [MEDIUM — preprint]
- "Do Automatic Factuality Metrics Measure Factuality? A Critical Evaluation", arXiv:2411.16638 [MEDIUM]
- Claude Agent SDK docs (platform.claude.com/docs/en/agent-sdk/typescript, .../agent-loop) — `SDKCompactBoundaryMessage`, `compact_metadata {trigger, pre_tokens}` [HIGH — official docs]
- 2026 embedding-model surveys: Milvus blog "choose-embedding-model-rag-2026", KnowledgeSDK MTEB guides [LOW-MEDIUM — blog-tier; use HF MTEB leaderboard for final ranking at implementation time]
- MPS small-batch embedding benchmark (MemPalace issue #515 discussion) [LOW-MEDIUM — single source]
- LLMPerf / Anyscale latency benchmarking docs (docs.anyscale.com/llm/serving/benchmarking/metrics) [MEDIUM]
- **Local ground truth:** `~/.claude/projects/**/*.jsonl` — 10 compact_boundary events, 9 parsed summaries, CC versions 2.1.121-2.1.170, inspected 2026-06-12 [HIGH — primary data]

**Established results cited from training knowledge (canonical, >20 y):**

- Clopper & Pearson, "The use of confidence or fiducial limits illustrated in the case of the binomial", Biometrika 26:404-413 (1934)
- Hanley & Lippman-Hand, "If nothing goes wrong, is everything all right? Interpreting zero numerators", JAMA 249(13):1743-1745 (1983)
- Howard, Ramdas, McAuliffe, Sekhon — "Time-uniform, nonparametric, nonasymptotic confidence sequences", Ann. Statist. 49(2) 2021, arXiv:1810.08240
- Zhang et al. — "BERTScore: Evaluating Text Generation with BERT", ICLR 2020, arXiv:1904.09675 (cited as alternative-considered only)

---

_Methods research for: Primordial v3.0 Live Validation_
_Researched: 2026-06-12 — all numerical tables computed exactly this session (scipy 1.17.1); all transcript schema claims verified against local disk data_
