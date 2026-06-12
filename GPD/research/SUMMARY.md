# Research Summary

**Project:** Primordial Computing: Typed Absence and Provenance in Agentic Systems
**Domain:** Formal systems / Agent runtime reliability / Type theory / Data provenance / Context management
**Synthesized:** 2026-03-15
**Confidence:** MEDIUM-HIGH

## Unified Notation

The project sits at the intersection of programming language theory, data provenance, and agent systems engineering. Notation is drawn primarily from software engineering and formal methods rather than physics, so conventional symbol collisions are minimal. The following table establishes binding conventions for all downstream work.

| Symbol / Term | Quantity | Convention | Notes |
|---|---|---|---|
| `AbsenceState` | Typed absence enum | 8 canonical members: `not_invoked`, `unknown`, `unresolved`, `withheld`, `invalid`, `deleted`, `pruned_recoverable`, `resolved` | Deprecated alias `pruned` maps to `pruned_recoverable`; legacy field name `absence_state` maps to `state` via `normalize_absent_object()` |
| `source_refs` | Provenance references | List of structured refs `[{ref: "artifact:...", ...}]` | Lightweight alternative to full W3C PROV; sufficient for single-runtime lineage |
| `parent_id` | Artifact lineage pointer | String ID of parent artifact in provenance chain | Combined with `source_refs` for complete provenance DAG |
| `reachability_fraction` | Provenance completeness metric | (reachable artifacts) / (total artifacts), via BFS/DFS on provenance DAG | Values range [0, 1]; 1.0 = complete structural provenance |
| `compression_ratio` | Trace codec efficiency | `encoded_size / original_size` | Measures forge internal dedup; distinct from LLM-level compaction ratio |
| `vs_vanilla_pct` | External overhead comparison | `(forge_size - vanilla_size) / vanilla_size * 100` | Measures total overhead of adding provenance vs vanilla logging |
| Compaction (forge) | Structural deduplication | Lossless, hash-verified via SHA-256 | `encode_trace()` / `decode_trace()` round-trip |
| Compaction (LLM) | Context-window summarization | Lossy, semantic; replaces message history with summary | Not controlled by forge; forge records `pruned_recoverable` state |
| Structural violation | Protocol-level illegal state transition or missing metadata | Distinguished from "hallucination" (content error) and "fault" (infrastructure failure) | Forge detects structural violations only; semantic correctness is out of scope |
| Hoare triple | Pre/postcondition specification | `{P} C {Q}` -- precondition P, command C, postcondition Q | Forge transition rules are domain-specific Hoare contracts |

**Unit system:** Not applicable (formal systems research). All metrics are dimensionless ratios or counts.

**Key convention distinction:** "Compaction" in this project has two distinct meanings that must never be conflated: (1) forge trace codec compression (lossless, reversible, hash-verified) and (2) LLM context-window compaction (lossy, semantic, uncontrolled by forge). All measurements must report which layer is being measured.

## Executive Summary

This project investigates whether typed absence, explicit provenance, and recoverable compaction can prevent silent state loss in long-running autonomous agents. The theoretical grounding is strong: Hoare's identification of null as a billion-dollar mistake (1969/2009) motivates typed absence; W3C PROV (2013) provides the standard provenance framework that forge's lightweight `parent_id` + `source_refs` model simplifies; and Landauer's principle (1961) provides the information-theoretic basis for why lossless compaction requires preserving sufficient metadata for reconstruction. The existing prototype (forge tools with 103 passing tests against MockLM) demonstrates the protocol works under controlled conditions: 100% provenance reachability, 6/6 deliberate violations detected, 87% trace compression. The central challenge -- and the weakest assumption -- is whether these results survive transition to a real LLM runtime (Zarathustra/OpenClaw) under genuine context pressure.

The recommended approach is a staged validation campaign with three baselines (MockLM ceiling, uninstrumented Zarathustra floor, instrumented Zarathustra treatment) and seven primary methods: Hypothesis stateful testing for ontology verification (RQ1), targeted fault injection with differential testing for violation detection (RQ2), and DAG reachability analysis with round-trip hash verification for compaction survival (RQ3). The computational infrastructure is lightweight -- pure Python with pytest, Hypothesis, NetworkX, and standard library tools. The primary cost driver is LLM API calls for real agent tasks, not local computation. All algorithms operate on small data structures (tens to hundreds of nodes) and run in seconds.

