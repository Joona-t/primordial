# Methods Research

**Domain:** Typed absence, provenance tracking, and recoverable compaction in agentic systems
**Researched:** 2026-03-15
**Confidence:** MEDIUM-HIGH

## Scope Boundary

METHODS.md covers analytical and computational METHODS for validating typed absence ontology, provenance-preserving protocols, and recoverable compaction in agent runtimes. It does NOT cover software tools/libraries (see COMPUTATIONAL.md) or the research landscape (see PRIOR-WORK.md).

---

## Recommended Methods

### Formal Methods (Type Systems, Model Checking, Property-Based Testing)

| Method | Purpose | Why Recommended |
| --- | --- | --- |
| Hypothesis stateful testing (RuleBasedStateMachine) | Verify absence state machine transition legality under random exploration | Gold standard for Python state machine testing; generates adversarial input sequences automatically; finds edge cases unit tests miss |
| Mypy strict-optional + custom types | Static enforcement that absence states flow correctly through code paths | Catches forgotten None-checks at compile-time; integrates with existing Python workflow; zero runtime cost |
| TLA+ lightweight specification | Formally specify the 8-state absence ontology transition rules and verify invariants | Model checker exhaustively verifies safety/liveness properties over all reachable states; used by AWS for protocol verification at scale |

### Testing Methods (Mutation Testing, Fault Injection, Chaos Engineering)

| Method | Purpose | Why Recommended |
| --- | --- | --- |
| Mutmut mutation testing | Measure test suite adequacy for forge tools by injecting code mutations | Most actively maintained Python mutation tool; 1200 mutants/min; 88.5% detection rate benchmarked in 2025; directly answers "do our tests actually catch real bugs?" |
| Targeted fault injection (custom harness) | Inject specific structural failures into agent runtime state (missing refs, corrupted hashes, null-collapsed fields) | The 6 violation types already tested on MockLM define the injection taxonomy; extend to Zarathustra runtime for ecological validity |
| Chaos engineering for LLM-MAS (ReliabilityBench-style) | Inject transient timeouts, rate limits, partial responses, schema drift during agent execution | Recent research (arXiv:2601.06112) demonstrates that even epsilon=0.2 perturbation causes 8.8% degradation; directly relevant to testing compaction survival under stress |

### Instrumentation Methods (Runtime Tracing, Provenance DAGs, Logging)

| Method | Purpose | Why Recommended |
| --- | --- | --- |
| Provenance DAG reachability analysis | Measure fraction of artifacts whose ancestry chain reaches root after compaction | Directly measures the core claim (provenance survival); standard graph-theoretic method with well-defined metrics (reachability fraction, max reconstructable depth, orphan count) |
| Structured trace instrumentation (forge-native) | Record typed absence states, transitions, and provenance metadata at every stage boundary | Forge already implements this via forge_chamber.py and forge_stage_output.py; extend rather than replace |
| Differential instrumentation (forge vs. vanilla) | Run identical tasks with and without forge protocol, compare structural integrity of outputs | Already validated in MockLM experiment; the method itself is the experimental design for RQ2 |

### Validation Techniques (Benchmarks, Baselines, Statistical Comparison)

| Method | Purpose | Why Recommended |
| --- | --- | --- |
| Dual-baseline comparison (MockLM + uninstrumented Zarathustra) | Establish performance ceiling (MockLM: controlled) and floor (vanilla Zarathustra: uncontrolled) | Anchors all claims between known-good synthetic results and real-world baseline; prevents cherry-picking |
| Round-trip integrity verification | Verify that encode_trace -> decode_trace produces bitwise-identical output via SHA-256 hash comparison | Already implemented in forge_trace_codec.py; extend to cover compaction under real context pressure |
| Bootstrap confidence intervals for detection rates | Quantify uncertainty on violation detection rates and provenance reachability fractions | Small sample sizes (expected <50 naturally-occurring violations) require non-parametric statistics; bootstrap avoids distributional assumptions |

---

## Method Details

### Method 1: Hypothesis Stateful Testing for Absence Ontology

**What:** Use Hypothesis `RuleBasedStateMachine` to model the 8-state absence ontology as a state machine. Define rules for each legal transition (e.g., `not_invoked -> unresolved`, `resolved -> pruned_recoverable`). Define invariants that must hold after every step (e.g., "no field is in an undefined absence state"). Define preconditions that constrain when rules can fire. Hypothesis will generate thousands of random transition sequences and check that no invariant is violated.

