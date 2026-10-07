# Phase 2: Integration and Baseline Establishment - Research

**Researched:** 2026-03-16
**Domain:** Agent runtime instrumentation / baseline measurement methodology / context management characterization
**Confidence:** MEDIUM

## Summary

Phase 2 bridges the gap between the MockLM proof-of-concept (103 passing tests, 100% provenance, 6/6 violations, 87% compression) and real-agent validation on Zarathustra/OpenClaw. The phase has four deliverables: (1) forge tool integration via adapter pattern, (2) characterization of Zarathustra's compaction mechanism, (3) uninstrumented baseline on a real task set, and (4) structured-logging intermediate baseline on the same task set. The central technical risk is whether Zarathustra's compaction is transparent enough for forge to attach meaningful `source_refs` -- research indicates it is partially transparent with viable hook points, though the `session:compacted` event hook was requested but not implemented upstream.

The recommended integration approach follows the existing `primordial_rlm_bridge.py` adapter pattern: subclass or wrap the Zarathustra/OpenClaw agent runtime to intercept iteration turns, subcalls, and compaction events, registering each as a forge chamber artifact with typed absence states and provenance refs. For the compaction characterization, OpenClaw's compaction operates at the prompt-assembly layer (splitting message history into old/recent, summarizing old via an LLM call, storing the summary as a JSONL transcript entry). This is semi-transparent: the pre-compaction message history and post-compaction summary are both accessible in the session JSONL, but no runtime callback exposes the compaction event to external tools in real time. The integration adapter must detect compaction by monitoring session transcript entries or by wrapping the compaction codepath directly.

**Primary recommendation:** Build a `PrimordialOpenClawAdapter` following the `PrimordialRLM` bridge pattern. Intercept at three points: (1) per-turn via the agent loop (iteration registration), (2) per-tool-call (subcall registration), (3) at compaction via either transcript monitoring or direct codepath wrapping. For the structured-logging baseline, use `opentelemetry-api` + `opentelemetry-sdk` with custom spans rather than GenAI auto-instrumentation (which targets specific LLM client libraries, not custom agent runtimes). The task set must include at least 3-5 tasks that exceed 128K tokens of accumulated context to trigger genuine compaction events.

## Active Anchor References

| Anchor / Artifact | Type | Why It Matters Here | Required Action | Where It Must Reappear |
| --- | --- | --- | --- | --- |
| ref-mock-experiment (103 passing tests) | prior artifact | Integration must not break existing tests; MockLM results (100% provenance, 6/6 violations, 87% compression) are the ceiling against which real baselines are measured | Run all 103 tests after integration; compare baseline metrics against MockLM ceiling | plan, execution, verification |
| forge_nulls.py | carry-forward input | Contains TRANSITION_TABLE (64 entries), validate_transition(), AbsenceState enum -- foundation for typed absence during instrumentation | Import and use in adapter; do not modify | plan, execution |
| forge_chamber.py | carry-forward input | create_chamber(), register_stage(), seal_chamber(), validate_chamber() -- chamber lifecycle for artifact registration | Import and use in adapter | plan, execution |
| forge_trace_codec.py | carry-forward input | encode_trace(), decode_trace(), verify_trace() -- trace compression and round-trip verification | Use for baseline compression measurements | plan, execution |
| forge_reversible_summary.py | carry-forward input | create_summary_view() -- summary creation with source_refs | Use for compaction artifact registration | plan, execution |
| primordial_rlm_bridge.py | carry-forward input | PrimordialRLM class -- existing adapter pattern to replicate for OpenClaw | Architectural template; replicate pattern, do not copy code | plan |
| vanilla_baseline.py | carry-forward input | Measurement methodology for uninstrumented baseline -- scenario structure (A/B/C), _analyze_trajectory() | Extend methodology to real tasks; do not use MockLM scenarios | plan |

**Missing or weak anchors:**
- **Zarathustra identity:** "Zarathustra" does not appear as a public project name. Web search finds no project by this name. The project charter and roadmap use "Zarathustra/OpenClaw" as the target runtime. Research proceeds assuming the target is OpenClaw (or a custom configuration thereof). If "Zarathustra" is a private fork or internal agent, the integration points may differ from stock OpenClaw. This must be clarified before implementation.
- **Real-task corpus:** Not yet defined. The contract identifies this as a gap. Research below provides design criteria but cannot select specific tasks without knowing the target domain.

## Conventions

| Choice | Convention | Alternatives | Source |
| --- | --- | --- | --- |
| Absence states | 8 canonical states per TRANSITION_TABLE in forge_nulls.py | 10-state (with timed_out, interrupted) | Phase 1 decision CC-002 |
| State field name | `state` (not `absence_state`) | Legacy `absence_state` via normalize_absent_object() | forge_nulls.py convention |
| Deprecated alias | `pruned` maps to `pruned_recoverable` | N/A | forge_nulls.py |
| Artifact ID format | `artifact:<runtime>:<run_id>:<type>:<index>:r<revision>` | Free-form string | primordial_rlm_bridge.py pattern |
| Chamber ID format | `chamber:<runtime>:<run_id>:v1` | Free-form string | primordial_rlm_bridge.py pattern |
| Compression metric | `compression_ratio = encoded_size / original_size` (forge trace codec) | N/A | forge_trace_codec.py |
| Overhead metric | `vs_vanilla_pct = (forge_size - vanilla_size) / vanilla_size * 100` | absolute_overhead_pct | primordial_rlm_bridge.py |
| Compaction (forge) | Lossless structural dedup via SHA-256 hash-verified encode/decode | N/A | forge_trace_codec.py |
| Compaction (LLM) | Lossy semantic summarization by the LLM runtime | N/A | OpenClaw docs |
| Provenance reachability | BFS/DFS fraction of artifacts reaching root | N/A | primordial_rlm_bridge.py compute_reversibility_score() |