The principal risks are: (1) the MockLM-to-real-LLM validity gap -- controlled test success may not transfer to nondeterministic agent behavior; (2) compaction destroying provenance semantically while preserving it structurally -- refs resolve but content behind them is lossy-summarized; (3) typed absence catching only structural violations while the most dangerous agent failures involve wrong (not absent) values; and (4) measuring against a straw-man baseline that makes any instrumentation look good. The mitigation strategy is explicit: staged validation with increasing realism, separate structural and semantic reachability metrics, honest framing of what typed absence does and does not catch, and a three-tier baseline comparison (vanilla, structured logging, forge).

## Key Findings

### Prior Work Landscape

The project extends three established research threads into a novel combination. **Typed absence** extends the Option/Maybe type (ML 1973, Haskell 1990, Rust 2015) from binary present/absent to an 8-state ontology encoding the *reason* for absence. This is a genuine extension: no prior work distinguishes `not_invoked` from `unknown` from `deleted` from `pruned_recoverable` at the type level. **Provenance tracking** simplifies W3C PROV's Entity-Activity-Agent triad into a lightweight `parent_id` + `source_refs` model designed to survive compaction, where PROV assumes a persistent, fully addressable graph. **Recoverable compaction** addresses the gap between MemGPT-style paging (mechanism without semantics) and ACON-style compression (bounded but destroys provenance). [CONFIDENCE: HIGH for individual threads; MEDIUM for the combination being novel and sufficient]

**Must reproduce (benchmarks):**
- MockLM experiment results: 100% provenance reachability, 6/6 violations detected, 87% trace compression -- these are the controlled-condition ceiling that real runtime results are measured against
- Round-trip integrity: `decode(encode(trace))` produces bitwise-identical output via SHA-256

**Novel contributions (if validated on real runtime):**
- Typed absence ontology that distinguishes 8 semantically meaningful absence states with formal transition rules
- Provenance-preserving compaction that maintains grounded return paths through context-window summarization
- Structural violation detection on naturally-occurring agent failures (not just synthetic injections)

**Recent parallel developments** (2025-2026) validate the problem space: Agent Contracts (Ye et al. 2026) formalizes resource bounds; PROV-AGENT (Souza et al. 2025) extends W3C PROV for agent workflows; silent hallucination research identifies the failure class forge aims to structurally prevent. These are orthogonal and composable with the primordial approach.

### Methods and Tools

Seven methods are recommended, organized by research question. For **RQ1 (ontology formalization):** Hypothesis `RuleBasedStateMachine` for implementation testing of the 8-state transition rules, with optional TLA+ for specification-level verification. For **RQ2 (violation detection):** targeted fault injection (9 fault types: D1-D9) with differential testing across three baselines (MockLM, uninstrumented Zarathustra, instrumented Zarathustra), using bootstrap confidence intervals for small-sample statistics. For **RQ3 (compaction survival):** DAG reachability analysis via NetworkX on real chamber data, plus round-trip hash verification for structural integrity. For **test suite quality:** Mutmut mutation testing targeting >85% mutation score on core forge modules. [CONFIDENCE: HIGH -- all tools are mature, well-documented, and appropriate for the data scale]

**Major components:**
1. Hypothesis stateful testing -- verify transition legality under random exploration (1000+ paths, ~5 seconds)
2. Targeted fault injection harness -- extend D1-D6 to D1-D9 covering compaction, context pressure, and timeout scenarios
3. Provenance DAG reachability -- BFS/DFS on NetworkX graphs, O(V+E) exact computation
4. Differential three-baseline comparison -- isolate forge's contribution from "any validation at all"
5. Bootstrap CI -- honest uncertainty quantification for small-sample metrics (N < 30)

### Computational Approaches

The computational challenge is correctness under adversarial conditions, not algorithmic complexity. All data structures are small (tens to hundreds of nodes per agent run). The recommended stack is pure Python: pytest + Hypothesis for testing, NetworkX for graph analysis, cProfile + tracemalloc for overhead measurement, and standard library tools (hashlib, json, sqlite3) for persistence and integrity. No heavy infrastructure (databases, message queues, distributed systems) is needed. The full experimental suite (20 tasks, both baselines) is estimated at 2-4 hours including LLM API latency, with ~$5-20 in API costs. [CONFIDENCE: HIGH for stack selection; MEDIUM for resource estimates until Zarathustra integration is characterized]

