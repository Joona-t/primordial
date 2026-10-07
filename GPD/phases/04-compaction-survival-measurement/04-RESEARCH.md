# Phase 4: Compaction Survival Measurement - Research

**Researched:** 2026-03-16
**Domain:** Provenance reachability under LLM context-window compaction / DAG integrity measurement / information-loss quantification
**Confidence:** MEDIUM

## Summary

Phase 4 is the highest-risk measurement phase and the project's genuinely open question: do provenance chains survive real context-window compaction with measurable reachability? The phase must produce tasks that accumulate 128K+ tokens to trigger actual LLM compaction events, then measure what happens to the forge provenance DAG after compaction. The challenge is twofold: (1) triggering genuine compaction in a controlled-enough environment to produce meaningful measurements, and (2) distinguishing between structural reachability (refs resolve to some artifact) and semantic reachability (the content behind those refs is faithful to the original).

The recommended approach has three components. First, design and execute long-running tasks that reliably exceed the context-window threshold and trigger observable compaction events -- the Claude API's `compact_20260112` strategy provides both the mechanism and observability (compaction blocks are structurally distinct in the response). Second, instrument the pre-compaction and post-compaction states so that the provenance DAG can be measured at both points -- this requires capturing the full artifact set before compaction and the surviving artifact set after. Third, compare post-compaction reachability against the Phase 2 MockLM ceiling (reachability=1.0) and measure trace compression ratio against the Phase 2 anchor (1.18x on real data, MockLM anchor 87%). The measurement toolkit is straightforward: BFS/DFS on provenance DAGs via NetworkX, SHA-256 hash comparison for structural integrity, and bootstrap CIs for uncertainty.

The critical architectural insight from Phase 2 is that OpenClaw/Zarathustra's queue-worker layer does NOT perform LLM compaction -- it uses cursor-based state advancement. The compaction that Phase 4 must measure happens at the **inner execution layer**, likely Claude Code's auto-compaction mechanism (triggering at approximately 95% context capacity or via the `compact_20260112` API). This means Phase 4 operates at a different instrumentation layer than Phase 2/3's post-hoc ledger analysis. The adapter must either: (a) intercept the compaction event within the LLM session (if using the Claude API directly with `pause_after_compaction`), or (b) reconstruct pre/post-compaction state from session transcripts or JSONL records after the fact.

**Primary recommendation:** Use the Claude API's `compact_20260112` endpoint with `pause_after_compaction=true` to gain observability over compaction events. Register forge artifacts before and after each compaction event. Measure provenance DAG reachability via BFS on the post-compaction artifact set, compare against the pre-compaction DAG, and report the reachability fraction with bootstrap 95% CIs.

## Active Anchor References

| Anchor / Artifact | Type | Why It Matters Here | Required Action | Where It Must Reappear |
| --- | --- | --- | --- | --- |
| ref-mock-experiment (reachability=1.0) | benchmark | Controlled-condition ceiling. Phase 4 measures degradation from this ceiling under real compaction. | Compare post-compaction reachability against 1.0. Report gap and explain which refs broke. | plan, execution, verification, final report |
| ref-mock-experiment (compression=87%) | benchmark | Trace compression anchor. Phase 4 measures compression ratio on real compacted tasks. | Measure trace compression on compacted tasks, compare against 87% and Phase 2's 1.18x. | plan, execution, report |
| Phase 2 baseline data | prior artifact | Forge reachability=1.0, compression=1.18x, depth=21 on real (non-compacted) ledger data. Establishes the non-compacted real-data baseline. | Use as pre-compaction reference. Gap = (non-compacted real) - (post-compacted real). | plan, execution, gap analysis |
| Phase 3 detection data | prior artifact | 4/9 fault types detected (44.4%). Violation detection must remain functional after compaction. | Run violation detection on post-compaction traces. Confirm D1/D2/D5/D9 still detected. | plan, execution, regression check |
| compaction-characterization.md | prior analysis | Queue-worker layer does NOT do LLM compaction. Inner execution layer is uncharacterized. Phase 4 must instrument the inner layer. | Use characterization to avoid re-investigating queue-worker layer. Focus on LLM session layer. | plan |
| task-corpus.md (L1-L3) | carry-forward input | Long tasks designed for 128K+ tokens. These are the compaction-triggering workloads. | Use L1-L3 as the task set. May need to extend if compaction does not trigger. | plan, execution |
| OpenClawAdapter | carry-forward input | 4 interception points for post-hoc ledger analysis. Must be extended or complemented for LLM session layer. | Extend with compaction event detection; or build parallel instrumentation for session layer. | plan, execution |
| CONVENTIONS.md #6 | contract constraint | "Compaction" always qualified. Phase 4 measures LLM context-window compaction (lossy semantic), NOT forge trace compression (lossless structural). | All metrics, reports, and code comments must qualify which compaction layer is measured. | plan, execution, reporting |

**Missing or weak anchors:**
- **Inner execution layer characterization:** Phase 2 characterized the queue-worker layer but explicitly flagged the inner execution layer as "UNCHARACTERIZED." Phase 4 depends on understanding how the task executor (run_queue.py -> Claude Code / Claude API) handles context-window management. If this layer is fully opaque, provenance measurement at this layer may be impossible.
- **VM access:** Phase 2 and 3 ran on local ledger samples, not live VM execution. Phase 4 requires either VM access or a local simulation of 128K+ token tasks that trigger genuine API-level compaction.
- **Pre-compaction snapshot mechanism:** No existing tool captures the full artifact state immediately before a compaction event. This must be built.

## Conventions