**Mathematical basis:** The state machine has 8 states with ~11 legal transitions and ~3 explicitly illegal ones. Hypothesis explores the reachable state space by composing randomly-selected legal transitions and checking invariants after each step. The `@invariant` decorator runs after every rule application.

**Convergence:** Hypothesis explores up to `max_examples` paths (default 200, recommend 1000+). Each path is a variable-length sequence of transitions. Coverage is probabilistic, not exhaustive -- but with shrinking, any violation is reduced to a minimal reproducing example.

**Known failure modes:** (1) State explosion if states carry complex metadata -- mitigate by abstracting metadata to a simplified model. (2) Slow if rules involve I/O -- keep the model pure; test real implementation separately. (3) Does not find all invariant violations for infinite state spaces -- the 8 canonical states are finite, so this is manageable.

**Regime of validity:** Appropriate for the discrete, finite state machine of absence states. Not appropriate for continuous dynamics or timing-dependent properties (those need TLA+ or temporal logic).

**Implementation sketch:**

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, initialize
from hypothesis import settings

class AbsenceStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.state = "not_invoked"
        self.transition_log = []

    @initialize()
    def init_state(self):
        self.state = "not_invoked"

    @rule()
    @precondition(lambda self: self.state == "not_invoked")
    def invoke_to_unresolved(self):
        self.state = "unresolved"
        self.transition_log.append(("not_invoked", "unresolved"))

    @rule()
    @precondition(lambda self: self.state == "unresolved")
    def resolve(self):
        self.state = "resolved"
        self.transition_log.append(("unresolved", "resolved"))

    # ... additional legal transitions

    @invariant()
    def state_is_canonical(self):
        assert self.state in V1_ABSENCE_STATES

    @invariant()
    def no_illegal_transition(self):
        for src, dst in self.transition_log:
            assert (src, dst) not in ILLEGAL_TRANSITIONS

TestAbsenceStateMachine = AbsenceStateMachine.TestCase
TestAbsenceStateMachine.settings = settings(max_examples=1000, stateful_step_count=50)
```

**Computational cost:** ~1-5 seconds for 1000 examples with 50 steps each. Negligible.

**Benchmarks:** Hypothesis PBT finds ~50x more mutations than average unit tests (OOPSLA 2025 empirical study on 426 Python programs using Hypothesis).

### Method 2: Mutmut Mutation Testing for Test Suite Adequacy

**What:** Mutmut systematically mutates the forge tool source code (replacing operators, deleting statements, changing constants, mutating dict keys) and runs the test suite against each mutant. Surviving mutants indicate gaps in test coverage -- places where the code could be wrong and no test would notice.

**Mathematical basis:** Mutation score = killed_mutants / total_mutants. A mutation score of 1.0 means every single-point code change is detected by at least one test. The "competent programmer hypothesis" assumes real bugs are similar to syntactic mutations.

**Convergence:** N/A (deterministic process). Cost scales linearly with (number_of_mutants * test_suite_runtime). Mutmut generates ~1200 mutants/minute.

**Known failure modes:** (1) Equivalent mutants -- mutations that don't change behavior (e.g., reordering independent statements). These inflate the denominator artificially. Manual review required for ~5-15% of survivors. (2) Slow test suites make mutation testing expensive. The 103 existing tests are fast (pure Python, no I/O), so this is manageable.

**Regime of validity:** Appropriate for pure logic (forge_nulls.py, forge_trace_codec.py, forge_reversible_summary.py). Less meaningful for I/O-heavy orchestration code (forge_orchestrator.py) where mutations may produce timing-dependent failures.

**Implementation:**

```bash
# Target the core forge modules
mutmut run --paths-to-mutate=tools/forge_nulls.py,tools/forge_trace_codec.py,tools/forge_reversible_summary.py --tests-dir=tools/