The critical integration risk is Zarathustra's compaction mechanism: if it uses opaque API-level compaction (like OpenAI's `/responses/compact`), forge cannot attach meaningful `source_refs` to compacted summaries. This must be investigated early.

### Critical Pitfalls

1. **MockLM-to-real-LLM validity gap** -- All 103 tests pass on deterministic MockLM; real LLM nondeterminism may break integration assumptions. **Mitigation:** Staged validation campaign: MockLM -> recorded playback -> live short tasks -> live compaction-triggering tasks.

2. **Compaction destroys provenance while appearing to preserve it** -- Forge's `verify_trace()` checks hash integrity of the *trace encoding*, but LLM-level compaction lossy-summarizes content *before* encoding. Refs resolve structurally but point to degraded content. **Mitigation:** Separate structural reachability (refs resolve) from semantic reachability (content behind refs matches original hash). This is the project's weakest anchor.

3. **Typed absence catches structural violations, not semantic failures** -- The most dangerous agent failures involve wrong (not absent) values. The MAST taxonomy identifies 14 multi-agent failure modes; only a fraction involve null/empty state. **Mitigation:** Frame typed absence as necessary-but-not-sufficient. Design experiments with known-failing tasks to demonstrate the boundary.

4. **Provenance chains over-reference under revision cycles** -- `_build_source_refs` returns ALL upstream artifacts, creating O(n^2) ref growth. 100% reachability with 0% specificity is not useful provenance. **Mitigation:** Distinguish structural provenance (what was available) from causal provenance (what was actually used). Measure ref chain width.

5. **Straw-man baseline undermines credibility** -- Comparing forge against vanilla logging (zero invariant checks) will always show forge winning. **Mitigation:** Add a structured-logging intermediate baseline. Report three-tier differential value.

## Approximation Landscape

| Method | Valid Regime | Breaks Down When | Controlled? | Complements |
|---|---|---|---|---|
| Hypothesis stateful testing | Discrete, finite state machines (8 states, ~14 transitions) | Infinite state spaces; timing-dependent properties | Yes (bounded examples, shrinking) | TLA+ for specification-level; Hypothesis for implementation-level |
| Mutmut mutation testing | Pure logic modules (forge_nulls.py, forge_trace_codec.py, forge_reversible_summary.py) | I/O-heavy orchestration code; timing-dependent mutations | Yes (mutation score = killed/total) | Code coverage as secondary sanity check |
| DAG reachability analysis | Small graphs (V < 1000, E < 5000); acyclic provenance | Cycles (indicates bug); semantic gaps not captured | Yes (exact BFS/DFS) | Content-hash comparison for semantic fidelity |
| SHA-256 round-trip verification | Structural dedup (forge trace codec) | Semantic compaction (LLM-level); non-deterministic JSON serialization | Yes (collision probability 2^-128) | Provenance reachability for semantic layer |
| Bootstrap CI | Metrics with 5-30 data points | N < 5 (report exact counts instead); assumes exchangeability | Yes (nonparametric) | Clopper-Pearson exact binomial for proportions |
| Targeted fault injection | Known fault classes (D1-D9) | Unknown failure modes; LLM-specific emergent behaviors | Partially (covers known faults, not unknown unknowns) | Clean runs for false-positive measurement |
| Differential three-baseline comparison | When confounds are controlled (same tasks, same conditions) | Non-deterministic agent behavior across runs | Partially (multiple runs + distributions mitigate) | Positive controls (injected faults) + negative controls (clean runs) |

**Coverage gap:** No method validates semantic faithfulness of compacted content. Structural reachability confirms refs exist; hash comparison confirms structural integrity; but whether a lossy summary preserves the information needed for downstream reasoning is not captured by any current metric. This gap is acknowledged in the project charter and is the open frontier for RQ3.

## Theoretical Connections

### Established Connections

1. **Hoare logic -> Forge transition rules:** The absence state machine's legal/illegal transitions are domain-specific Hoare contracts. Each transition has implicit preconditions (current state) and postconditions (target state + required metadata). The forge validation layer (validate_record, validate_field) operationalizes Design by Contract (Meyer 1986) for absence-type correctness rather than value-range correctness. [ESTABLISHED]

2. **W3C PROV -> Forge provenance model:** Forge's `parent_id` + `source_refs` is a domain-specific projection of PROV's derivation and generation relations, optimized for single-runtime agent traces and designed to survive compaction. PROV-AGENT (Souza et al. 2025) brings the standard closer to agent-specific workflows but still lacks absence typing and compaction recoverability. [ESTABLISHED]