| Choice | Convention | Alternatives | Source |
| --- | --- | --- | --- |
| Compaction layer | LLM context-window compaction (lossy semantic) | Forge trace compression (lossless structural), cursor advancement (queue-worker) | CONVENTIONS.md #6, compaction-characterization.md |
| Reachability metric | reachability_fraction = reachable_artifacts / total_artifacts via BFS/DFS on provenance DAG | Reachability depth only, per-artifact binary | CONVENTIONS.md #7 |
| Compression metric | compression_ratio = original_size / encoded_size | Space saving (1 - encoded/original) | CONVENTIONS.md #7, forge_trace_codec.py |
| CI method | Bootstrap 95% CI for N >= 5; Clopper-Pearson for boundary proportions | Wald interval (poor coverage for small N) | Phase 3 established convention |
| Compaction trigger threshold | 128K+ tokens of accumulated state | 50K (API minimum), 150K (API default) | COMP-01, task-corpus.md |
| Ref classification | Each ref classified as: resolved (content reachable and matches), degraded (ref resolves but content is lossy-summarized), or broken (ref does not resolve) | Binary resolved/broken only | Novel for Phase 4 -- extends Phase 2 binary |
| Hash verification | SHA-256 on canonical JSON (sort_keys=True, ensure_ascii=True) | MD5, CRC32 | forge_trace_codec.py established |

**CRITICAL: All equations and results below use these conventions. "Compaction" means LLM context-window compaction (lossy semantic) unless explicitly qualified as "forge trace compression" (lossless structural) or "cursor advancement" (queue-worker layer).**

## Mathematical Framework

### Key Equations and Starting Points

| Equation | Name/Description | Source | Role in This Phase |
| --- | --- | --- | --- |
| `reachability_fraction = count(reachable_via_BFS) / total_artifacts` | Provenance reachability | CONVENTIONS.md #7 | Primary metric: what fraction of artifacts can trace back to root? |
| `degradation = reachability_pre_compaction - reachability_post_compaction` | Reachability degradation | New for Phase 4 | Measures how much compaction reduces provenance completeness |
| `compression_ratio = original_size / encoded_size` | Trace compression | forge_trace_codec.py | Secondary metric: how efficiently does forge compress post-compaction traces? |
| `ref_status(r) = resolved if hash(content(r)) == original_hash(r), degraded if ref resolves but hash differs, broken if ref does not resolve` | Three-tier ref classification | New for Phase 4 -- extends Pitfall 2 mitigation | Distinguishes structural from semantic reachability |
| `semantic_fidelity = resolved_refs / (resolved_refs + degraded_refs + broken_refs)` | Semantic reachability | New for Phase 4 | Measures content fidelity, not just structural resolution |
| `structural_reachability = (resolved_refs + degraded_refs) / total_refs` | Structural reachability | Phase 2 convention | Measures ref existence regardless of content fidelity |
| `CI_bootstrap = [percentile(2.5), percentile(97.5)]` of B=10000 resamples | Bootstrap 95% CI | baseline_measurement.py | Uncertainty quantification for all metrics |

### Required Techniques

| Technique | What It Does | Where Applied | Standard Reference |
| --- | --- | --- | --- |
| BFS/DFS on provenance DAG | Compute reachability from each artifact to root nodes | Post-compaction artifact set | METHODS.md Method 4 |
| SHA-256 hash comparison | Detect content degradation after compaction | Pre-compaction vs post-compaction artifact content | forge_trace_codec.py |
| Pre/post compaction snapshots | Capture full artifact state at compaction boundary | Before and after each compaction event | New for Phase 4 |
| Compaction event detection | Identify when LLM compaction occurs and what content was affected | Claude API `compaction` block or session transcript analysis | Claude API docs |
| Three-tier ref classification | Classify each ref as resolved/degraded/broken | Post-compaction provenance analysis | New for Phase 4 |
| Forge violation regression | Verify D1/D2/D5/D9 detection still works post-compaction | Post-compaction forge traces | Phase 3 established |

### Approximation Schemes

| Approximation | Small Parameter | Regime of Validity | Error Estimate | Alternatives if Invalid |
| --- | --- | --- | --- | --- |
| BFS/DFS exact reachability | N/A (exact computation) | DAG with V < 1000, E < 5000 (expected range) | Exact -- no approximation | Monte Carlo sampling for very large DAGs (V > 10000) |
| Bootstrap percentile CI | N >= 5 data points | N in [5, 30]; exchangeability assumed | Coverage ~93-97% for N=10 | Clopper-Pearson exact binomial for proportions near 0 or 1 |
| Token count estimation (chars/4) | Token estimation error ~20-40% | Short-medium text | Off by up to 40% for code-heavy content | tiktoken for exact counts; or rely on API's reported input_tokens |
| Compaction trigger as proxy for "genuine context pressure" | Threshold >= 128K tokens | Tasks that organically accumulate state | False negatives if compaction triggers at different thresholds than expected | Use Claude API's reported compaction events rather than estimating |

## Standard Approaches

### Approach 1: Claude API Compaction with Instrumented Snapshots (RECOMMENDED)

**What:** Use the Claude API's `compact_20260112` endpoint with `pause_after_compaction=true` to gain structured observability over compaction events. Before each API call that may trigger compaction, snapshot the current forge artifact set (pre-compaction state). When the API returns a `compaction` stop reason, capture the compaction summary block and record which message content was replaced. After the compacted conversation continues, snapshot the post-compaction forge artifact set. Compare pre and post states via BFS reachability on the provenance DAG.

**Why standard:** The Claude API's compaction mechanism is the best-documented, most observable LLM compaction pathway available. The `pause_after_compaction` parameter provides a clean interception point where the pre/post boundary is unambiguous. This is directly measuring the phenomenon the project claims to handle (LLM context-window compaction), not simulating it.

**Track record:** This is the first time this measurement is attempted in this project. Phase 2 established reachability=1.0 under non-compacted conditions. Phase 4 measures degradation from that ceiling.

**Key steps:**