**CRITICAL: "Compaction" has two distinct meanings in this project. Forge trace codec compression (lossless, hash-verified) is NEVER conflated with LLM context-window compaction (lossy, semantic). All measurements must specify which layer is being measured.**

## Mathematical Framework

### Key Equations and Starting Points

| Equation | Name/Description | Source | Role in This Phase |
| --- | --- | --- | --- |
| reachability_fraction = reachable_artifacts / total_artifacts | Provenance reachability | primordial_rlm_bridge.py | Primary provenance metric for baseline measurement |
| compression_ratio = encoded_size / original_size | Trace codec efficiency | forge_trace_codec.py | Compression metric for baseline measurement |
| vs_vanilla_pct = (forge_size - vanilla_size) / vanilla_size * 100 | Overhead vs vanilla | primordial_rlm_bridge.py | Overhead metric for integration cost assessment |
| detection_rate = violations_detected / violations_present | Violation detection | New for baselines | Measures what each baseline tier catches (expected: 0 for uninstrumented, partial for structured logging, full for forge) |

### Required Techniques

| Technique | What It Does | Where Applied | Standard Reference |
| --- | --- | --- | --- |
| Adapter pattern (subclass/wrapper) | Wraps agent runtime to intercept lifecycle events without modifying source | Integration adapter for OpenClaw | primordial_rlm_bridge.py (PrimordialRLM subclass pattern) |
| JSONL transcript parsing | Reads OpenClaw session files to extract compaction events and message history | Compaction characterization | OpenClaw session management docs |
| OpenTelemetry manual instrumentation | Creates custom spans around agent operations for structured logging baseline | Structured-logging baseline | opentelemetry-api + opentelemetry-sdk Python packages |
| Bootstrap confidence intervals | Quantifies uncertainty on small-sample metrics | Baseline metric reporting | numpy resampling (see METHODS.md Method 6) |

### Approximation Schemes

| Approximation | Small Parameter | Regime of Validity | Error Estimate | Alternatives if Invalid |
| --- | --- | --- | --- | --- |
| Token count estimation via character heuristic | chars/4 approximation | Short to medium messages; breaks for code, JSON, non-ASCII | Can be off by 20-40% for structured content | Use tiktoken or model-specific tokenizer for exact counts |
| Task complexity proxy via accumulated token count | Using total tokens as proxy for "task complexity" | Linear scaling of context usage with task difficulty | Does not account for branching, revision cycles, or tool-call density | Use multi-dimensional complexity vector (tokens + tool calls + revisions + depth) |
| Single-run baseline | Assuming one run is representative | Low-variance tasks with deterministic tool calls | High variance for tasks with nondeterministic LLM behavior | Run each task N>=5 times; report distributions, not single values |

## Standard Approaches

### Approach 1: Adapter-Pattern Integration (RECOMMENDED)

**What:** Create `PrimordialOpenClawAdapter` that wraps the OpenClaw agent runtime, intercepting lifecycle events (iteration turns, tool calls, compaction events) and registering each as a forge chamber artifact. Does NOT modify OpenClaw source code.

**Why standard:** This is the established pattern in the codebase -- `PrimordialRLM` already does exactly this for the RLM runtime. The adapter pattern keeps forge tools decoupled from the target runtime, allowing the same forge protocol to instrument different agent architectures.

**Track record:** PrimordialRLM successfully instruments 3 scenarios (linear, tree recursion, compaction) with full provenance and compression. 103 tests validate the pattern.

**Key steps:**

1. **Identify OpenClaw lifecycle hooks.** Map the equivalent of RLM's `_completion_turn()`, `_subcall()`, and `_compact_history()` in OpenClaw's agent loop. OpenClaw's agent runtime runs a loop of: assemble context -> LLM call -> parse response -> execute tool calls -> persist transcript. Each of these is an interception point.

2. **Build the adapter class.** Following the PrimordialRLM pattern:
   - On agent turn start: create chamber if first turn, track iteration index
   - On each LLM response: call `create_v1_stage_artifact()` with output content, build source_refs to previous iterations and subcalls
   - On each tool call: register as subcall artifact with parent ref to current iteration
   - On compaction trigger: register compaction artifact with source_refs to all compacted iteration artifacts, capture pre-compaction and post-compaction message counts

3. **Characterize compaction.** Before building the full adapter, investigate OpenClaw's compaction codepath:
   - Read the session JSONL after a compaction event to identify the compaction summary entry format
   - Determine whether the adapter can wrap the compaction function directly or must detect compaction post-hoc from transcript changes
   - Assess whether `source_refs` can meaningfully point to pre-compaction artifacts (are their IDs still resolvable after compaction?)

4. **Validate regression.** Run all 103 existing forge tests to confirm the adapter does not break forge tool internals. Then run a smoke test on a simple OpenClaw task (e.g., "write hello world") to confirm the adapter produces valid chambers.

5. **Measure baselines.** Run the defined task set with: (a) uninstrumented OpenClaw (vanilla), (b) OpenClaw + OpenTelemetry structured logging, (c) OpenClaw + forge adapter. Collect metrics for each.