3. **Landauer's principle -> Reversible compaction:** Logically irreversible operations (many-to-one mappings) have a thermodynamic cost. By analogy, lossy compaction that destroys source references is "irreversible information erasure" -- the provenance cannot be reconstructed. Forge's `pruned_recoverable` state with `source_refs` preserves the metadata needed for reversibility. [ESTABLISHED as analogy; not a formal proof]

### Conjectured Connections

4. **Agent Contracts (Ye et al. 2026) + Forge state contracts:** Agent Contracts govern resource bounds (token budgets, time limits); forge governs state semantics (absence types, provenance completeness). These are orthogonal governance dimensions. Composing them would yield agents with both resource-bounded execution AND state-semantic correctness guarantees. [CONJECTURED -- not yet implemented or tested]

5. **ACON compression + Forge provenance:** ACON achieves 26-54% compression via guideline-optimized lossy summarization without provenance. Forge achieves 87% compression via lossless structural dedup with provenance. A combined approach -- ACON-style semantic compression with forge-style provenance tracking -- could achieve high compression ratios while maintaining grounded return paths. [CONJECTURED -- the 87% vs 26-54% comparison may not be apples-to-apples due to different compression targets]

### Cross-Validation Opportunities

| | Uninstrumented Zarathustra | MockLM + Forge | Instrumented Zarathustra | Structured Logging Baseline |
|---|:---:|:---:|:---:|:---:|
| **MockLM + Forge** | Ceiling vs floor comparison | -- | Gap = real-world degradation | N/A |
| **Instrumented Zarathustra** | Forge's differential value | Gap = nondeterminism cost | -- | Typed absence's differential value |
| **Structured Logging** | Any-validation value | N/A | Forge-specific value above generic validation | -- |

**High-risk method with no cross-validation:** Semantic faithfulness of compacted content has no independent cross-check. This is flagged for investigation.

## Critical Claim Verification

| # | Claim | Source | Verification | Result |
|---|---|---|---|---|
| 1 | Hypothesis PBT finds ~50x more mutations than average unit tests | METHODS.md | web_search: OOPSLA 2025 empirical PBT evaluation | CONFIRMED -- OOPSLA 2025 study of 426 Python programs, published ACM SIGPLAN |
| 2 | MemGPT achieves virtual context via OS-inspired paging | PRIOR-WORK.md | web_search: arXiv:2310.08560 | CONFIRMED -- Packer et al. 2023, two-tier memory architecture |
| 3 | Agent Contracts achieve 90% token reduction, 525x lower variance | PRIOR-WORK.md | web_search: arXiv:2601.08815 | CONFIRMED -- Ye & Tan 2026, formal resource-bounded framework |
| 4 | "Lost in the Middle" shows 30%+ accuracy drop | PRIOR-WORK.md | web_search: Liu et al. TACL 2024 | CONFIRMED -- Published TACL 2024, pages 157-173 |
| 5 | PROV-AGENT extends W3C PROV for agent workflows | PRIOR-WORK.md / COMPUTATIONAL.md | web_search: PROV-AGENT 2025 | CONFIRMED -- Souza et al., IEEE e-Science 2025, extends PROV with MCP concepts |
| 6 | MockLM experiment: 100% provenance, 6/6 violations, 87% compression | PRIOR-WORK.md | Local data: experiment_results.json, 103 tests | CONFIRMED (local verification; controlled conditions) |
| 7 | ACON achieves 26-54% memory reduction | PRIOR-WORK.md | Cited as arXiv:2510.00615 | UNVERIFIED -- unable to independently verify exact figures; relies on researcher citation |

## Input Quality -> Roadmap Impact

| Input File | Quality | Affected Recommendations | Impact if Wrong |
|---|---|---|---|
| METHODS.md | GOOD | Method selection, phase ordering, validation strategy | Phases 2-4 may need different tools or approaches |
| PRIOR-WORK.md | GOOD | Benchmark values, novelty claims, success criteria | Overclaimed novelty; benchmarks may be wrong ceiling |
| COMPUTATIONAL.md | GOOD | Resource estimates, tool selection, integration risk assessment | Tool substitution needed; timeline estimates wrong |
| PITFALLS.md | GOOD | Risk mitigation in all phases; baseline design | Blind spots in experimental design |

All four input files are substantive, well-structured, and contain confidence-weighted claims. No quality issues detected.