1. **Extend task execution harness.** Build a task runner that uses the Claude API with `compact_20260112` enabled. Configure trigger threshold at 128K tokens (or lower if needed to ensure compaction fires within the task). Each task must accumulate enough context to trigger at least one compaction event.

2. **Pre-compaction snapshot.** Before each API call, serialize the current forge chamber state: all artifacts, all source_refs, all hashes. Store as a timestamped snapshot.

3. **Detect compaction event.** When the API response includes a `compaction` block (identified by `stop_reason == "compaction"` or `content[i].type == "compaction"`), record: (a) the compaction summary text, (b) the number of tokens before and after compaction, (c) which message blocks were dropped.

4. **Post-compaction snapshot.** After the conversation continues post-compaction, register the compaction event as a forge artifact with `output_state: "pruned_recoverable"` and `source_refs` pointing to all artifacts that existed in the pre-compaction snapshot. Serialize the new chamber state.

5. **BFS reachability analysis.** For each post-compaction snapshot, build the provenance DAG from the artifact set. Compute reachability_fraction via BFS from every artifact to the root. Classify each ref as resolved (content hash matches pre-compaction), degraded (ref resolves but content hash differs due to summarization), or broken (ref does not resolve to any artifact).

6. **Measure trace compression.** Run `encode_trace()` on the post-compaction chamber. Compare compression_ratio against Phase 2 baseline (1.18x) and MockLM anchor (87%).

7. **Violation detection regression.** Run the Phase 3 fault injector on post-compaction traces. Confirm D1/D2/D5/D9 detection remains functional. Report any detection rate changes.

**Known difficulties at each step:**

- Step 1: Tasks must genuinely accumulate 128K+ tokens. If the task resolves too quickly, compaction never fires. Mitigation: use deliberately complex multi-step tasks (L1-L3 from task corpus) or artificially extend context by including verbose tool outputs.
- Step 2: Snapshots must capture the FULL state, including content that will be summarized. This is memory-intensive for 128K+ token sessions. Mitigation: snapshot only forge-tracked artifacts and their hashes, not the full conversation history.
- Step 3: The compaction summary is a lossy representation. The boundary between "what was preserved" and "what was lost" is implicit in the summary text. Mitigation: compare pre-compaction artifact content hashes against post-compaction summary for explicit loss quantification.
- Step 5: Distinguishing "degraded" from "broken" requires comparing content, not just ref existence. If the compaction summary paraphrases an artifact's content, the ref resolves structurally but the hash differs -- this is "degraded," not "broken."
- Step 7: Post-compaction traces may have different structural properties (fewer stages, different ref topology) that affect violation detection. Some fault types may not be applicable post-compaction.

### Approach 2: Simulated Compaction via Truncation (FALLBACK)

**What:** If genuine API-level compaction cannot be triggered (VM unavailable, API changes, cost constraints), simulate compaction by programmatically truncating the forge artifact set to mimic what compaction would do. Remove the oldest N% of artifacts and their content, keeping only ref stubs. Then measure reachability on the truncated DAG.

**When to switch:** If after 3+ attempts, no task triggers a genuine compaction event. Or if API access is unavailable and the phase must proceed on local data.

**Tradeoffs:** Simulated compaction tests the measurement framework but does NOT test whether real LLM compaction preserves or destroys provenance. The results would be reported as "simulated compaction" with reduced confidence. This is a weaker claim than genuine compaction measurement but still validates the measurement tooling.

### Approach 3: Session Transcript Post-Hoc Analysis (COMPLEMENTARY)

**What:** If using Claude Code (rather than the raw API), analyze the session JSONL transcript after task execution. Claude Code writes session transcripts that include microcompaction, auto-compaction, and manual compaction events. Parse these transcripts to reconstruct the compaction timeline and identify which content was compacted.

**When to use:** As a complement to Approach 1 if using Claude Code as the task executor. Provides a second data source for compaction event detection.

**Tradeoffs:** Session transcripts may not be available in all deployment configurations. The transcript format is not a stable API. But this approach requires no code changes to the executor.

### Anti-Patterns to Avoid