# Review surviving mutants
mutmut results
mutmut show <mutant_id>
```

**Computational cost:** With 103 tests running in <1s total and ~500-800 mutants across the three core modules, expect 10-15 minutes wall time.

### Method 3: Targeted Fault Injection for Violation Detection (RQ2)

**What:** Extend the 6 existing MockLM violation tests (D1-D6) into a fault injection harness for the real Zarathustra runtime. Inject structural failures at specific points in the agent workflow: during stage registration, during compaction, during ref resolution.

**Fault taxonomy (from existing MockLM tests, extended):**

| Fault ID | Injection Point | What Breaks | Detection Expected By |
| --- | --- | --- | --- |
| D1 | Stage output | Empty output without typed absence | ForgeNullError |
| D2 | Summary creation | Summary without source_refs | ForgeRefError |
| D3 | Ref registration | Dangling reference to non-existent artifact | ForgeChamberError |
| D4 | Artifact registration | Duplicate artifact ID | ForgeChamberError |
| D5 | Post-seal mutation | Writing to sealed chamber | ForgeChamberError |
| D6 | Field validation | Raw null where typed state required | ForgeChamberError |
| D7 (new) | Compaction | Compacted artifact with broken recovery path | ForgeRefError or silent (the dangerous case) |
| D8 (new) | Context pressure | Forced compaction mid-chain drops intermediate provenance | Provenance reachability < 1.0 |
| D9 (new) | Timeout/interrupt | Agent timeout during subcall leaves unresolved state | Should become `unresolved` not `unknown` |

**Known failure modes:** (1) Fault injection in a real LLM runtime is non-deterministic -- the agent may work around the fault in unpredictable ways. Mitigation: run each injection multiple times and report detection rate with confidence interval. (2) Injecting faults into the context window itself (D8) requires instrumenting the runtime's compaction pathway, which may not be cleanly separable.

**Regime of validity:** Fault injection validates detection capability (false negatives). It does not validate false positive rate -- that comes from running the full protocol on correct (non-injected) traces and checking for spurious errors.

### Method 4: Provenance DAG Reachability Analysis

**What:** After each agent run (with or without compaction), construct the provenance DAG from artifact references. Measure:
- **Reachability fraction:** proportion of leaf artifacts whose ancestry chain reaches a root (initial input or not_invoked origin)
- **Max reconstructable depth:** longest chain from any compacted artifact back to its original source
- **Orphan count:** artifacts with broken provenance (no path to root)

**Mathematical basis:** Standard directed graph reachability. Given a DAG G = (V, E) where V = artifacts and E = source_ref edges: reachability(v) = 1 if exists path from v to any root node, 0 otherwise. Reachability fraction = sum(reachability(v)) / |V|.

**Convergence:** Exact computation via BFS/DFS. O(|V| + |E|) per run. No approximation needed for the expected graph sizes (tens to hundreds of nodes per agent run).

**Known failure modes:** (1) Semantic provenance gaps -- an artifact may have a syntactically valid ref chain but the intermediate summaries lost critical information. Reachability measures structural completeness, not semantic fidelity. (2) Self-referential or cyclic refs would break DAG assumptions -- validate acyclicity as a precondition.

**Implementation sketch:**

```python
def compute_reachability(artifacts: list[dict], roots: set[str]) -> dict:
    """Compute provenance reachability metrics for a set of artifacts."""
    # Build adjacency list from source_refs
    graph = {}
    for art in artifacts:
        art_id = art["id"]
        refs = [r["ref"] if isinstance(r, dict) else r
                for r in art.get("source_refs", [])]
        graph[art_id] = refs

    # BFS from each node toward roots
    reachable = {}
    for node in graph:
        visited = set()
        queue = [node]
        found_root = False
        while queue:
            current = queue.pop(0)
            if current in roots:
                found_root = True
                break
            if current in visited:
                continue
            visited.add(current)
            queue.extend(graph.get(current, []))
        reachable[node] = found_root

    fraction = sum(reachable.values()) / len(reachable) if reachable else 0.0
    orphans = [n for n, r in reachable.items() if not r]
    max_depth = max(len(visited) for visited in [...])  # compute per-node

    return {
        "reachability_fraction": fraction,
        "orphan_count": len(orphans),
        "orphan_ids": orphans,
        "total_artifacts": len(graph),
    }
