# Computational Approaches: Typed Absence, Provenance, and Compaction in Agentic Systems

**Surveyed:** 2026-03-15
**Domain:** Formal systems / agent runtime reliability / provenance tracking
**Confidence:** MEDIUM-HIGH

## Recommended Stack

The project already has a working Python implementation (forge tools) with 103 tests on MockLM. The computational challenge is now to instrument a real agent runtime (Zarathustra/OpenClaw) and measure protocol behavior under genuine context pressure. The recommended stack builds on the existing forge tools, adds property-based testing for state machine validation, uses NetworkX for provenance graph analysis, and instruments with lightweight decorators and cProfile-based overhead measurement. No heavy infrastructure (databases, message queues) is needed at this stage -- the project is single-runtime, single-machine.

The key computational concern is NOT algorithmic complexity (the data structures are small -- hundreds to low thousands of nodes) but rather **correctness under adversarial conditions**: compaction events, interrupted subcalls, and cascading absence states. The tools must be correct-by-construction, not just fast.

## Numerical Algorithms

| Algorithm | Problem | Convergence | Cost per Step | Memory | Key Reference |
|-----------|---------|-------------|---------------|--------|---------------|
| SHA-256 hash verification | Trace integrity / tamper detection | Exact (deterministic) | O(n) in payload size | O(1) working | FIPS 180-4 |
| Dict-level structural dedup | Trace compression | Single-pass (no iteration) | O(s * d) where s=stages, d=avg dict depth | O(s) for shared dict | Already implemented: forge_trace_codec.py |
| DAG reachability (BFS/DFS) | Provenance chain completeness | O(V+E) exact | O(V+E) | O(V) visited set | Cormen et al. CLRS, Ch. 22 |
| Finite state machine validation | Absence state transition legality | O(1) per transition check | O(1) lookup | O(|states|^2) transition table | Hopcroft & Ullman, Ch. 2 |
| Property-based random testing | State machine invariant coverage | Statistical -- N trials | O(1) per generated case | O(test_case_size) | Hypothesis library docs |

### Convergence Properties

**SHA-256 hash verification:**
- **Convergence criterion:** Hash matches or does not. No iteration needed.
- **Expected rate:** Deterministic, single-pass.
- **Known failure modes:** Collision probability 2^(-128) -- effectively zero. Non-deterministic JSON serialization breaks comparison; already handled via `_canonical_json()` with `sort_keys=True`.

**Structural deduplication (forge_trace_codec.py):**
- **Convergence criterion:** Single pass -- collect candidates, build shared dict, apply refs. No iteration.
- **Expected rate:** O(s * d) where s = number of stages and d = average nested dict depth.
- **Known failure modes:** Dedup only catches exact structural duplicates. Semantically equivalent but structurally different dicts will not be deduplicated. This is by design -- exact reversibility requires exact structural matching.

**DAG reachability for provenance scoring:**
- **Convergence criterion:** BFS/DFS terminates when all reachable nodes are visited.
- **Expected rate:** O(V+E) where V = artifacts + summaries, E = ref edges. For typical agent runs: V < 1000, E < 5000.
- **Known failure modes:** Cycles in the provenance graph indicate a bug (provenance is a DAG). Cycle detection should be a validation check, not a runtime cost.

**State machine transition validation:**
- **Convergence criterion:** Transition table is finite and fully specified. Lookup is O(1).
- **Expected rate:** Constant time per transition.
- **Known failure modes:** Incomplete transition table (undefined transitions silently accepted). Prevention: make the transition table exhaustive and treat undefined transitions as illegal.

**Property-based testing (Hypothesis):**
- **Convergence criterion:** Statistical -- confidence grows with trial count. 200 trials per property is the Hypothesis default; 1000+ for high-assurance properties.
- **Expected rate:** Linear in trial count. Each trial is O(operation_complexity).
- **Known failure modes:** Insufficient strategy coverage can miss edge cases. Shrinking may time out on complex state sequences. Mitigation: use `@settings(max_examples=1000, stateful_step_count=50)` for critical state machine properties.

## Software Ecosystem

### Primary Tools