## Implications for Roadmap

### Suggested Phase Structure

### Phase 1: Ontology Formalization and State Machine Verification (RQ1)

**Rationale:** The 8-state absence ontology is the foundation for all downstream work. It must be formally specified and verified before being tested on real agents. This phase has no external dependencies (no LLM API calls needed) and can begin immediately.
**Delivers:** Complete transition table for 8 absence states; Hypothesis `RuleBasedStateMachine` tests verifying all legal transitions and catching all illegal ones; optional TLA+ specification.
**Methods:** Hypothesis stateful testing (primary), Mutmut mutation testing (supporting), optional TLA+ model checking.
**Validates:** All 11 legal transitions exercised; all 3 explicitly illegal transitions detected; mutation score >85% on forge_nulls.py.
**Avoids:** Pitfall 3 (typed absence insufficient) -- by formally specifying exactly what the ontology covers and documenting what it does not.
**Risk:** LOW -- well-established formal methods on a small, finite state space.

### Phase 2: Integration and Baseline Establishment

**Rationale:** Before measuring forge's value, establish what "normal" looks like on the real runtime. This phase addresses Pitfall 1 (MockLM-to-real gap) and Pitfall 5 (straw-man baseline). Must precede measurement phases.
**Delivers:** Zarathustra instrumentation adapter (following primordial_rlm_bridge.py pattern); uninstrumented baseline metrics on the task suite; structured-logging intermediate baseline; characterization of Zarathustra's compaction mechanism.
**Methods:** Differential testing setup, smoke tests with real LLM calls, recorded-response playback tier.
**Builds on:** Phase 1 (formalized ontology ensures correct state assignment during instrumentation).
**Avoids:** Pitfall 1 (MockLM-to-real gap) via staged validation; Pitfall 5 (straw-man baseline) via three-tier design.
**Risk:** MEDIUM -- Zarathustra's compaction mechanism is unknown until inspected. If opaque, forge cannot attach meaningful source_refs, and the integration strategy must adapt.

### Phase 3: Violation Detection Measurement (RQ2)

**Rationale:** With baselines established, measure whether forge detects structural failures that go undetected without it. This is the primary experimental signal per the project charter.
**Delivers:** Violation report with three-tier comparison (vanilla, structured logging, forge); detection rates with bootstrap CIs; false-positive rate on clean runs.
**Methods:** Targeted fault injection (D1-D9), differential testing, bootstrap CI.
**Builds on:** Phase 2 (baselines and instrumented runtime).
**Validates:** Acceptance criterion: at least 1 naturally-occurring violation detected. If not met, report as negative finding per Pitfall 3.
**Avoids:** Pitfall 3 (typed absence insufficient) -- by including known-failing tasks and honestly reporting what forge catches vs. what it misses.
**Risk:** MEDIUM -- if naturally-occurring violations are rare in the test campaign, the primary signal may be weak.

### Phase 4: Compaction Survival Measurement (RQ3)

**Rationale:** This addresses the project's weakest anchor -- whether provenance chains survive real context-window compaction. Requires tasks long enough to trigger genuine compaction (>50K tokens of accumulated state).
**Delivers:** Provenance reachability fractions per task, structural vs semantic reachability comparison, compaction survival report with MockLM cross-reference.
**Methods:** DAG reachability analysis (NetworkX), round-trip hash verification, content-hash comparison before/after compaction.
**Builds on:** Phase 2 (compaction mechanism characterized), Phase 3 (instrumented runtime validated).
**Validates:** Reachability measured and any gaps explained per scoping contract. MockLM anchor: 100% reachability under controlled conditions; measure degradation under real conditions.
**Avoids:** Pitfall 2 (compaction destroys provenance while appearing to preserve it) -- by separating structural and semantic reachability metrics.
**Risk:** HIGH -- this is the genuinely open question. The outcome is uncertain and may produce a negative result.

### Phase 5: Cross-Reference and Synthesis