```

**Computational cost:** Negligible. O(V+E) where V ~ 10-100, E ~ 10-200 per run.

### Method 5: Round-Trip Integrity Verification for Compaction

**What:** Verify that the encode/decode cycle in forge_trace_codec.py is lossless by comparing SHA-256 hashes of pre-compression and post-decompression data. Already implemented -- the method here is to extend it to cover real context-pressure compaction (not just structural dedup).

**Mathematical basis:** SHA-256 collision resistance provides 2^128 security against accidental collisions. If hash(decode(encode(data))) == hash(data), the round-trip is lossless with overwhelming probability.

**Key distinction -- two kinds of compaction:**
1. **Structural dedup** (forge_trace_codec.py): Lossless, verified by hash. Already works at 87% compression vs. vanilla logger.
2. **Semantic compaction** (forge_reversible_summary.py): Lossy by design -- summaries discard detail. Verified not by hash equality but by provenance reachability: can we get back to the original artifact?

The project must measure BOTH and keep their metrics separate. Conflating them would invalidate the results.

**Regime of validity:** Hash-based integrity is definitive for structural compaction. For semantic compaction, the "lossless" claim is weaker: we verify structural path existence (can you navigate back?), not content preservation (is the summary faithful?).

### Method 6: Bootstrap Confidence Intervals for Small-Sample Statistics

**What:** Given that the number of naturally-occurring violations in a reasonable Zarathustra test campaign may be small (perhaps 5-50), use bootstrap resampling to construct confidence intervals on detection rates and reachability fractions rather than relying on normal-distribution assumptions.

**Mathematical basis:** Draw B bootstrap samples (B=10000) with replacement from the observed data. Compute the statistic of interest on each sample. The 2.5th and 97.5th percentiles of the bootstrap distribution form a 95% confidence interval.

**When to use:** Any metric with fewer than ~30 data points. Specifically: violation detection rates, provenance reachability fractions per run, compression ratios across runs.

**Known failure modes:** Bootstrap can be unreliable with very small samples (N < 5). If the test campaign produces fewer than 5 naturally-occurring violations, report exact counts rather than rates with confidence intervals.

**Computational cost:** Negligible. 10000 resamples of a 50-element array takes milliseconds.

### Method 7: Differential Testing (Instrumented vs. Uninstrumented Baselines)

**What:** Run identical task sets on three configurations: (1) Zarathustra + forge protocol, (2) Zarathustra without forge (vanilla baseline), (3) MockLM + forge (controlled ceiling). Compare violation detection, provenance reachability, and compression metrics across all three.

**Mathematical basis:** This is a controlled experiment with three treatment arms. The key comparison is (1) vs. (2) for "does forge detect violations that go undetected without it?" The anchor comparison is (1) vs. (3) for "how does real runtime degrade from the controlled ceiling?"

**Task set requirements:**
- Must include tasks long enough to trigger genuine context-window compaction (>50K tokens of accumulated state)
- Must include recursive subcall chains (depth >= 2) to exercise provenance tracking
- Must include at least one deliberate fault injection per run for positive control
- Must include clean runs for false-positive measurement

**Known failure modes:** (1) Task set too easy -- short tasks never trigger compaction. Prevention: pre-validate that tasks exceed compaction threshold. (2) Non-deterministic agent behavior makes runs non-comparable. Prevention: run each task N times (N >= 5) and report distributions, not single values. (3) Forge overhead changes agent behavior, invalidating comparison. Prevention: measure and report overhead separately.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
| --- | --- | --- | --- |
| State machine verification | Hypothesis stateful + TLA+ spec | Alloy model finder | Alloy is less expressive than TLA+ for protocol properties; Python integration is poor; the 8-state ontology is small enough for TLA+ model checking |
| Mutation testing | Mutmut | Cosmic Ray | Cosmic Ray has broader operator set but slower execution; Mutmut's 88.5% detection rate exceeds Cosmic Ray's 82.7% on Python-specific mutations (2025 benchmarks) |
| Provenance analysis | Custom DAG reachability on forge structures | W3C PROV-O ontology | W3C PROV is designed for interoperability across heterogeneous systems; overkill for a single-runtime validation; forge's native ref structure is simpler and sufficient |
| Statistical method | Bootstrap CI | Fisher's exact test | Fisher's is appropriate for 2x2 contingency tables (detected/not x forge/vanilla), but bootstrap handles the continuous metrics (reachability fraction, compression ratio) that Fisher's cannot |
| Fault injection | Custom targeted harness (D1-D9) | Generic chaos framework (e.g., Chaos Monkey) | Generic chaos tools inject infrastructure faults (kill pods, drop network); we need semantic faults (corrupt a ref, null-collapse a field, break a hash). Custom harness is unavoidable. |
| Runtime tracing | Extend existing forge instrumentation | OpenTelemetry auto-instrumentation | OTel provides excellent generic observability but does not understand forge protocol semantics (absence states, provenance refs, chamber sealing). The forge-native instrumentation already carries the right metadata. OTel is useful as a complementary transport layer, not a replacement for domain-specific tracing. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
| --- | --- | --- |
| Generic fuzzing (AFL, libFuzzer) for protocol testing | Forge protocols operate on structured JSON dicts, not byte streams; generic fuzzers waste cycles on syntactically invalid inputs | Hypothesis with custom strategies that generate valid-but-adversarial protocol messages |
| Full formal verification (Coq, Isabelle) | The 8-state ontology is small enough that TLA+ model checking is exhaustive for safety properties; theorem provers add months of effort for marginal gain over model checking | TLA+ for invariant checking; Hypothesis for implementation testing |
| Code coverage as test adequacy metric | Coverage tells you what code was executed, not whether the tests actually check anything meaningful. 100% coverage with zero assertions is useless. | Mutation score (mutmut) as the primary test adequacy metric; coverage as a secondary sanity check |
| Monte Carlo sampling for graph reachability | The provenance DAGs are small (10-100 nodes); exact BFS/DFS is trivial and provides exact answers | Exact BFS/DFS reachability computation |
| Normal-distribution confidence intervals | Detection rates with small N violate normality assumptions; Wald intervals can produce impossible values (<0 or >1) | Bootstrap confidence intervals or exact binomial (Clopper-Pearson) for proportions |

---

## Method Selection by Problem Type

**If verifying absence state machine correctness (RQ1: ontology formalization):**

- Use Hypothesis `RuleBasedStateMachine` for implementation testing
- Use TLA+ for specification-level verification of transition legality
- Because: Together they cover both "does the spec allow only legal transitions?" (TLA+) and "does the code correctly implement the spec?" (Hypothesis)

**If measuring violation detection capability (RQ2: forge vs. vanilla):**

- Use targeted fault injection (D1-D9) with differential testing across three baselines
- Use bootstrap CI for quantifying detection rates
- Because: Fault injection provides controlled positive signals; differential testing isolates the forge protocol's contribution; bootstrap handles small samples honestly

**If measuring provenance survival through compaction (RQ3: compaction recoverability):**

- Use DAG reachability analysis after real context-pressure compaction
- Use round-trip hash verification for structural compaction
- Use provenance reachability fraction as the primary metric
- Because: Structural integrity (hash) and provenance integrity (reachability) are complementary; both must survive for the compaction claim to hold

**If assessing test suite quality (supporting all RQs):**

- Use mutmut mutation testing on the three core forge modules
- Target mutation score > 0.85 (85% of mutants killed)
- Because: Mutation score directly measures whether the test suite would catch real code defects; this is the quality gate for trusting experimental results

---

## Validation Strategy by Method

| Method | Validation Approach | Key Benchmarks |
| --- | --- | --- |
| Hypothesis stateful testing | Run 1000+ examples; verify all illegal transitions raise errors; verify all invariants hold | All 3 illegal transitions (deleted->resolved, not_invoked->invalid, deleted->pruned_recoverable) detected; all 11 legal transitions exercised |
| Mutmut mutation testing | Score >= 0.85; review all surviving mutants manually for equivalence | 103 existing tests should kill majority; add tests for any non-equivalent survivors |
| Fault injection (D1-D9) | Each fault detected on MockLM (positive control); measure detection rate on Zarathustra | MockLM: 6/6 detected (existing result); Zarathustra: target >= 4/6 on original faults, report new faults D7-D9 |
| DAG reachability | MockLM: 100% reachability (existing result); measure degradation under real compaction | Acceptance: reachability measured and any gaps explained per PROJECT.md scoping contract |
| Round-trip hash verification | Bitwise match after encode/decode cycle | Already verified in MockLM experiment; must hold on real runtime traces |
| Bootstrap CI | Verify CI coverage by simulation: generate known-distribution data, check that 95% CI covers true value 95% of the time | Standard bootstrap validation; well-established |
| Differential testing | Positive control (injected faults detected) + negative control (clean runs have zero false positives) | False positive rate < 5% on clean runs; detection rate reported with CI |

---

## Software Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
| --- | --- | --- | --- |
| Python | 3.11+ | Primary implementation language | Matches existing forge tools; entire prototype is Python |
| pytest | 8.x | Test runner and fixture framework | Standard Python testing; better than unittest for parameterized tests and fixtures |
| Hypothesis | 6.x | Property-based and stateful testing | Only Python PBT library with first-class state machine support; actively maintained |
| Mutmut | 3.x | Mutation testing | Most active Python mutation tool; fastest mutant generation (1200/min) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
| --- | --- | --- | --- |
| numpy | 1.26+ | Bootstrap resampling and basic statistics | Computing confidence intervals on metrics |
| networkx | 3.x | Provenance DAG construction and reachability analysis | Graph algorithms for provenance analysis; overkill but well-tested for correctness |
| mypy | 1.8+ | Static type checking with strict-optional | CI pipeline for catching absence-state type errors statically |

### Symbolic/Formal Tools

| Tool | Version | Purpose | Notes |
| --- | --- | --- | --- |
| TLA+ Toolbox / Apalache | 0.44+ | Model checking the absence ontology specification | Write spec once; model checker verifies all reachable states. Use for specification, not implementation. Optional -- only if formalizing the ontology is prioritized. |

---

## Installation

```bash
# Core computational environment (all tools are pip-installable)
pip install pytest hypothesis mutmut mypy numpy networkx