| Tool | Version | Purpose | License | Maturity |
|------|---------|---------|---------|----------|
| Python | 3.11+ | Runtime, all forge tools | PSF | Stable |
| pytest | 8.x | Test runner, 103 existing tests | MIT | Stable |
| hashlib (stdlib) | 3.11+ | SHA-256 for trace integrity | PSF | Stable |
| json (stdlib) | 3.11+ | Canonical serialization, persistence | PSF | Stable |
| sqlite3 (stdlib) | 3.11+ | Chamber index persistence | PSF | Stable |
| unittest (stdlib) | 3.11+ | Existing test infrastructure | PSF | Stable |

### Supporting Tools

| Tool | Version | Purpose | When Needed |
|------|---------|---------|-------------|
| hypothesis | 6.x | Property-based testing for state machines and protocol invariants | Phase: state machine formalization and transition table validation |
| python-statemachine | 2.x | Declarative FSM definition for null ontology transitions | Phase: formal ontology encoding (alternative: hand-rolled, since the existing code already does this) |
| networkx | 3.x | Provenance DAG analysis, reachability scoring, cycle detection | Phase: provenance measurement on real agent runs |
| prov | 2.1.1 | W3C PROV data model interop, provenance graph export/visualization | Phase: comparison with PROV-AGENT and standard provenance models (optional -- only if interop is needed) |
| cProfile (stdlib) | 3.11+ | Overhead measurement -- wall time and call counts for instrumentation | Phase: overhead benchmarking on Zarathustra |
| time (stdlib) | 3.11+ | Simple wall-clock timing for per-operation overhead | Phase: overhead benchmarking |
| tracemalloc (stdlib) | 3.11+ | Memory overhead measurement for forge instrumentation | Phase: memory overhead benchmarking |

### Tools Evaluated and NOT Recommended

| Tool | Why Not |
|------|---------|
| Flowcept | Designed for distributed multi-framework HPC workflows. Overkill for single-runtime Python agent. Adds Redis/Kafka dependency. |
| OpenTelemetry GenAI conventions | Emerging standard (still draft in 2026). Useful if the project eventually needs production observability, but premature for research-phase measurement. |
| PROV-AGENT / Flowcept's agent decorator | Targets scientific workflow orchestrators (Parsl, Dask). Wrong abstraction level for a single-agent runtime. |
| Graph databases (Neo4j, etc.) | The provenance graphs here are small (< 10K nodes). NetworkX in-memory is sufficient. A graph DB adds deployment complexity with no benefit. |
| BLAKE3 for hashing | Faster than SHA-256 but adds a dependency (the `blake3` crate via Python binding). SHA-256 is adequate for traces under 100MB. |

## Data Flow

```
Agent runtime (Zarathustra/OpenClaw)
  |
  | [LLM API call + tool use]
  v
forge_stage_output.py: create_v1_stage_artifact()
  |
  | [null discipline: typed absence enforcement]
  | [hash computation: SHA-256 of semantic payload]
  | [ref construction: structured refs to upstream artifacts]
  v
forge_chamber.py: register_stage()
  |
  | [ref validation: check all refs resolve in artifact_index]
  | [monotonic index: stage_index grows only]
  | [null discipline: summary requires state or content]
  v
Chamber (in-memory, append-only)
  |
  | [on context pressure or task completion]
  v
forge_trace_codec.py: encode_trace()
  |
  | [structural dedup: shared dict of repeated structures]
  | [ref replacement: inline structures -> $ref:shared.sN strings]
  | [integrity: SHA-256 of original stages stored in envelope]
  v
Trace Envelope (compressed, hash-verified)
  |
  | [on query or recovery]
  v
forge_trace_codec.py: decode_trace()
  |
  | [ref resolution: $ref strings -> deep-copy from shared dict]
  | [integrity check: hash of decoded == original_hash]
  v
Reconstructed stages (bit-for-bit identical to originals)
```

## Computation Order and Dependencies

| Step | Depends On | Produces | Can Parallelize? |
|------|-----------|----------|-----------------|
| 1. Establish uninstrumented Zarathustra baseline | Task set definition | Baseline metrics (completion rate, wall time, token count) | Yes (across tasks) |
| 2. Instrument Zarathustra with forge tools | Baseline + forge tools + integration adapter (like primordial_rlm_bridge.py) | Instrumented runtime | No (must complete before measurement) |
| 3. Run instrumented task suite | Instrumented runtime + same task set | Chamber data per task, violation reports | Yes (across tasks) |
| 4. Measure provenance reachability | Chamber data | DAG analysis, reachability fractions per task | Yes (across tasks) |
| 5. Measure overhead | Baseline metrics + instrumented metrics | Overhead comparison tables | Depends on steps 1, 3 |
| 6. Formalize null ontology transitions | Existing draft (NULL_ONTOLOGY.md) | Complete transition table, Hypothesis property tests | Independent (can run in parallel with 1-5) |
| 7. Trigger and measure compaction | Long-running tasks that exceed context window | Compaction survival metrics, trace round-trip verification | No (requires specific task design) |
| 8. Compare with MockLM anchor | MockLM results (100% provenance, 6/6 violations, 87% compression) + real results | Cross-reference report | Depends on 3-7 |