**Rationale:** Integrate results across all measurement phases. Compare real runtime results against MockLM ceiling. Assess whether the three research questions are answered.
**Delivers:** Cross-reference report: MockLM ceiling vs Zarathustra floor vs instrumented Zarathustra; assessment of each RQ; honest evaluation of what worked and what did not; identification of items for future work (RQ4 generality).
**Methods:** Statistical comparison, qualitative analysis.
**Builds on:** All prior phases.
**Risk:** LOW -- synthesis phase, not discovery phase.

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** The ontology must be formally verified before being embedded in real-agent instrumentation. An incorrectly specified transition table would produce meaningless measurements.
- **Phase 2 before Phases 3-4:** Baselines must exist before differential measurements. The compaction mechanism must be characterized before compaction survival can be measured.
- **Phase 3 before Phase 4:** Violation detection is the primary experimental signal (per project charter); compaction survival is the harder, higher-risk question. Establishing that forge works at all (Phase 3) before testing the hardest claim (Phase 4) reduces risk.
- **Phase 1 can partially overlap Phase 2:** Ontology formalization is independent of Zarathustra integration and can proceed in parallel.

### Phases Requiring Deep Investigation

- **Phase 2:** Zarathustra's compaction mechanism is uncharacterized. If it is opaque (API-level), the integration strategy must be redesigned. This is the highest-priority unknown.
- **Phase 4:** Compaction survival is genuinely open. No prior work demonstrates provenance-preserving compaction under real context pressure. The outcome is uncertain.

Phases with established methodology (straightforward execution):
- **Phase 1:** Hypothesis stateful testing and TLA+ model checking are well-documented for finite state machines. Multiple references available.
- **Phase 3:** Fault injection and differential testing are standard experimental methods. The only uncertainty is whether naturally-occurring violations are frequent enough to observe.
- **Phase 5:** Synthesis follows standard research methodology.

## Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| Methods | HIGH | All recommended tools are mature, well-documented, and appropriate for the data scale. Hypothesis, pytest, NetworkX are production-grade. |
| Prior Work | HIGH | Individual research threads are well-established (type theory, PROV, reversible computation). The specific combination is novel but each component has strong foundations. |
| Computational Approaches | HIGH | Lightweight pure-Python stack on small data structures. No algorithmic risk. Primary uncertainty is Zarathustra integration, not computational tooling. |
| Pitfalls | MEDIUM-HIGH | Five critical pitfalls identified with concrete mitigations. The gap is unknown unknowns from real LLM nondeterminism. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Zarathustra compaction mechanism:** Uncharacterized. Must be investigated in Phase 2 before compaction measurement design can be finalized.
- **Semantic reachability metric:** No current method validates whether content behind a `pruned_recoverable` ref is faithful to the original. Structural reachability (refs resolve) is necessary but not sufficient. A content-hash comparison approach is sketched but untested.
- **Natural violation frequency:** Unknown whether real Zarathustra workflows produce enough structural violations for meaningful measurement. If violations are rare, the test campaign may need to be larger than estimated.
- **Ontology sufficiency:** The 8-state ontology may be insufficient for real agent workflows. `timed_out` and `interrupted` are already flagged as candidates. Real data from Phase 2 will inform whether expansion is needed.
- **Provenance specificity:** Current `_build_source_refs` conflates structural and causal provenance (refs ALL upstream artifacts). This degrades provenance utility. May need redesign before Phase 4 measurements.

## Open Questions

1. **[HIGH, blocks Phase 2]** How does Zarathustra's compaction work internally? Opaque vs transparent determines whether forge can attach meaningful source_refs.

2. **[HIGH, blocks Phase 4]** Can semantic reachability be measured? Structural reachability (refs resolve) is easy; semantic reachability (content behind refs is faithful) has no established metric.

3. **[MEDIUM, blocks Phase 3]** How frequent are naturally-occurring structural violations in real agent workflows? If too rare, the test campaign may produce null results.

4. **[MEDIUM, informs Phase 1]** Is the 8-state ontology sufficient? Should `timed_out` and `interrupted` be added? Should recoverability be graded rather than binary?

5. **[MEDIUM, informs Phase 4]** What is the provenance metadata overhead under real context pressure? At what fraction of the context budget does provenance tracking itself become a problem?

6. **[LOW, future work]** How does provenance compose across multi-agent boundaries? The forge tools handle single-agent traces; multi-agent provenance is deferred to RQ4.

7. **[LOW, informs Phase 3]** What is the false positive rate of typed-absence enforcement on real (non-injected) agent traces?

## Sources

### Primary (HIGH)