# Optional: TLA+ toolbox (requires Java)
# brew install --cask tla-plus-toolbox  # macOS
```

---

## Version Compatibility

| Tool A | Compatible With | Notes |
| --- | --- | --- |
| Hypothesis 6.x | pytest 8.x | Fully compatible; use `hypothesis.settings` for configuration |
| Mutmut 3.x | pytest 8.x | Mutmut runs pytest as subprocess; compatible with any pytest version |
| mypy 1.8+ | Python 3.11+ | Use `--strict --strict-optional` flags |
| networkx 3.x | Python 3.11+ | Stable API for graph algorithms |

---

## Sources

- [Hypothesis stateful testing documentation](https://hypothesis.readthedocs.io/en/latest/stateful.html) -- RuleBasedStateMachine API, rule/precondition/invariant decorators (HIGH confidence)
- [An Empirical Evaluation of Property-Based Testing in Python](https://2025.splashcon.org/details/OOPSLA/102/An-Empirical-Evaluation-of-Property-Based-Testing-in-Python) -- OOPSLA 2025, 426 Python programs, PBT finds ~50x more mutations than unit tests (HIGH confidence)
- [Static and Dynamic Comparison of Mutation Testing Tools for Python](https://dl.acm.org/doi/10.1145/3701625.3701659) -- SBQS 2024, comparative benchmark of Mutmut, Cosmic Ray, MutPy, Mutatest (HIGH confidence)
- [Hybrid Fault-Driven Mutation Testing for Python](https://arxiv.org/html/2601.19088v1) -- January 2026, advances in Python mutation testing (MEDIUM confidence)
- [ReliabilityBench: Evaluating LLM Agent Reliability](https://arxiv.org/pdf/2601.06112) -- Chaos engineering framework for agent systems, 1280 episodes, perturbation analysis (MEDIUM confidence)
- [Assessing and Enhancing the Robustness of LLM-based Multi-Agent Systems Through Chaos Engineering](https://arxiv.org/abs/2505.03096) -- Fault types: hallucinations, agent failures, communication failures (MEDIUM confidence)
- [Contextual Memory Virtualisation: DAG-Based State Management](https://www.researchgate.net/publication/401279945) -- DAG-based state management with structurally lossless trimming for LLM agents (MEDIUM confidence)
- [Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents](https://blog.jetbrains.com/research/2025/12/efficient-context-management/) -- NeurIPS 2025, observation masking vs. LLM summarization (MEDIUM confidence)
- [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf) -- TLA+ for protocol verification at production scale (HIGH confidence)
- [W3C PROV Data Model](https://www.w3.org/TR/prov-dm/) -- Standard provenance ontology; reference point for forge's simpler approach (HIGH confidence)
- Existing forge experiment_results.json -- MockLM benchmark: 100% provenance, 6/6 violations, 87% compression (HIGH confidence, local data)

---

_Methods research for: Typed absence, provenance, and recoverable compaction in agentic systems_
_Researched: 2026-03-15_