- **Using `_fake_count_tokens` to simulate compaction.** PITFALLS.md explicitly flags this: the MockLM experiment used a fake token counter that forces compaction after 5 messages regardless of content. This tests the protocol logic but completely bypasses real context pressure. Phase 4 MUST use genuine token accumulation.
- **Conflating forge trace compression with LLM compaction.** These are measured separately (Convention #6). Reporting forge compression_ratio as evidence of "compaction survival" is a forbidden conflation.
- **Measuring only tasks that complete successfully.** Survivorship bias. Tasks that fail or trigger the backtracking condition (reachability < 50%) are the most informative data points.
- **Running only short tasks and claiming compaction works.** The contract explicitly forbids fp-short-tasks. Every task must exceed 128K tokens and trigger at least one compaction event.
- **Treating structural reachability as proof of semantic preservation.** Pitfall 2 from PITFALLS.md. A ref that resolves to a lossy summary is structurally reachable but semantically degraded. Report both metrics separately.

## Existing Results to Leverage

### Established Results (DO NOT RE-DERIVE)

| Result | Exact Form | Source | How to Use |
| --- | --- | --- | --- |
| MockLM reachability ceiling | 1.0 (100% all scenarios) | tools/experiment_results.json | Compare post-compaction reachability against this ceiling |
| MockLM compression anchor | 87% (0.87 compression ratio vs vanilla) | tools/experiment_results.json | Compare post-compaction trace compression |
| Phase 2 forge reachability (non-compacted) | 1.0 on real ledger data | data/baselines/baseline-report.json | Pre-compaction real-data baseline |
| Phase 2 forge compression (non-compacted) | 1.18x on real ledger data | data/baselines/baseline-report.json | Pre-compaction real-data compression |
| Phase 2 provenance depth | 21 | data/baselines/baseline-report.json | Pre-compaction chain depth for comparison |
| Phase 2 uninstrumented reachability | 0.0 | data/baselines/baseline-report.json | Floor value (no provenance) |
| Phase 3 forge detection rate | 40/90 = 44.4% [CI: 0.344, 0.544] on D1-D9 | data/campaign/campaign-report.json | Pre-compaction detection rate for regression comparison |
| Phase 3 detected fault types | D1, D2, D5, D9 at 100%; D3/D4/D6/D7/D8 at 0% | data/campaign/campaign-report.json | Regression check: D1/D2/D5/D9 must still detect post-compaction |
| Phase 3 FPR | 0.0% (0/30) | data/campaign/campaign-report.json | FPR must remain low post-compaction |
| Queue-worker has NO LLM compaction | Cursor advancement only, no prompt summarization | docs/compaction-characterization.md | Do NOT re-investigate queue-worker layer; focus on LLM session layer |
| BFS reachability is O(V+E) | Exact computation, no approximation needed | METHODS.md Method 4 | Use directly; no Monte Carlo sampling needed for expected graph sizes |
| Bootstrap CI implementation | bootstrap_ci() with B=10000, seed=42 | tools/baseline_measurement.py | Reuse for all CI computation |
| Clopper-Pearson exact CI | For boundary proportions (0/n or n/n) | Phase 3 convention | Use when reachability is 0.0 or 1.0 |

**Key insight:** Phase 2 established reachability=1.0 on non-compacted real data. Phase 4 measures degradation from this ceiling. If post-compaction reachability is also 1.0, the claim is strong but suspiciously perfect -- verify that compaction actually occurred. If post-compaction reachability is < 1.0, the interesting question is WHICH refs broke and WHY.

### Useful Intermediate Results

| Result | What It Gives You | Source | Conditions |
| --- | --- | --- | --- |
| OpenClawAdapter.process_session_events() | Parses JSONL ledger into forge chambers | tools/openclaw_adapter.py | Post-hoc analysis mode; queue-worker layer only |
| encode_trace() / decode_trace() | Structural trace compression with exact reversibility | tools/forge_trace_codec.py | Forge trace compression (lossless) -- distinct from LLM compaction |
| verify_trace() | Round-trip hash verification | tools/forge_trace_codec.py | Checks structural integrity of trace encoding, NOT semantic content |
| validate_chamber() | Structural invariant checking on chambers | tools/forge_chamber.py | Returns list of structural errors; does not check semantic content |
| FaultInjector (D1-D9) | Injection harness for all 9 fault types | tools/fault_injector.py | Reuse for post-compaction violation regression testing |
| bootstrap_ci() | Non-parametric CI computation | tools/baseline_measurement.py | Reuse with same parameters (B=10000, seed=42) |

### Relevant Prior Work

| Paper/Result | Authors | Year | Relevance | What to Extract |
| --- | --- | --- | --- | --- |
| Evaluating Context Compression for AI Agents | Factory.ai | 2025 | Probe-based evaluation framework for measuring what information survives compression: recall probes, artifact probes, continuation probes, decision probes | Probe methodology for measuring semantic vs structural survival |
| Compaction vs Summarization | Morph | 2025 | Distinguishes deletion-based compaction (preserves exact text) from summarization (paraphrases). Morph Compact reduces context 50-70% with verbatim survival. | The distinction between deletion-based and summarization-based compaction affects what "degraded" means |
| Building an internal agent: Context window compaction | Lethain | 2026 | Practical compaction patterns: "Compaction destroys specifics: file paths, exact values, config details, reasoning chains." | Specific classes of information lost under compaction -- directly informs what to measure |
| Understanding and Improving Information Preservation in Prompt Compression | arXiv:2503.19114 | 2025 | Measures information preservation via reconstruction: can the compressed prompt be used to reconstruct the original? | Reconstruction as a measurement strategy for semantic fidelity |
| Compaction API documentation | Anthropic | 2026 | `compact_20260112` strategy, `pause_after_compaction`, `compaction` content block type, `compaction` stop reason, trigger configuration | Technical mechanism for observing and controlling compaction events |

## Computational Tools

### Core Tools

| Tool | Version/Module | Purpose | Why Standard |
| --- | --- | --- | --- |
| Python | 3.11+ | All implementation | Matches existing forge tools |
| networkx | 3.x | Provenance DAG construction and BFS reachability | Standard graph library; already in project dependencies from METHODS.md |
| anthropic | SDK (latest) | Claude API with `compact_20260112` compaction support | Official SDK; required for compaction endpoint access |
| pytest | 8.x | Test runner for regression tests | Matches existing test suite |
| numpy | 1.26+ | Bootstrap resampling | Already used by baseline_measurement.py |

### Supporting Tools

| Tool | Purpose | When to Use |
| --- | --- | --- |
| json (stdlib) | Artifact serialization, session transcript parsing | All data I/O |
| hashlib (stdlib) | SHA-256 for content hash comparison pre/post compaction | Content fidelity measurement |
| pathlib (stdlib) | Snapshot file management | Pre/post compaction snapshot storage |
| copy (stdlib) | Deep copy of artifact state for snapshots | Pre-compaction snapshot creation |
| scipy.stats | Clopper-Pearson exact CI for boundary proportions | When reachability is exactly 0.0 or 1.0 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
| --- | --- | --- |
| Claude API `compact_20260112` | Claude Code auto-compaction | Claude Code auto-compaction is less controllable (triggers at ~95% capacity), harder to observe programmatically, but closer to real-world usage |
| networkx BFS | Custom BFS on dict-based adjacency list | networkx is heavier but well-tested for correctness; custom BFS is lighter but risks edge-case bugs |
| SHA-256 content comparison | ROUGE/BERTScore for semantic similarity | Hash comparison gives binary match/mismatch; ROUGE/BERTScore could measure degree of degradation, but adds complexity and model dependency |

### Computational Feasibility

| Computation | Estimated Cost | Bottleneck | Mitigation |
| --- | --- | --- | --- |
| Long-task execution (128K+ tokens, 3+ tasks) | 3-8 hours LLM time; $10-50 API cost | LLM API latency; token accumulation time | Run tasks in sequence; batch overnight if needed |
| Pre/post compaction snapshots | < 1 second per snapshot | Memory for 128K+ token artifact sets | Snapshot hashes and refs only, not full content |
| BFS reachability on provenance DAG | < 100ms per chamber | None (exact, O(V+E), V < 1000) | Negligible |
| Trace compression (encode_trace) | < 100ms per chamber | None | Negligible |
| Bootstrap CI computation | < 1 second per metric | None | Negligible |
| Violation detection regression (D1-D9) | < 1 minute for all 9 types | Building post-compaction fault injection | Reuse existing FaultInjector |

**Installation / Setup:**
```bash
# networkx and anthropic SDK needed
pip install networkx anthropic  # or: uv add networkx anthropic
# scipy for Clopper-Pearson (if not already installed from Phase 3)
pip install scipy  # or: uv add scipy
# All other dependencies (numpy, pytest) already installed
```

## Validation Strategies

### Internal Consistency Checks

| Check | What It Validates | How to Perform | Expected Result |
| --- | --- | --- | --- |
| Compaction event verification | At least one compaction event occurred during the task | Check API response for `compaction` content blocks or `stop_reason == "compaction"` | Each long task must produce >= 1 compaction event |
| Token threshold verification | Task accumulated 128K+ tokens before compaction | Check API-reported `input_tokens` immediately before compaction trigger | input_tokens >= 128,000 at compaction trigger |
| Pre-compaction reachability | Reachability is 1.0 before compaction (consistent with Phase 2) | Run BFS on pre-compaction snapshot | reachability_fraction == 1.0 (matching Phase 2 baseline) |
| DAG acyclicity | Provenance DAG has no cycles (cycles indicate a bug) | Check for cycles in networkx DiGraph before BFS | is_directed_acyclic_graph() == True |
| Round-trip integrity | Trace encoding is still lossless after compaction | verify_trace() on post-compaction chambers | hash_match == True (forge trace compression is always lossless) |
| Violation detection regression | D1/D2/D5/D9 still detected post-compaction | Run FaultInjector with D1/D2/D5/D9 on post-compaction chambers | Detection rate for D1/D2/D5/D9 >= Phase 3 rate (100% on those types) |
| Ref classification consistency | Every ref classified as exactly one of resolved/degraded/broken | Sum of three categories == total refs | resolved + degraded + broken == total_refs |

### Known Limits and Benchmarks

| Limit | Parameter Regime | Known Result | Source |
| --- | --- | --- | --- |
| Non-compacted reachability | No LLM compaction events | 1.0 (100%) | Phase 2 baseline-report.json |
| Non-compacted compression | No LLM compaction events | 1.18x (real data), ~1.10x (MockLM) | Phase 2 baseline-report.json |
| MockLM controlled ceiling | Deterministic, no real context pressure | reachability=1.0, compression=87%, detection=6/6 | experiment_results.json |
| Uninstrumented floor | No forge instrumentation | reachability=0.0, detection=0 | Phase 2 baseline-report.json |
| Phase 3 detection ceiling | Injected faults on non-compacted data | 4/9 types detected (44.4%) | Phase 3 campaign-report.json |

### Numerical Validation

| Test | Method | Tolerance | Reference Value |
| --- | --- | --- | --- |
| Reachability fraction range | Assert 0.0 <= reachability <= 1.0 | Exact | Dimensional consistency |
| Compression ratio range | Assert compression_ratio > 0 | Exact | Must be positive |
| Degradation consistency | Assert degradation = pre_reachability - post_reachability >= 0 | Exact | Reachability cannot increase after compaction |
| Ref classification exhaustive | Assert resolved + degraded + broken == total_refs | Exact | All refs must be classified |
| Bootstrap CI sanity | CI lower <= point estimate <= CI upper | Exact | Mathematical property of percentile CI |
| Hash determinism | Same content produces same SHA-256 hash across runs | Exact | Deterministic hashing |

### Red Flags During Computation

- **If post-compaction reachability is exactly 1.0:** This is suspicious unless compaction did not actually occur. Verify that compaction events are logged. If compaction occurred but reachability is still 1.0, check whether the refs are resolving to the compaction summary (which would be "degraded" not "resolved" in the three-tier classification).
- **If post-compaction reachability is exactly 0.0:** Something is fundamentally broken. Even under aggressive compaction, some refs should resolve. Check for DAG construction bugs, incorrect artifact ID matching, or snapshot corruption.
- **If forge trace compression changes dramatically post-compaction:** Trace compression measures structural dedup, which should be independent of LLM compaction. A large change suggests the compaction is altering the structural composition of artifacts, not just their content.
- **If violation detection IMPROVES after compaction:** Nonsensical. Compaction removes information; it cannot add detection capability. Investigate whether the post-compaction trace has a structurally different shape that happens to make certain checks pass differently.
- **If no compaction events fire after 128K+ tokens:** The trigger threshold may be misconfigured, or the API's compaction behavior may differ from documentation. Check the `trigger` parameter in the API request. If using Claude Code, check the auto-compaction threshold.
- **If the DAG has cycles:** This is a bug in artifact construction, not a property of compaction. Cycles should be impossible in a well-formed provenance DAG (children created after parents). Fix before measuring.

## Common Pitfalls

### Pitfall 1: Structural Reachability Masking Semantic Loss (CRITICAL -- Project's Weakest Anchor)

**What goes wrong:** Provenance reachability is 100% (all refs resolve) but the content behind the refs has been lossy-summarized by LLM compaction. The system reports "provenance survived" but the agent is operating on paraphrased approximations, not original artifacts. As Lethain (2026) documents: "Compaction destroys specifics: file paths, exact values, config details, reasoning chains."
**Why it happens:** `validate_chamber()` and BFS reachability check whether refs exist in the artifact index, not whether the content is faithful. Forge's `verify_trace()` checks hash integrity of the trace encoding (lossless layer) but cannot detect semantic degradation by LLM compaction (lossy layer that happens BEFORE forge encoding).
**How to avoid:** Implement the three-tier ref classification: resolved (content hash matches original), degraded (ref resolves but content hash differs), broken (ref does not resolve). Report structural_reachability and semantic_fidelity as SEPARATE metrics. The gap between them quantifies exactly how much compaction degraded provenance.
**Warning signs:** structural_reachability >> semantic_fidelity. All refs resolve but content hashes mismatch.
**Recovery:** If structural reachability is high but semantic fidelity is low, the finding is: "Forge preserves structural provenance through compaction but cannot prevent semantic degradation of content behind refs. This is a limitation of any system operating above the LLM compaction layer."

### Pitfall 2: Tasks Not Triggering Genuine Compaction

**What goes wrong:** L1-L3 tasks complete before accumulating 128K+ tokens, or the LLM compaction mechanism does not fire despite exceeding the threshold. The phase produces measurements of "post-compaction" state where no compaction actually occurred -- which trivially matches the non-compacted baseline.
**Why it happens:** The task corpus was designed based on estimated retry counts (5-7 retries at ~25K each). If the LLM resolves the task in fewer retries, context stays under the threshold. Or the compaction API trigger threshold may be set higher than the accumulated tokens.
**How to avoid:** (a) Monitor API-reported `input_tokens` on each call. (b) Use `pause_after_compaction=true` so compaction events are structurally observable. (c) If compaction does not trigger after 3+ task runs, extend tasks with additional complexity or lower the trigger threshold (minimum 50K per API docs). (d) As a last resort, use deliberately verbose tool outputs to inflate context.
**Warning signs:** Zero compaction events across all task runs. Post-compaction metrics exactly match pre-compaction.
**Recovery:** Extend the task set. Add more complex retry scenarios. Lower the compaction trigger threshold to 50K or 80K for measurement purposes (with caveat that this is a lower threshold than natural operation).

### Pitfall 3: Confusing Queue-Worker State Loss with LLM Compaction

**What goes wrong:** The Phase 2 compaction characterization found that the queue-worker layer uses cursor advancement (lossless at file level), NOT LLM compaction. Phase 4 might accidentally measure cursor advancement effects and report them as "LLM compaction survival" -- which would be trivially successful because cursor advancement does not destroy data.
**Why it happens:** The queue-worker layer and the LLM session layer are different instrumentation targets. The existing OpenClawAdapter operates at the queue-worker layer. Phase 4 needs instrumentation at the LLM session layer.
**How to avoid:** (a) Always qualify which layer is being measured. (b) Verify that compaction events are LLM-generated summaries, not cursor advancement records. (c) If using the Claude API, the `compaction` content block type is unambiguous -- it can only come from LLM compaction.
**Warning signs:** "Compaction" events look like cursor advancement events from the ledger. Reachability is trivially 1.0 because the underlying data was never summarized.
**Recovery:** Re-instrument at the correct layer. If the inner execution layer is fully opaque, report as a limitation.

### Pitfall 4: Measuring Compaction Only on Successful Tasks (Survivorship Bias)

**What goes wrong:** Only tasks that complete successfully are included in the measurement. Tasks that fail or hit the backtracking trigger (reachability < 50%) are excluded, biasing the results toward cases where compaction was benign.
**Why it happens:** It is natural to measure "what survived" and ignore "what failed." But the interesting data is precisely the failure cases.
**How to avoid:** Include ALL tasks in the measurement, regardless of success status. Report measurements for: (a) tasks that completed successfully with compaction, (b) tasks that completed but with degraded provenance, (c) tasks that triggered the backtracking condition.
**Warning signs:** All reported reachability fractions are high. No mention of tasks excluded from analysis.
**Recovery:** Re-run analysis including failed/excluded tasks. Report separately.

## Level of Rigor

**Required for this phase:** Controlled measurement with explicit separation of structural and semantic metrics, honest reporting of what compaction preserves and what it destroys.

**Justification:** This is the project's highest-risk phase and its genuinely open question. The outcome is uncertain and may produce a negative result (compaction breaks provenance beyond recovery). Honest measurement is more important than favorable results.

**What this means concretely:**

- Structural reachability (refs resolve) and semantic fidelity (content behind refs matches original) MUST be reported as separate metrics.
- Every compaction event must be logged with pre/post state.
- If reachability drops below 50%, report honestly as a negative finding per the backtracking trigger.
- All reachability fractions reported with 95% CIs.
- The three-tier ref classification (resolved/degraded/broken) must be applied to every ref in every post-compaction trace.
- Results compared explicitly against MockLM ceiling (reachability=1.0), Phase 2 non-compacted baseline (reachability=1.0), and the backtracking threshold (reachability=0.5).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| Full context window (no compaction) | Context compaction / compression (summarization, deletion, paging) | 2023-2024 (MemGPT, ACON) | LLM systems now routinely compress context; provenance measurement must account for this |
| Binary compaction (keep or discard) | Graduated compaction (summary, microcompaction, hot tail) | 2025-2026 (Claude Code, Google ADK) | Multiple compaction strategies with different preservation characteristics |
| No provenance through compaction | PROV-AGENT, forge (provenance-preserving compaction) | 2025-2026 | Emerging area; forge is among the first to measure provenance survival through LLM compaction |
| Structural integrity only | Structural + semantic reachability | 2025-2026 (Factory.ai probes) | Factory's probe-based evaluation demonstrates that structural survival is insufficient; semantic probes needed |

**Superseded approaches to avoid:**

- **Treating MockLM compaction as representative of real LLM compaction.** MockLM uses `_fake_count_tokens` to force compaction after 5 messages. Real compaction triggers at 128K+ tokens with LLM-generated summaries. Do not extrapolate from MockLM to real conditions.
- **Measuring only forge trace compression ratio and claiming "compaction survival."** Forge trace compression (lossless, hash-verified) is a different layer from LLM compaction (lossy, semantic). Measuring only the lossless layer and claiming compaction survival is a prohibited conflation.

## Open Questions

1. **Is the inner execution layer (run_queue.py -> Claude API) observable?**
   - What we know: The queue-worker layer is semi-transparent with 4 hook points. The inner execution layer was flagged as "UNCHARACTERIZED" by Phase 2.
   - What is unclear: Whether task execution uses the Claude API with compaction enabled, and if so, whether the compaction events are visible to the forge adapter.
   - Impact on this phase: If the inner execution layer is fully opaque, provenance measurement at this layer requires a different approach (Approach 2: simulated compaction or Approach 3: session transcript analysis).
   - Recommendation: Attempt Approach 1 (Claude API with `compact_20260112`) first. If the task executor does not expose API-level compaction events, fall back to Approach 3 (session transcript post-hoc analysis). If neither works, use Approach 2 (simulated compaction) with reduced confidence.

2. **Will compaction preserve artifact IDs in the summary?**
   - What we know: Lethain (2026) reports that compaction "destroys specifics: file paths, exact values, config details." The Claude API compaction summary is a free-form text block -- there is no guarantee that artifact IDs survive.
   - What is unclear: Whether Claude's compaction summarizer preserves structured identifiers like `artifact:openclaw:session1:task:t1:r1` in the summary text, or whether it paraphrases them away.
   - Impact on this phase: If artifact IDs are not preserved in the compaction summary, ALL refs to pre-compaction artifacts will be structurally "broken" (not resolvable from the summary text). This would make reachability_fraction close to 0 and trigger the backtracking condition.
   - Recommendation: Test with a small pilot task. If IDs are lost, investigate whether custom `instructions` in the compaction config can instruct the summarizer to preserve structured identifiers.

3. **Is the three-tier ref classification (resolved/degraded/broken) sufficient?**
   - What we know: Phase 2 used binary (resolved/broken). Phase 4 introduces "degraded" for refs that resolve but whose content is lossy-summarized.
   - What is unclear: Whether "degraded" should have sub-levels (slightly degraded vs heavily degraded) based on ROUGE or BERTScore similarity to the original.
   - Impact on this phase: A binary resolved/broken classification would miss the middle ground where compaction preserves structure but degrades content.
   - Recommendation: Start with the three-tier classification. If the data shows a wide range of degradation levels, consider adding a continuous `fidelity_score` as metadata on degraded refs. But do not over-engineer before seeing the data.

4. **What is the provenance metadata overhead under compaction?**
   - What we know: Phase 2 measured forge trace overhead at +460% vs raw events (but this measures chamber metadata, not provenance-specific overhead). The context budget under compaction is reduced.
   - What is unclear: Whether provenance metadata (source_refs, hashes, typed absence states) consumes a significant fraction of the post-compaction context budget, accelerating the next compaction cycle.
   - Impact on this phase: If provenance metadata overhead is > 10% of post-compaction context, it may contribute to more frequent compaction, creating a feedback loop.
   - Recommendation: Measure the token count of forge metadata as a fraction of total post-compaction context. If > 10%, flag as a finding.

## Alternative Approaches if Primary Fails

| If This Fails | Because Of | Switch To | Cost of Switching |
| --- | --- | --- | --- |
| No compaction events fire (tasks too short) | L1-L3 resolve in < 128K tokens | Lower compaction trigger to 50K-80K; add more complex retry scenarios; use verbose tool outputs | 2-4 hours task redesign |
| Inner execution layer is fully opaque | run_queue.py does not expose API-level compaction | Session transcript post-hoc analysis (Approach 3) or simulated compaction (Approach 2) | 4-8 hours to build transcript parser; reduced confidence |
| Artifact IDs lost in compaction summary | Claude's summarizer paraphrases structured identifiers | Custom compaction instructions to preserve IDs; or pre-compaction checkpointing to external store | 2-4 hours; may not work if summarizer ignores instructions |
| Reachability < 50% (backtracking trigger) | Compaction systematically breaks provenance chains | Assess partial mitigation: pre-compaction checkpointing of refs to external store; report as negative finding on RQ3 | Phase redesign; 1-2 days; may conclude with negative result |
| API compaction unavailable | Beta endpoint changes or becomes unavailable | Simulated compaction (Approach 2); reduced confidence | 2-4 hours; weaker claim |

**Decision criteria for backtracking:** If provenance reachability drops below 50% across 3+ tasks with no clear mitigation path (pre-compaction checkpointing, custom instructions), this triggers the contractual stop/rethink condition: "Compaction grounding proves too brittle to preserve meaningful return paths." Report as a negative finding on RQ3 and assess whether partial mitigation is viable.

## Caveats and Alternatives

### Self-Critique

1. **Assumption that may be wrong:** I assume the Claude API `compact_20260112` endpoint provides sufficient observability for measuring provenance survival. In practice, the compaction summary is a free-form text block, and reconstructing which specific artifacts were preserved vs lost from that text may be ambiguous. The "three-tier ref classification" depends on being able to compare pre and post compaction content -- but the post-compaction content may be a summary that does not structurally correspond to individual pre-compaction artifacts.

2. **Alternative approach dismissed too quickly:** Factory.ai's probe-based evaluation (recall probes, artifact probes, continuation probes, decision probes) is a more sophisticated measurement of what survives compaction than BFS reachability on a DAG. Probes test whether the agent can actually USE the information that survived, not just whether refs resolve. However, probe-based evaluation requires designing agent-specific probes and running additional LLM calls to test them, which significantly increases cost and complexity. For Phase 4's scope (structural measurement, not behavioral evaluation), DAG reachability is the appropriate starting point. Probes could be added as a Phase 5 extension if structural reachability proves insufficient.

3. **Understated limitation:** The entire measurement assumes that forge artifacts and their source_refs exist in the LLM's context window before compaction. But if the task executor does not use forge tools natively (i.e., forge instrumentation is post-hoc, not real-time), then forge artifacts are never IN the context window -- they exist only in the external data store. In this case, LLM compaction cannot destroy forge refs because they were never in the compactable content. This would make the reachability measurement trivially 1.0 (nothing to compact), which is correct but uninteresting. The more interesting question -- do forge refs help the agent RECOVER information after compaction? -- requires a behavioral evaluation that is beyond Phase 4's structural measurement scope.

4. **Simpler method overlooked:** Rather than building a full compaction instrumentation pipeline, a simpler approach would be to take the existing Phase 2 non-compacted chamber data, programmatically delete the oldest 50-70% of artifacts (simulating compaction), and measure reachability on the pruned DAG. This gives an analytical prediction of how reachability degrades under different compaction ratios, without requiring any LLM API calls. The limitation is that real compaction is not uniform deletion -- it is LLM-generated summarization that may preserve some information while losing other. But the analytical prediction provides a lower bound on reachability (random deletion is worse than intelligent summarization) that complements empirical measurement.

5. **Specialist disagreement:** A data provenance researcher might argue that BFS reachability is too coarse a metric -- it treats all refs equally, but some refs are more causally important than others (Phase 2 noted the over-referencing problem where source_refs point to ALL upstream artifacts). A weighted reachability metric that prioritizes causal refs over structural refs would be more informative. The response: weighted reachability requires knowing which refs are causal, which is not currently tracked (source_refs are structural). Adding causal provenance tracking is a design change, not a measurement change. Phase 4 should measure what exists (structural refs) and report the limitation.

## Sources

### Primary (HIGH confidence)

- [Compaction - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/compaction) -- Technical specification of `compact_20260112` strategy, `pause_after_compaction`, `compaction` content block, trigger configuration
- [How Claude Code works - Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works) -- Three-layer compaction design: microcompaction, auto-compaction, manual compaction
- MockLM experiment results (tools/experiment_results.json) -- Controlled-condition ceiling: reachability=1.0, compression=87%
- Phase 2 baseline data (data/baselines/baseline-report.json) -- Non-compacted real-data baseline: reachability=1.0, compression=1.18x
- Phase 3 campaign data (data/campaign/campaign-report.json) -- Detection rates for regression comparison
- Compaction characterization (docs/compaction-characterization.md) -- Queue-worker layer has NO LLM compaction; inner execution layer UNCHARACTERIZED

### Secondary (MEDIUM confidence)

- [Evaluating Context Compression for AI Agents - Factory.ai](https://factory.ai/news/evaluating-compression) -- Probe-based evaluation framework for measuring information survival through compression
- [Building an internal agent: Context window compaction - Lethain](https://lethain.com/agents-context-compaction/) -- Practical compaction patterns; "Compaction destroys specifics"
- [Compaction vs Summarization - Morph](https://www.morphllm.com/compaction-vs-summarization) -- Deletion-based (verbatim) vs summarization-based (lossy) compaction distinction
- [Understanding and Improving Information Preservation in Prompt Compression - arXiv:2503.19114](https://arxiv.org/html/2503.19114) -- Reconstruction-based measurement of information preservation
- [Context compression - Google ADK](https://google.github.io/adk-docs/context/compaction/) -- Alternative compaction framework with configurable summarizer
- [The Fundamentals of Context Management and Compaction in LLMs - Kargar 2026](https://kargarisaac.medium.com/the-fundamentals-of-context-management-and-compaction-in-llms-171ea31741a2) -- Overview of compaction fundamentals

### Tertiary (LOW confidence)

- [Compaction: The Missing Design Principle - Bermudez 2026](https://medium.com/data-science-collective/compaction-the-missing-design-principle-for-scalable-llm-applications-3e9c831a72e0) -- Design patterns for compaction
- [Claude Opus 4.6 Introduces Adaptive Reasoning and Context Compaction - InfoQ](https://www.infoq.com/news/2026/03/opus-4-6-context-compaction/) -- 1M context window reduces compaction frequency by 15%
- [Inside Claude Code's Compaction System - Decode Claude](https://decodeclaude.com/compaction-deep-dive/) -- Community analysis of Claude Code compaction internals

## Metadata

**Confidence breakdown:**

- Mathematical framework: HIGH -- BFS reachability, SHA-256 hash comparison, bootstrap CI are well-established methods applied to well-defined metrics. The three-tier ref classification is novel but straightforward.
- Standard approaches: MEDIUM -- The recommended approach (Claude API compaction with instrumented snapshots) depends on API behavior that has not been tested in this project. The API mechanism is well-documented, but integration with forge artifacts is untested.
- Computational tools: HIGH -- networkx, anthropic SDK, hashlib are mature. Computational costs are negligible (graph analysis on small DAGs).
- Validation strategies: MEDIUM -- Pre/post compaction comparison is sound in principle, but the practical challenge of capturing clean pre-compaction snapshots at the correct moment is untested.
- Compaction behavior predictability: LOW -- How much information survives compaction, whether artifact IDs are preserved in summaries, and whether custom instructions can control the summarizer are all empirically unknown until tested.

**Research date:** 2026-03-16
**Valid until:** Compaction API behavior may change (beta endpoint). Core measurement methodology (BFS reachability, hash comparison) is stable indefinitely. Re-check Claude API compaction docs if project pauses > 3 months.