**Known difficulties at each step:**

- Step 1: OpenClaw's agent loop is TypeScript, not Python. The adapter may need to operate at the session JSONL level (post-hoc analysis) rather than wrapping Python functions. Alternatively, if OpenClaw exposes a Python SDK or the project uses a Python agent framework on top of OpenClaw, direct interception is possible.
- Step 2: OpenClaw's nondeterministic LLM responses mean artifact IDs and source_refs must be generated based on observed output, not pre-scripted responses. The adapter must handle malformed or unexpected outputs gracefully.
- Step 3: The `session:compacted` hook was requested (issue #11799) but closed as "not planned." Compaction detection must use alternative methods.
- Step 5: Reproducibility is limited by LLM nondeterminism. Multiple runs per task are needed.

### Approach 2: Session Transcript Post-Hoc Analysis (FALLBACK)

**What:** Instead of wrapping the agent runtime in real time, analyze OpenClaw session JSONL transcripts after task completion. Parse entries to reconstruct the agent's execution history, identify compaction events, and compute metrics.

**When to switch:** If real-time interception proves infeasible (e.g., OpenClaw's TypeScript runtime cannot be instrumented from Python, or the target "Zarathustra" runtime has no Python interface).

**Tradeoffs:** Loses real-time validation (forge cannot reject violations as they occur -- only detect them post-hoc). Gains simplicity (no runtime coupling) and works regardless of the agent's implementation language. The post-hoc approach is sufficient for baseline measurement but insufficient for Phase 3's fault injection (which requires runtime interception).

### Approach 3: Prompt-Layer Interception (EMERGENCY FALLBACK)

**What:** If compaction is fully opaque (no JSONL evidence, no transcript markers), intercept at the prompt assembly layer -- capture the full message history before each LLM call and detect when the history shrinks (indicating compaction occurred).

**When to switch:** If Approach 1 cannot detect compaction events through either wrapping or transcript analysis.

**Tradeoffs:** Most invasive; requires inserting forge logic into the prompt construction pipeline. Provides the most complete view of what the LLM actually sees, but tightly couples forge to the runtime's prompt format.

### Anti-Patterns to Avoid

- **Modifying OpenClaw source code directly:** Breaks on upstream updates; makes the integration non-portable. Always use adapter/wrapper patterns.
- **Using `_fake_count_tokens` for real measurements:** This was appropriate for MockLM tests but is forbidden for real baseline measurements. Real token counts must come from actual tokenizer or runtime estimates.
- **Assuming compaction triggers at a fixed token threshold:** OpenClaw's compaction threshold is configurable (`autoCompactThreshold`, `softThresholdTokens`) and may vary by session. The adapter must detect actual compaction events, not predict them.
- **Running only short tasks and claiming the baseline is complete:** The contract explicitly forbids fp-short-tasks. At least some tasks must exceed 128K tokens of accumulated state.

## Existing Results to Leverage

### Established Results (DO NOT RE-DERIVE)

| Result | Exact Form | Source | How to Use |
| --- | --- | --- | --- |
| MockLM provenance reachability | 1.0 (100%) across scenarios A, B, C | experiment_results.json | Cross-reference ceiling for real baseline measurements |
| MockLM violation detection | 6/6 (100%) on D1-D6 | experiment_results.json | Cross-reference ceiling; real baselines expected to show 0 detection (uninstrumented) |
| MockLM trace compression | 1.08-1.10x ratio (87-88% of original size) | experiment_results.json | Cross-reference anchor for real compression measurements |
| Vanilla baseline detection | 0/6 (0%) -- no invariant checks | vanilla_baseline_results.json | Expected floor for uninstrumented baseline |
| Vanilla reversibility | 0.0 across all scenarios | vanilla_baseline_results.json | Expected floor for uninstrumented provenance |
| Transition table | 64 entries (45 legal, 19 illegal) | forge_nulls.py TRANSITION_TABLE | Use for absence state assignment during instrumentation; do not re-derive |
| validate_transition() | Pure function: (from_state, to_state) -> bool | forge_nulls.py | Use for runtime validation in adapter |
| PrimordialRLM adapter pattern | Subclass with chamber lifecycle management | primordial_rlm_bridge.py | Architectural template for OpenClaw adapter |
| compute_reversibility_score() | BFS-based provenance reachability | primordial_rlm_bridge.py | Reuse directly for baseline measurements |
| compute_overhead() | vs_vanilla_pct and compression_ratio computation | primordial_rlm_bridge.py | Reuse directly for overhead measurements |

**Key insight:** The entire forge tool suite (nulls, chamber, trace codec, reversible summary, v1 bridge) is carry-forward input. Phase 2 builds an adapter ON TOP of these tools. No forge tool code should be modified in Phase 2 -- only new adapter code and measurement scripts are created.

### Useful Intermediate Results

| Result | What It Gives You | Source | Conditions |
| --- | --- | --- | --- |
| OpenClaw compaction mode: semi-transparent | Compaction writes a summary entry to session JSONL; pre-compaction messages are replaced in active context but may persist in transcript | Web research (OpenClaw docs, DeepWiki) | Stock OpenClaw configuration; custom forks may differ |
| OpenClaw compaction configuration | `agents.defaults.compaction.mode`, `threshold`, `autoCompactThreshold`, `model` settings | OpenClaw docs | Available in openclaw.json |
| OpenClaw memory flush before compaction | Silent turn writes durable notes to memory/YYYY-MM-DD.md before compaction | OpenClaw docs | Enabled by default; softThresholdTokens configurable |
| OpenClaw identifier policy | `identifierPolicy: "strict"` preserves opaque identifiers during compaction summarization | OpenClaw docs | Default behavior; can be configured to "off" or "custom" |
| OpenClaw session JSONL structure | Tree-structured entries with id + parentId; branch_summary entry type for compaction | OpenClaw session management docs | Standard format; ~/.openclaw/sessions/ or agent-specific location |
| `tool_result_persist` hook | Synchronous hook that transforms tool results before transcript persistence | OpenClaw hook system | Available for modifying tool result entries; cannot intercept compaction directly |

### Relevant Prior Work

| Paper/Result | Authors | Year | Relevance | What to Extract |
| --- | --- | --- | --- | --- |
| Lossless Claw (LCM plugin) | Martian Engineering | 2025-2026 | Alternative compaction approach for OpenClaw: DAG-based summarization preserving every message | Architectural comparison; validates that compaction interception is technically feasible |
| Lethain compaction patterns | Will Larson | 2026 | Documents how production agents handle compaction; identifies what compaction destroys | Specific failure modes: "Compaction destroys specifics: file paths, exact values, config details, reasoning chains" |
| Block Engineering testing pyramid | Block Inc. | 2025 | Testing pyramid for AI agents; identifies the mock-to-real gap | Staged validation approach: unit tests -> recorded playback -> live short -> live long |
| OpenTelemetry GenAI semantic conventions | OTel GenAI SIG | 2025-2026 | Draft standard for agent observability spans | Span naming conventions for structured logging baseline (gen_ai.agent.invoke, etc.) |

## Computational Tools

### Core Tools

| Tool | Version/Module | Purpose | Why Standard |
| --- | --- | --- | --- |
| pytest | 8.x | Test runner for regression tests (103 existing) and new integration tests | Already in use; all forge tests are pytest-based |
| forge_nulls.py | Phase 1 output | Typed absence enforcement, state validation | Core forge tool; carry-forward input |
| forge_chamber.py | Phase 1 output | Chamber lifecycle (create, register, seal, validate) | Core forge tool; carry-forward input |
| forge_trace_codec.py | Phase 1 output | Trace compression and round-trip verification | Core forge tool; carry-forward input |
| forge_reversible_summary.py | Phase 1 output | Grounded summary creation with source_refs | Core forge tool; carry-forward input |

### Supporting Tools

| Tool | Purpose | When to Use |
| --- | --- | --- |
| opentelemetry-api + opentelemetry-sdk | Manual span instrumentation for structured-logging baseline | BASE-02: creating custom spans around agent operations |
| opentelemetry-exporter-otlp-proto-grpc or -json | Exporting spans to file/collector for baseline analysis | BASE-02: persisting structured logging data |
| networkx | Provenance DAG construction and reachability analysis | Baseline provenance measurements |
| numpy | Bootstrap confidence intervals on metrics | Statistical reporting for baseline measurements |
| cProfile + tracemalloc | Overhead measurement (wall time and memory) | Measuring forge instrumentation cost |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
| --- | --- | --- |
| OpenTelemetry manual spans | Langfuse / Braintrust tracing | Third-party dependency; adds SaaS coupling for a research project. OTel is vendor-neutral. |
| Custom JSONL transcript parser | OpenClaw Python SDK (if it exists) | SDK would be cleaner but adds a dependency on OpenClaw's Python bindings. JSONL parsing is dependency-free. |
| Real-time adapter wrapping | Post-hoc transcript analysis | Post-hoc loses real-time validation but works regardless of runtime language. Try real-time first, fall back to post-hoc. |
| networkx for DAG analysis | Custom BFS implementation | networkx is overkill for small graphs but well-tested. Custom BFS is simpler but risks bugs. Use networkx for correctness, custom for performance if needed. |

### Computational Feasibility

| Computation | Estimated Cost | Bottleneck | Mitigation |
| --- | --- | --- | --- |
| Run 103 existing forge tests | < 10 seconds | None | Already fast |
| Single OpenClaw task (uninstrumented) | 30s - 10min per task | LLM API latency + token cost | Budget $0.50-2.00 per task for Claude/GPT-4 class |
| Single OpenClaw task (instrumented) | 30s - 10min + < 5% forge overhead | LLM API latency | Forge overhead is negligible vs LLM latency |
| Full task set (15-20 tasks, 2 baselines) | 2-4 hours including API latency | LLM API cost | Budget $15-40 for full evaluation suite |
| Tasks triggering compaction (128K+ tokens) | 10-30 minutes per task | Context window fill time | Need 3-5 such tasks minimum; most expensive items |
| Provenance DAG analysis (per chamber) | < 1 second | None | Exact BFS/DFS on small graphs |
| Bootstrap CI computation | < 100ms | None | 10000 resamples on small arrays |

**Installation / Setup:**
```bash
# Core (already installed from Phase 1)
pip install pytest hypothesis numpy networkx

# New for Phase 2: OpenTelemetry for structured-logging baseline
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc

# Optional: for exact token counting (replace character heuristic)
pip install tiktoken
```

## Validation Strategies

### Internal Consistency Checks

| Check | What It Validates | How to Perform | Expected Result |
| --- | --- | --- | --- |
| 103 existing tests pass after integration | Adapter does not break forge tools | `pytest tools/` | All 103 pass (301 if including Phase 1 additions) |
| Chamber validation after each task | Structural integrity of instrumented chambers | `validate_chamber(chamber)` returns `[]` | Zero validation errors |
| Trace round-trip verification | Encode/decode losslessness on real data | `verify_trace(encode_trace(chamber), chamber)` | `{valid: True, hash_match: True, content_match: True}` |
| Provenance DAG acyclicity | No circular refs (which would indicate a bug) | networkx.is_directed_acyclic_graph(dag) | True |
| Absence state validity | All states assigned during instrumentation are canonical | Check each artifact's output_state against V1_ABSENCE_STATES | All states are members of V1_ABSENCE_STATES |

### Known Limits and Benchmarks

| Limit | Parameter Regime | Known Result | Source |
| --- | --- | --- | --- |
| MockLM ceiling (provenance) | Deterministic, no real compaction | 1.0 (100% reachability) | experiment_results.json |
| MockLM ceiling (violations) | Deterministic, scripted D1-D6 | 6/6 detected | experiment_results.json |
| MockLM ceiling (compression) | 3-5 stage chambers | 1.08-1.10x ratio | experiment_results.json |
| Vanilla floor (provenance) | No forge instrumentation | 0.0 (no provenance structure) | vanilla_baseline_results.json |
| Vanilla floor (violations) | No invariant checks | 0/6 detected | vanilla_baseline_results.json |

### Numerical Validation

| Test | Method | Tolerance | Reference Value |
| --- | --- | --- | --- |
| Compression ratio consistency | Run encode_trace() on same chamber twice | Exact match (deterministic) | Same ratio both times |
| Provenance reachability consistency | Run compute_reversibility_score() on same chamber twice | Exact match | Same fraction both times |
| Overhead measurement stability | Run same task 5 times, measure forge overhead | Coefficient of variation < 30% | < 10% median overhead |
| Task set token count | Verify tasks claiming 128K+ tokens actually accumulate that many | Within 20% of claimed count | >= 100K actual tokens |

### Red Flags During Computation

- If the adapter rejects > 20% of real agent outputs as malformed, the adapter's parsing logic is too strict for real LLM output -- loosen validation, do not blame the agent
- If provenance reachability on instrumented runs is 0% (no refs resolve), the adapter is not correctly building source_refs -- check artifact ID generation
- If compression ratio is > 2.0x (encoded larger than original), the trace codec's dedup is failing on the real data format -- inspect shared_structures count
- If all tasks complete without triggering compaction, the tasks are too short -- extend task complexity or lower the compaction threshold
- If the structured-logging baseline detects the same violations as forge, the structured logging is doing more than expected -- verify it does not include forge-specific checks
- If uninstrumented baseline shows non-zero provenance, something is wrong with the measurement methodology -- vanilla OpenClaw should have zero structured provenance

## Common Pitfalls

### Pitfall 1: MockLM-to-Real-LLM Integration Gap

**What goes wrong:** All 103 tests pass on MockLM but the adapter fails on real LLM output because real responses have variable formatting, unexpected structures, or timing-dependent behaviors.
**Why it happens:** MockLM returns deterministic, pre-scripted responses. Real LLMs produce nondeterministic output that may not match the adapter's parsing expectations.
**How to avoid:** Staged validation: (1) verify 103 tests still pass with adapter installed, (2) run adapter on 3-5 simple tasks with real LLM, (3) inspect chambers manually for structural correctness before running full baseline suite.
**Warning signs:** ForgeNullError or ForgeChamberError exceptions on outputs that are actually valid but formatted differently than expected.
**Recovery:** Loosen adapter parsing; add normalization layer between raw agent output and forge artifact construction.

### Pitfall 2: Compaction Detection Failure

**What goes wrong:** The adapter fails to detect when OpenClaw triggers compaction, so compaction events are not recorded as forge artifacts. This makes Phase 4 impossible.
**Why it happens:** The `session:compacted` hook was requested but not implemented. Compaction is an internal operation with limited external visibility.
**How to avoid:** Implement multiple detection strategies: (1) monitor session JSONL for compaction summary entries, (2) track message history length and detect sudden decreases, (3) if possible, wrap the compaction codepath directly. Test each strategy on a task known to trigger compaction.
**Warning signs:** Chamber has no compaction artifacts despite the session JSONL showing a compaction summary entry.
**Recovery:** Fall back to post-hoc transcript analysis rather than real-time detection.

### Pitfall 3: Task Set Too Easy (fp-short-tasks)

**What goes wrong:** All tasks complete within the context window without triggering compaction. Baselines look good but are meaningless for Phase 4.
**Why it happens:** Natural tendency to design manageable, quick-running tasks. Tasks that accumulate 128K+ tokens of context require 20-60 minutes of sustained agent activity.
**How to avoid:** Pre-validate tasks by running them and checking accumulated token counts. Configure OpenClaw with a lower compaction threshold for testing (e.g., `autoCompactThreshold: 0.50` to trigger compaction earlier). Include at least one multi-file refactoring or codebase analysis task that requires extensive tool use.
**Warning signs:** Zero compaction events in any baseline run.
**Recovery:** Add longer tasks or lower the compaction threshold. Do NOT claim baselines are complete without compaction-triggering tasks.

### Pitfall 4: Straw-Man Baseline (Pitfall 5 from project research)

**What goes wrong:** Comparing forge against vanilla (zero invariant checks) produces trivially favorable results. Every difference is attributable to "anything vs nothing," not to forge's specific value.
**Why it happens:** Vanilla OpenClaw has no structural validation or provenance tracking by design.
**How to avoid:** The structured-logging baseline (BASE-02) is specifically designed to address this. It adds schema validation and structured event recording WITHOUT typed absence or provenance. This isolates forge's differential value.
**Warning signs:** All reported gains come from comparing forge vs vanilla; the structured-logging baseline is identical to vanilla.
**Recovery:** Ensure the structured-logging baseline includes at least: (1) span-based event recording for each agent turn and tool call, (2) basic schema validation on LLM responses (JSON structure present, required fields non-null), (3) timing and token count instrumentation. This provides a reasonable "any validation" baseline.

### Pitfall 5: Non-Reproducible Baselines

**What goes wrong:** Baseline metrics vary wildly between runs due to LLM nondeterminism, making differential comparison meaningless.
**Why it happens:** Real LLMs produce different outputs on the same prompt. Task completion paths, tool call sequences, and compaction trigger points all vary.
**How to avoid:** Run each task N >= 5 times per baseline tier. Report distributions (median, IQR) not single values. Use bootstrap CI for uncertainty quantification. For reproducibility, log the LLM API response for each run so results can be audited.
**Warning signs:** Coefficient of variation > 50% on any metric across runs of the same task.
**Recovery:** Increase N; stratify results by task type; consider using temperature=0 for more deterministic runs (noting this in methodology).

## Level of Rigor

**Required for this phase:** Controlled measurement with reproducible methodology

**Justification:** Phase 2 establishes baselines that all subsequent phases compare against. If baselines are unreliable, all downstream measurements are suspect. The rigor level is "measurement science" -- controlled conditions, multiple runs, statistical uncertainty, reproducible methodology -- not formal proof.

**What this means concretely:**

- Each task must be run N >= 5 times per baseline tier for statistical stability
- All metrics must be reported with bootstrap 95% confidence intervals
- The task set design must be documented with inclusion/exclusion criteria
- Compaction events must be verified (not just assumed) by checking session transcripts
- The structured-logging baseline must provide genuine validation, not just event recording
- All raw data (session transcripts, chambers, measurements) must be persisted for audit

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| Manual session inspection | Automated session transcript parsing | OpenClaw JSONL format (2025) | Enables post-hoc compaction detection without runtime hooks |
| Opaque compaction (no visibility) | Semi-transparent compaction with JSONL persistence and identifier preservation | OpenClaw identifierPolicy (2025-2026) | Makes forge integration feasible; identifiers survive compaction summarization |
| No standard agent observability | OpenTelemetry GenAI semantic conventions (draft) | 2025-2026 | Provides span naming standards for structured-logging baseline |
| Single-baseline comparison | Three-tier baseline (vanilla, structured logging, forge) | Project design (PITFALLS.md Pitfall 5) | Isolates forge-specific value from "any validation" value |

**Superseded approaches to avoid:**

- **Full W3C PROV instrumentation:** Overkill for single-runtime measurement. Forge's native `parent_id` + `source_refs` is sufficient. PROV export can be added later if needed for RQ4 (generality).
- **OpenTelemetry auto-instrumentation for GenAI:** These packages target specific LLM client libraries (openai, google-genai). The agent runtime needs manual instrumentation with custom spans.
- **Flowcept decorator-based provenance:** Designed for distributed HPC workflows; wrong abstraction level for a single-agent session.

## Open Questions

1. **What exactly is "Zarathustra"?**
   - What we know: The project charter and roadmap consistently say "Zarathustra/OpenClaw." Web search finds no public project named "Zarathustra" in the agent runtime space.
   - What's unclear: Whether Zarathustra is a private fork of OpenClaw, a custom configuration, a different name for the same system, or a distinct internal tool.
   - Impact on this phase: If Zarathustra has different internals than stock OpenClaw, the compaction characterization and hook point analysis may not apply.
   - Recommendation: **Clarify with the user before implementation.** Proceed with OpenClaw assumptions for planning, but flag that integration code may need adjustment.

2. **Can the adapter intercept compaction in real time?**
   - What we know: OpenClaw's `session:compacted` hook was requested but not implemented (issue #11799, closed "not planned"). `tool_result_persist` hook exists but handles tool results, not compaction. A `session_before_compact` hook exists in the Pi extension API but is not exposed to workspace hooks.
   - What's unclear: Whether wrapping the compaction function directly (TypeScript source modification or monkey-patching) is feasible, or whether post-hoc transcript analysis is the only viable approach.
   - Impact on this phase: Real-time detection enables forge to record `pruned_recoverable` states BEFORE compaction occurs. Post-hoc detection can only reconstruct what happened after the fact.
   - Recommendation: Try three approaches in order: (1) check if there's a Python-accessible compaction event, (2) monitor JSONL transcript for compaction entries between turns, (3) detect compaction by observing message history length decreases. Document which approach works.

3. **What tasks should be in the real-task corpus?**
   - What we know: Tasks must be "mixed autonomous" (variety of complexity), include some that trigger 128K+ token accumulation, and cover recursive subcall chains. The project contract identifies this as a gap.
   - What's unclear: Target domain (coding tasks? general agent tasks? multi-tool workflows?), specific task sources (SWE-bench? Custom? Production logs?), minimum task count for statistical validity.
   - Impact on this phase: Task set design determines whether baselines are representative and whether compaction is triggered.
   - Recommendation: Design a task set with three tiers: (a) 5-7 short tasks (< 32K tokens, no compaction expected -- baseline calibration), (b) 5-7 medium tasks (32K-128K tokens, possible compaction -- stress test), (c) 3-5 long tasks (128K+ tokens, compaction required -- primary measurement targets). Source from real coding tasks that the agent would naturally encounter. Document inclusion criteria.

4. **How does OpenClaw's `identifierPolicy: "strict"` affect forge source_refs?**
   - What we know: This policy instructs the compaction summarizer to preserve opaque identifiers. If forge artifact IDs (e.g., `artifact:oc:run123:iter:0:r1`) appear in the context, the summarizer should preserve them.
   - What's unclear: Whether the policy reliably preserves artifact-style IDs, or whether it's tuned for shorter identifiers (file paths, URLs, commit hashes).
   - Impact on this phase: If identifiers survive compaction, forge `source_refs` may remain resolvable post-compaction. This is a positive signal for Phase 4.
   - Recommendation: Test with a task that includes forge artifact IDs in context, trigger compaction, and check whether the IDs survive in the summary. This is a key characterization datapoint for INTG-02.

## Alternative Approaches if Primary Fails

| If This Fails | Because Of | Switch To | Cost of Switching |
| --- | --- | --- | --- |
| Real-time adapter wrapping | OpenClaw runtime is TypeScript-only, no Python interception points | Post-hoc JSONL transcript analysis | MEDIUM -- need to build parser and reconstruct chambers from transcripts, lose real-time validation |
| Compaction detection via transcript monitoring | Compaction entries are not distinguishable in JSONL | Prompt-layer interception (monitor message history length) | MEDIUM -- more invasive, requires understanding prompt assembly |
| OpenTelemetry structured-logging baseline | OTel SDK adds too much complexity for a research baseline | Custom structured logging with JSON event records | LOW -- simpler, fewer dependencies, same measurement capability |
| Task set design targeting 128K+ tokens | No tasks naturally accumulate enough context | Lower compaction threshold in OpenClaw config (e.g., 50K tokens) | LOW -- config change; note in methodology that compaction threshold was lowered |
| Single adapter for all three baselines | Baselines require fundamentally different instrumentation approaches | Separate measurement scripts per baseline tier | LOW -- more code but cleaner separation of concerns |

**Decision criteria:**

- If the primary adapter approach produces zero valid chambers after 3 attempts on real tasks, switch to post-hoc transcript analysis
- If no compaction events are detected after running 3 tasks that should trigger compaction, investigate compaction threshold configuration before switching approaches
- If OpenTelemetry adds > 100ms per span (unlikely but possible with OTLP export), switch to custom JSON logging

## Task Set Design Criteria

This section provides guidance for the planner on designing the real-task corpus (an identified contract gap).

### Inclusion Criteria

| Criterion | Rationale | Minimum |
| --- | --- | --- |
| Coding tasks with tool use (file read/write, command execution) | Matches the agent's primary use case; generates structured provenance chains | 60% of task set |
| Tasks requiring multi-step reasoning (plan -> execute -> verify) | Exercises provenance chain depth (depth >= 2) | 50% of task set |
| Tasks with recursive subcalls (agent delegates to sub-agent or nested tool calls) | Tests provenance DAG branching, matches Scenario B pattern | 20% of task set |
| Tasks accumulating 128K+ tokens of context | Triggers genuine compaction events; satisfies fp-short-tasks guard | >= 3 tasks |
| Clean tasks (expected to succeed without errors) | Establishes false-positive baseline for violation detection | >= 5 tasks |

### Exclusion Criteria

| Criterion | Rationale |
| --- | --- |
| Tasks that complete in < 5 agent turns | Too short to generate meaningful provenance chains |
| Tasks requiring external services not available in test environment | Non-reproducible |
| Tasks with high sensitivity to LLM model version | Baseline measurements would not be comparable across runs |

### Task Complexity Tiers

| Tier | Token Range | Expected Compaction | Count | Purpose |
| --- | --- | --- | --- | --- |
| Short | < 32K | None | 5-7 | Calibration; establish metrics under simple conditions |
| Medium | 32K-128K | Possible (depends on threshold) | 5-7 | Stress test; exercise extended provenance chains |
| Long | 128K+ | Required (must trigger) | 3-5 | Primary measurement target; compaction survival anchor |

### Reproducibility Requirements

- Each task must have a fixed prompt template (parameterized, not free-form)
- Each task must have defined success criteria (how to know the agent completed it)
- Each task must be run N >= 5 times per baseline tier
- All session transcripts, chamber data, and measurements must be persisted
- LLM API responses should be logged for post-hoc audit

## Structured-Logging Baseline Design (BASE-02)

The structured-logging baseline must provide MORE than vanilla logging but LESS than forge instrumentation. It represents what a competent team would build with standard observability tools, without typed absence or provenance tracking.

### What It Must Include

| Feature | Implementation | Why |
| --- | --- | --- |
| Span-based event recording | OpenTelemetry spans around each agent turn and tool call | Standard observability practice |
| Basic schema validation | Check that LLM responses contain expected JSON structure | Catches malformed responses |
| Timing instrumentation | Start/end timestamps, duration per turn and tool call | Performance baseline |
| Token count tracking | Record input/output token counts per LLM call | Context budget monitoring |
| Error recording | Log exceptions, HTTP errors, timeout events | Failure detection baseline |

### What It Must NOT Include

| Feature | Why Excluded |
| --- | --- |
| Typed absence states | This is forge's specific contribution; including it defeats the purpose of the intermediate baseline |
| Provenance DAG / source_refs | This is forge's specific contribution |
| Hash-verified trace compression | This is forge's specific contribution |
| Violation detection (null discipline, ref validation) | This is forge's specific contribution |

### Expected Baseline Results

| Metric | Uninstrumented (Vanilla) | Structured Logging | Forge |
| --- | --- | --- | --- |
| Provenance reachability | 0.0 (no provenance) | 0.0 (no provenance DAG) | > 0 (forge builds DAG) |
| Violation detection | 0 (no checks) | Partial (schema validation catches malformed responses) | Full (typed absence + ref validation + null discipline) |
| Trace compression | N/A | N/A | Measured (expected 1.05-1.15x on real data) |
| Timing/token data | None | Full | Full (from adapter) |

## Caveats and Self-Critique

1. **Assumption about OpenClaw as target:** This research assumes "Zarathustra" is OpenClaw or closely related. If it is a fundamentally different system, the compaction characterization, hook point analysis, and JSONL parsing approach may not apply. The adapter pattern itself is generic, but the specific interception points are OpenClaw-specific.

2. **Compaction transparency may be overstated:** The research found that OpenClaw's compaction is "semi-transparent" based on documentation and issue discussions. The actual transparency in practice (especially for the specific version in use) has not been verified. The `session:compacted` hook not being implemented is a significant limitation.

3. **Structured-logging baseline design is a judgment call:** The line between "standard observability" and "forge-specific features" is somewhat arbitrary. Schema validation could be argued as a lightweight form of typed absence. The planner should document the exact boundary and justify it.

4. **Task set design criteria are preliminary:** Without knowing the specific domain (coding, general, multi-tool), the task set criteria are generic. The actual task selection requires understanding what Zarathustra/OpenClaw is typically used for.

5. **Statistical requirements may be expensive:** Running each task N >= 5 times across 3 baseline tiers with 15-20 tasks means 225-300 task executions. At $0.50-2.00 per task for LLM API costs, the full baseline suite could cost $100-600. This may need to be reduced by running fewer repetitions on short tasks (which have lower variance).

## Sources

### Primary (HIGH confidence)

- [OpenClaw Compaction Docs](https://docs.openclaw.ai/concepts/compaction) -- Official documentation on compaction mechanism, configuration, and behavior
- [OpenClaw Session Management](https://docs.openclaw.ai/reference/session-management-compaction) -- JSONL format, session structure, compaction entries
- primordial_rlm_bridge.py (local) -- Existing adapter pattern for RLM integration; architectural template for Phase 2
- experiment_results.json (local) -- MockLM experiment results; cross-reference ceiling
- vanilla_baseline_results.json (local) -- Vanilla baseline results; cross-reference floor
- forge_nulls.py (local) -- Transition table, validate_transition(), AbsenceState enum
- METHODS.md (project research) -- Recommended methods for all phases
- PITFALLS.md (project research) -- Five critical pitfalls with mitigations

### Secondary (MEDIUM confidence)

- [OpenClaw Context Overflow and Auto-Compaction (DeepWiki)](https://deepwiki.com/openclaw/openclaw/5.5-context-overflow-and-auto-compaction) -- Code flow analysis of compaction mechanism
- [session:compacted hook feature request (issue #11799)](https://github.com/openclaw/openclaw/issues/11799) -- Hook was requested but closed "not planned"; confirms limited compaction observability
- [Lossless Claw plugin](https://github.com/Martian-Engineering/lossless-claw) -- Alternative compaction approach; validates that compaction interception is technically feasible
- [OpenTelemetry AI Agent Observability blog](https://opentelemetry.io/blog/2025/ai-agent-observability/) -- Emerging standards for agent observability
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) -- Draft span conventions for LLM operations
- [Configurable compaction threshold (issue #10073)](https://github.com/openclaw/openclaw/issues/10073) -- Compaction threshold configuration options
- [OpenClaw Architecture Overview](https://ppaolo.substack.com/p/openclaw-system-architecture-overview) -- System architecture and agent runtime design

### Tertiary (LOW confidence)

- [Configurable early auto-compaction threshold (issue #30411)](https://github.com/openclaw/openclaw/issues/30411) -- Feature request; may not be implemented
- [OpenClaw Hooks docs](https://openclaw-ai.com/en/docs/automation/hooks) -- Hook system overview; some community sites, not official docs
- [OpenClaw Context Management blog](https://agi-xiaobai-no1.github.io/posts/context-management/) -- Community analysis; not verified against source code

## Metadata

**Confidence breakdown:**

- Mathematical framework: HIGH -- All metrics and equations are established in the existing codebase and project research. No new formalism needed.
- Standard approaches: MEDIUM -- The adapter pattern is well-established but OpenClaw-specific integration points are based on documentation review, not hands-on testing. The "Zarathustra" identity is unresolved.
- Computational tools: HIGH -- All tools (pytest, OTel, networkx, numpy) are mature, well-documented, and appropriate. Installation is straightforward.
- Validation strategies: HIGH -- Cross-reference against MockLM ceiling and vanilla floor is straightforward. Statistical methods (bootstrap CI) are well-established.
- Compaction characterization: MEDIUM -- Based on OpenClaw documentation and issue discussions, not source code inspection. Actual behavior may differ from documented behavior.
- Task set design: LOW -- Generic criteria without domain-specific task selection. Requires user input to finalize.

**Research date:** 2026-03-16
**Valid until:** Stable for forge tools and project methodology. OpenClaw compaction behavior may change with version updates -- re-check if upgrading OpenClaw.