## Resource Estimates

| Computation | Time (estimate) | Memory | Storage | Hardware |
|-------------|-----------------|--------|---------|----------|
| Forge tool unit tests (103 existing) | < 10 seconds | < 100 MB | Negligible | Any CPU |
| Property-based state machine tests (1000 examples x 50 steps) | 30-120 seconds | < 200 MB | Negligible | Any CPU |
| Single Zarathustra task (uninstrumented) | 30s - 5min per task | < 500 MB + LLM API | < 1 MB per task log | Any CPU + network |
| Single Zarathustra task (instrumented with forge) | 30s - 5min per task + < 5% overhead | < 600 MB (chamber + traces) | < 2 MB per task (chamber JSON + trace) | Any CPU + network |
| Provenance DAG analysis (per chamber) | < 1 second for chambers with < 1000 stages | < 50 MB (NetworkX graph) | Negligible | Any CPU |
| Trace encode/decode round-trip | < 100ms per chamber | O(chamber_size) | Compressed trace < original | Any CPU |
| Full task suite (20 tasks, both baselines) | 2-4 hours including LLM API latency | < 1 GB peak | < 100 MB total | Any CPU + network |
| Overhead benchmark suite | 30 min (cProfile + tracemalloc on 5 representative tasks) | < 1 GB | < 50 MB profiles | Any CPU + network |

**LLM API cost note:** The primary cost driver is NOT local computation but LLM API calls for Zarathustra tasks. Each task uses 10K-200K tokens depending on complexity and compaction. Budget: approximately $5-20 for a full 20-task evaluation suite using Claude/GPT-4 class models.

## Integration with Existing Code

The project already has a working integration adapter: `primordial_rlm_bridge.py`, which wraps the RLM (Recursive Language Model) with forge instrumentation. The same pattern applies to Zarathustra/OpenClaw.

- **Input formats:** Zarathustra/OpenClaw produces subcall chains, tool use results, and LLM responses. These are Python dicts/strings -- same as what forge_stage_output.py already consumes.
- **Output formats:** Forge produces chamber JSON (for persistence), trace envelopes (for compression), and validation error lists (for violation detection). All JSON-serializable.
- **Interface points:**
  - **Per LLM call:** Wrap with `create_v1_stage_artifact()` to capture output + hash + refs
  - **Per subcall:** Register child artifacts with refs to parent, building the provenance DAG
  - **On compaction trigger:** Call `encode_trace()` to compress the chamber, store `original_hash`
  - **On recovery/query:** Call `decode_trace()` + `verify_trace()` for exact reconstruction