- Hoare, C.A.R. (1969). "An Axiomatic Basis for Computer Programming." CACM 12(10):576-580. -- Foundation for contract-based verification
- Hoare, C.A.R. (2009). "Null References: The Billion Dollar Mistake." QCon London keynote. -- Motivates typed absence
- W3C (2013). "PROV-DM: The PROV Data Model." W3C Recommendation. -- Standard provenance ontology
- Liu, N.F. et al. (2024). "Lost in the Middle." [TACL 2024](https://aclanthology.org/2024.tacl-1.9/). -- Attention degradation in long contexts
- Packer, C. et al. (2023). [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560). -- Virtual context management
- Landauer, R. (1961). "Irreversibility and Heat Generation in the Computing Process." IBM J. Res. Dev. -- Thermodynamic cost of information erasure
- [OOPSLA 2025 PBT Empirical Study](https://2025.splashcon.org/details/OOPSLA/102/An-Empirical-Evaluation-of-Property-Based-Testing-in-Python) -- Hypothesis finds ~50x more mutations than unit tests
- Amazon (2014). [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf) -- TLA+ for protocol verification at scale
- MockLM experiment (local): experiment_results.json, 103 passing tests -- Controlled-condition anchor

### Secondary (MEDIUM)

- Ye, Q. et al. (2026). [Agent Contracts](https://arxiv.org/abs/2601.08815). -- Formal resource-bounded agent governance
- Souza, R. et al. (2025). [PROV-AGENT](https://arxiv.org/abs/2508.02866). -- W3C PROV extended for agent workflows
- Kang, M. et al. (2025). [ACON](https://arxiv.org/abs/2510.00615). -- Context compression without provenance
- Pathak, D. et al. (2025). "Detecting Silent Failures in Multi-Agentic AI Trajectories." arXiv:2511.04032. -- Silent failure detection benchmark
- Cemri et al. (2025). "Why Do Multi-Agent LLM Systems Fail?" arXiv:2503.13657. -- MAST failure taxonomy
- Lethain (2026). [Context window compaction](https://lethain.com/agents-context-compaction/). -- Practical compaction patterns
- [Hypothesis Stateful Testing Docs](https://hypothesis.readthedocs.io/en/latest/stateful.html) -- RuleBasedStateMachine API
- SBQS 2024. [Mutation Testing Tools for Python](https://dl.acm.org/doi/10.1145/3701625.3701659) -- Mutmut benchmarks

### Tertiary (LOW)

- "Tiny Silent Hallucinations in Agentic AI." OpenReview (ICLR 2026 submission). -- Needs peer review
- "Agent Behavioral Contracts." arXiv:2602.22302. -- Runtime behavioral contracts; early work
- ReliabilityBench, arXiv:2601.06112. -- Chaos engineering for agents; relevant but tangential

---

_Research synthesis completed: 2026-03-15_
_Ready for research plan: yes_

```yaml
# --- ROADMAP INPUT (machine-readable, consumed by gpd-roadmapper) ---
synthesis_meta:
  project_title: "Primordial Computing: Typed Absence and Provenance in Agentic Systems"
  synthesis_date: "2026-03-15"
  input_files: [METHODS.md, PRIOR-WORK.md, COMPUTATIONAL.md, PITFALLS.md]
  input_quality: {METHODS: good, PRIOR-WORK: good, COMPUTATIONAL: good, PITFALLS: good}

conventions:
  unit_system: "N/A"
  metric_signature: "N/A"
  fourier_convention: "N/A"
  coupling_convention: "N/A"
  renormalization_scheme: "N/A"

methods_ranked:
  - name: "Hypothesis stateful testing"
    regime: "Discrete finite state machines; 8 states, ~14 transitions"
    confidence: HIGH
    cost: "O(1) per transition check; 1000 examples in ~5 seconds"
    complements: "TLA+ for specification-level verification"
  - name: "Targeted fault injection (D1-D9)"
    regime: "Known fault classes; requires instrumented runtime"
    confidence: HIGH
    cost: "Per-task LLM API cost; 9 fault types x N runs"
    complements: "Clean runs for false-positive measurement"
  - name: "DAG reachability analysis"
    regime: "Provenance graphs with V < 1000, E < 5000; acyclic"
    confidence: HIGH
    cost: "O(V+E) per chamber; < 1 second"
    complements: "Content-hash comparison for semantic fidelity"
  - name: "Differential three-baseline comparison"
    regime: "Same task set across MockLM, uninstrumented, instrumented"
    confidence: HIGH
    cost: "3x task suite cost; 2-4 hours + $5-20 API"
    complements: "Positive/negative controls"
  - name: "Mutmut mutation testing"
    regime: "Pure logic modules; forge_nulls.py, forge_trace_codec.py, forge_reversible_summary.py"
    confidence: HIGH
    cost: "500-800 mutants x test suite; ~15 minutes"
    complements: "Code coverage as secondary metric"
  - name: "Bootstrap confidence intervals"
    regime: "Metrics with 5-30 data points"
    confidence: HIGH
    cost: "Negligible; 10000 resamples in milliseconds"
    complements: "Clopper-Pearson exact binomial for proportions"
  - name: "Round-trip hash verification"
    regime: "Structural dedup (forge trace codec); deterministic JSON serialization"
    confidence: HIGH
    cost: "O(n) in payload size; < 100ms per chamber"
    complements: "DAG reachability for semantic layer"

phase_suggestions:
  - name: "Ontology Formalization"
    goal: "Formally verify 8-state absence ontology with complete transition table and property-based tests"
    methods: ["Hypothesis stateful testing", "Mutmut mutation testing"]
    depends_on: []
    needs_research: false
    risk: LOW
    pitfalls: ["typed-absence-insufficient"]
  - name: "Integration and Baseline Establishment"
    goal: "Instrument Zarathustra with forge tools and establish three-tier baseline measurements"
    methods: ["Differential three-baseline comparison"]
    depends_on: ["Ontology Formalization"]
    needs_research: true
    risk: MEDIUM
    pitfalls: ["mockml-to-real-gap", "straw-man-baseline"]
  - name: "Violation Detection Measurement"
    goal: "Measure whether forge detects structural failures missed by uninstrumented and structured-logging baselines"
    methods: ["Targeted fault injection (D1-D9)", "Bootstrap confidence intervals", "Differential three-baseline comparison"]
    depends_on: ["Integration and Baseline Establishment"]
    needs_research: false
    risk: MEDIUM
    pitfalls: ["typed-absence-insufficient", "straw-man-baseline"]
  - name: "Compaction Survival Measurement"
    goal: "Measure provenance chain survival through real context-window compaction with structural and semantic reachability"
    methods: ["DAG reachability analysis", "Round-trip hash verification"]
    depends_on: ["Integration and Baseline Establishment", "Violation Detection Measurement"]
    needs_research: true
    risk: HIGH
    pitfalls: ["compaction-destroys-provenance", "provenance-over-referencing"]
  - name: "Cross-Reference and Synthesis"
    goal: "Integrate results across phases, compare against MockLM ceiling, assess all three RQs"
    methods: ["Bootstrap confidence intervals"]
    depends_on: ["Violation Detection Measurement", "Compaction Survival Measurement"]
    needs_research: false
    risk: LOW
    pitfalls: []

critical_benchmarks:
  - quantity: "MockLM provenance reachability"
    value: "1.0 (100%)"
    source: "experiment_results.json (local)"
    confidence: HIGH
  - quantity: "MockLM deliberate violation detection"
    value: "6/6 (100%)"
    source: "experiment_results.json (local)"
    confidence: HIGH
  - quantity: "MockLM trace compression vs vanilla"
    value: "87% (1.87x ratio)"
    source: "experiment_results.json (local)"
    confidence: HIGH
  - quantity: "Forge instrumentation overhead target"
    value: "< 10% wall time increase"
    source: "COMPUTATIONAL.md recommendation"
    confidence: MEDIUM
  - quantity: "Mutation score target for core modules"
    value: "> 0.85 (85% of mutants killed)"
    source: "METHODS.md recommendation"
    confidence: HIGH

open_questions:
  - question: "How does Zarathustra's compaction work internally (opaque API-level or transparent prompt-level)?"
    priority: HIGH
    blocks_phase: "Integration and Baseline Establishment"
  - question: "Can semantic reachability (content fidelity behind pruned_recoverable refs) be measured?"
    priority: HIGH
    blocks_phase: "Compaction Survival Measurement"
  - question: "How frequent are naturally-occurring structural violations in real agent workflows?"
    priority: MEDIUM
    blocks_phase: "none"
  - question: "Is the 8-state ontology sufficient, or should timed_out and interrupted be added?"
    priority: MEDIUM
    blocks_phase: "none"
  - question: "What is provenance metadata overhead as fraction of context budget under real pressure?"
    priority: MEDIUM
    blocks_phase: "none"
  - question: "How does provenance compose across multi-agent boundaries?"
    priority: LOW
    blocks_phase: "none"

contradictions_unresolved: []
```