**Key integration risk:** Zarathustra's compaction mechanism may differ from the RLM's. The forge tools assume compaction produces a summary text with identifiable source artifacts. If Zarathustra uses opaque compaction (like OpenAI's /responses/compact), forge cannot attach meaningful source_refs. This must be investigated during instrumentation.

## Open Questions

Questions without consensus answers that affect computational approach.

| Question | Why Open | Impact on Project | Approaches Being Tried |
|----------|---------|-------------------|----------------------|
| How does Zarathustra's compaction work internally? | Not yet inspected; may be opaque API-level or transparent prompt-level | Determines whether forge can attach source_refs to compacted summaries | Inspect Zarathustra source; worst case, treat compacted content as pruned_recoverable with hash-only anchor |
| What is the right granularity for provenance nodes? | Per-LLM-call? Per-tool-use? Per-subcall-chain? | Affects DAG size, overhead, and reachability scoring denominator | Start with per-LLM-call (matches existing forge_stage_output), measure, adjust |
| Should state transitions be recorded as first-class artifacts? | Currently transitions are implicit (old state -> new state) | Would increase trace size but enable transition auditing | Defer until basic measurement is done; add if violation analysis needs it |
| Is 8 absence states sufficient for real agent workflows? | MockLM tested 8 states; real agents may encounter timed_out, interrupted | May need to expand ontology or collapse states | Run real tasks first, catalog naturally-occurring absence patterns, then decide |

## Anti-Approaches

Approaches to explicitly NOT pursue.

| Anti-Approach | Why Avoid | What to Do Instead |
|---------------|-----------|-------------------|
| Semantic deduplication in trace compression | Breaks exact reversibility guarantee. Two structurally different dicts that are "semantically equivalent" cannot be safely merged without losing the ability to reconstruct originals. | Stick with structural (hash-based) dedup as in forge_trace_codec.py. Accept lower compression ratios in exchange for exact round-trip. |
| LLM-based compaction verification | Using an LLM to judge whether a compacted summary preserves "all important information" is subjective and non-reproducible. | Use structural verification: hash match, ref chain completeness, reachability scoring. These are deterministic and reproducible. |
| Graph database for provenance storage | Adds deployment complexity (Neo4j, etc.) for graphs that fit in memory. | Use NetworkX for analysis, SQLite + JSON for persistence. The project's provenance graphs are small. |
| Full W3C PROV compliance | The W3C PROV data model is designed for inter-organizational provenance sharing. The forge tools are internal-only. Forcing PROV compliance would add translation overhead without benefit. | Keep forge's native schema (ArtifactEnvelope, SummaryView, Chamber). If interop is ever needed (RQ4 generality), add a PROV export layer then. |
| Gradient-based compression optimization (ACON-style) | ACON optimizes compressor prompts for task performance. The project needs lossless structural compression, not lossy semantic compression. Different goals. | Use the existing structural dedup. If lossy compression is ever desired, it would be a separate layer above the lossless trace codec. |
| Production observability tooling (OpenTelemetry, Datadog) | The project is measuring research-grade metrics (provenance reachability, absence state coverage), not production SLOs. OTel conventions for GenAI are still draft. | Use cProfile + tracemalloc + custom measurement code. Simpler, no dependencies, full control over what is measured. |

## Logical Dependencies

```
forge_nulls.py (typed absence)
  -> forge_stage_output.py (uses null discipline for artifact construction)
  -> forge_chamber.py (uses null discipline for registration validation)

forge_reversible_summary.py (grounded summaries)
  -> forge_stage_output.py (uses create_summary_view for stage summaries)

forge_v1_bridge.py (protocol validation)
  -> forge_stage_output.py (validates artifacts at construction time)
  -> forge_chamber.py (validates stages at registration time)

forge_chamber.py (chamber/context system)
  -> forge_trace_codec.py (encodes chamber stages into compressed traces)

NULL_ONTOLOGY.md (8 absence states)
  -> forge_nulls.py (AbsenceState enum, V1_ABSENCE_STATES)
  -> Transition table formalization (not yet implemented)

MockLM experiment results (anchor)
  -> Cross-reference comparison (requires real Zarathustra results)

Zarathustra baseline (uninstrumented)
  -> Overhead comparison (requires instrumented Zarathustra results)
```

## Recommended Investigation Scope

Prioritize:
1. **Zarathustra instrumentation adapter** -- replicate the primordial_rlm_bridge.py pattern for OpenClaw. This unblocks all real-world measurement.
2. **Provenance reachability measurement** -- implement DAG analysis with NetworkX on real chamber data. This directly answers RQ3.
3. **State machine formalization with Hypothesis** -- property-based testing of the null ontology transition table. This directly answers RQ1.
4. **Overhead benchmarking** -- cProfile + tracemalloc on instrumented vs uninstrumented runs. This addresses the "complexity without benefit" stop condition.

Defer:
- W3C PROV export: only if RQ4 (generality) becomes in-scope
- Production observability (OTel): only if the project moves past research phase
- Expanded absence states (timed_out, interrupted): wait for real data to show the need

## Validation Strategy

| Result | Validation Method | Benchmark | Source |
|--------|------------------|-----------|--------|
| Trace round-trip integrity | `verify_trace()`: hash of decoded stages == original_hash | 100% match rate | Already implemented and tested |
| Provenance reachability | BFS from leaf artifacts to root: fraction of artifacts with complete chains | MockLM anchor: 100% reachability | MockLM experiment |
| Violation detection | Count structural violations caught (null discipline, dangling refs, duplicates) | MockLM anchor: 6/6 deliberate violations caught | MockLM experiment scenario D |
| Compression ratio | encoded_size / original_size | MockLM anchor: 87% compression (1.87x ratio) | MockLM experiment scenario C |
| Overhead | wall_time(instrumented) / wall_time(baseline) - 1.0 | Target: < 10% overhead on real tasks | To be established |
| State transition legality | Hypothesis stateful test: generate random transition sequences, assert all accepted transitions are in legal set | 100% of 1000+ random sequences pass | To be established |
| Absence state coverage | Count distinct absence states naturally occurring in real agent runs | At least 4 of 8 states observed naturally | To be established |

## Key References and Sources

### Directly Relevant to This Project

- **PROV-AGENT** -- Souza et al., "Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows," IEEE e-Science 2025. [arXiv:2508.02866](https://arxiv.org/abs/2508.02866). Extends W3C PROV for LLM agent workflows. Most relevant prior art for provenance in agent systems.
- **ACON** -- Kang et al., "Optimizing Context Compression for Long-horizon LLM Agents," arXiv 2025. [arXiv:2510.00615](https://arxiv.org/abs/2510.00615). Gradient-free compression guideline optimization. Relevant as a comparison point for lossy vs lossless compression approaches.
- **Flowcept** -- ORNL, "Runtime provenance for AI and scientific workflows." [GitHub: ORNL/flowcept](https://github.com/ORNL/flowcept). Python decorator-based provenance capture. Architectural reference for instrumentation patterns.
- **Google ADK Context Compaction** -- [ADK Docs](https://google.github.io/adk-docs/context/compaction/). Sliding window compaction with summarization. Reference for how production agent frameworks handle compaction.
- **Anthropic Context Engineering** -- [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Production patterns for context management in agent systems.

### Tools and Libraries

- **Hypothesis** -- property-based testing for Python. [hypothesis.readthedocs.io](https://hypothesis.readthedocs.io/en/latest/stateful.html). Stateful testing support directly applicable to state machine validation.
- **python-statemachine** -- declarative FSM library. [PyPI: python-statemachine](https://pypi.org/project/python-statemachine/). Option for encoding null ontology transitions declaratively.
- **NetworkX** -- graph analysis library. [networkx.org](https://networkx.org/). DAG construction, reachability, cycle detection for provenance graphs.
- **prov (Python)** -- W3C PROV data model implementation, v2.1.1. [PyPI: prov](https://pypi.org/project/prov/). Optional interop layer if PROV export is ever needed.
- **OpenTelemetry GenAI Semantic Conventions** -- [opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/). Emerging standard for agent observability. Not recommended now but worth monitoring.

### Algorithmic Foundations

- **Cormen, Leiserson, Rivest, Stein** -- "Introduction to Algorithms" (CLRS), Ch. 22 (BFS/DFS for graph traversal). Standard reference for provenance DAG reachability algorithms.
- **Ramusat et al.** -- "Provenance-Based Algorithms for Rich Queries over Graph Databases," EDBT 2021. [hal-03140067](https://inria.hal.science/hal-03140067v1/document). Semiring-based provenance query algorithms. Relevant if provenance queries become complex.
- **FIPS 180-4** -- SHA-256 specification. Standard reference for the hash function used in trace verification.

## Sources

- [PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions](https://arxiv.org/abs/2508.02866) -- agent-level provenance model extending W3C PROV
- [ACON: Optimizing Context Compression for Long-horizon LLM Agents](https://arxiv.org/abs/2510.00615) -- gradient-free context compression optimization
- [Flowcept: Runtime provenance for AI workflows](https://github.com/ORNL/flowcept) -- Python decorator-based provenance capture
- [Google ADK Context Compaction](https://google.github.io/adk-docs/context/compaction/) -- production agent compaction patterns
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) -- production context management
- [OpenTelemetry GenAI Agent Observability](https://opentelemetry.io/blog/2025/ai-agent-observability/) -- emerging observability standards
- [Hypothesis Stateful Testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) -- property-based state machine testing
- [prov Python library v2.1.1](https://pypi.org/project/prov/) -- W3C PROV data model implementation
- [Factory.ai: Evaluating Context Compression for AI Agents](https://factory.ai/news/evaluating-compression) -- compression benchmark methodology
- [Provenance-Based Algorithms for Rich Queries over Graph Databases](https://inria.hal.science/hal-03140067v1/document) -- semiring-based provenance query algorithms
- [Building an internal agent: Context window compaction](https://lethain.com/agents-context-compaction/) -- practical compaction patterns
