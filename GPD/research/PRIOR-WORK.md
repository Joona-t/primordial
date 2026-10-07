# Prior Work: Typed Absence, Provenance, and Recoverable Compaction in Agentic Systems

**Surveyed:** 2026-03-15
**Domain:** Formal systems / Agent architectures / Type theory / Data provenance / Context management
**Confidence:** MEDIUM (cross-disciplinary synthesis; individual threads are well-established but the specific combination is novel)

## Key Results

| Result | Expression / Value | Conditions | Source | Year | Confidence |
|---|---|---|---|---|---|
| Null references cause systemic failures at scale | "Billion-dollar mistake" -- systemic type-safety violations from untyped absence | All languages with null references (ALGOL W onward) | Hoare, QCon London keynote | 2009 | HIGH |
| Option/Maybe types eliminate null-pointer exceptions at compile time | `Option<T> = Some(T) \| None` enforced by type checker | Languages with algebraic data types (Rust, Haskell, OCaml, Scala) | ML (1973), Haskell (1990), Rust (2015) | 1973+ | HIGH |
| W3C PROV provides a standard ontology for provenance | Entity-Activity-Agent triad with derivation, delegation, attribution relations | Requires consistent instrumentation at entity boundaries | W3C PROV-DM / PROV-O Recommendation | 2013 | HIGH |
| LLMs suffer "lost in the middle" degradation | 30%+ accuracy drop when relevant info is in middle of long context | Multi-document QA, key-value retrieval tasks; 20-doc contexts | Liu et al., TACL 2024 (arXiv:2307.03172) | 2024 | HIGH |
| MemGPT achieves virtual context via OS-inspired paging | Two-tier memory (main + external) with self-editing via tool use | Requires function-calling capable LLM; overhead from memory management calls | Packer et al. (arXiv:2310.08560) | 2023 | HIGH |
| ACON reduces long-horizon agent memory 26-54% | Guideline-optimized compression preserving 95% accuracy on distillation | Long-horizon tasks (50-250 steps); requires paired success/failure trajectories for optimization | Kang et al. (arXiv:2510.00615) | 2025 | MEDIUM |
| Silent hallucinations are a distinct failure class in agentic AI | Internally generated false beliefs that propagate without user-visible signals | Multi-step autonomous workflows with tool use | OpenReview (ICLR 2026 submission) | 2025 | MEDIUM |
| Silent failure detection achieves 96-98% accuracy via trajectory analysis | XGBoost: 98%, SVDD: 96% on curated agentic trajectory datasets (4275 + 894 traces) | Requires labeled trajectory data; supervised and semi-supervised approaches | Pathak et al. (arXiv:2511.04032) | 2025 | MEDIUM |
| Agent Contracts formalize resource-bounded execution | Tuple C=(I,O,S,R,T,Phi,Psi) unifying specs, resources, temporal bounds, success criteria | 90% token reduction, 525x lower variance in iterative workflows | Ye et al. (arXiv:2601.08815) | 2026 | MEDIUM |
| Hoare logic provides the foundational formalism for pre/post-condition verification | {P} C {Q} -- precondition P, command C, postcondition Q | Partial correctness only; total correctness requires separate termination proof | Hoare, CACM 1969 | 1969 | HIGH |
| Irreversible information erasure has a thermodynamic cost | Erasing n bits costs at least nkT ln(2) in entropy | Applies to logically irreversible operations (many-to-one mappings) | Landauer, IBM J. Res. Dev. 1961; Bennett, Studies in History and Philosophy of Modern Physics 2003 | 1961 | HIGH |
| MockLM prototype: 100% provenance, 6/6 violations, 87% compression | Full reachability, all deliberate violations caught, ~87% size reduction vs vanilla | Controlled MockLM environment; no real context pressure or genuine LLM nondeterminism | Primordial project (this repo), experiment_results.json | 2025 | HIGH (for controlled conditions) |

## Foundational Work

### Hoare (1969) - An Axiomatic Basis for Computer Programming

**Key contribution:** Established the formal framework for reasoning about program correctness through preconditions, postconditions, and invariants. The Hoare triple {P} C {Q} provides the template for specifying what must be true before and after a computation.

**Method:** Axiomatic semantics with inference rules for composition, conditionals, and iteration.

**Limitations:** Proves partial correctness only (if the program terminates, the postcondition holds). Total correctness requires a separate termination argument. Does not address nondeterministic or concurrent systems without extensions.

**Relevance:** The forge tools' state-transition rules (legal/illegal transitions between absence states) are a domain-specific instantiation of Hoare-style contracts. Each transition has implicit preconditions (the current state) and postconditions (the target state plus required metadata). The formal verification approach for validating forge protocol compliance maps directly to this framework.

### Hoare (2009) - Null References: The Billion Dollar Mistake

**Key contribution:** Hoare's retrospective admission that introducing null references into ALGOL W (1965) was a fundamental error. The null reference conflates "absence of value" with "presence of an invalid reference," creating a class of errors that type systems cannot prevent.

**Method:** Retrospective analysis and industry damage assessment.

**Limitations:** The talk identified the problem but did not propose a specific multi-state replacement ontology -- only the binary Option/Maybe type was established as the standard remedy.

**Relevance:** This is the intellectual origin point for the primordial project's core claim. Hoare identified that null conflates distinct absence semantics. The primordial project extends this insight from binary (Some/None) to an 8-state ontology tailored for agent computation. The key advance is recognizing that even Option types are insufficient when the *reason* for absence carries operational meaning (not_invoked vs unknown vs deleted vs pruned_recoverable).

### Milner et al. (1973+) - ML and the Option/Maybe Type

**Key contribution:** The ML programming language (1973) introduced algebraic data types that enabled the Option pattern. Haskell (1990) standardized this as `Maybe a = Just a | Nothing`. Rust (2015) made it mainstream with `Option<T>` and compile-time enforcement.

**Method:** Algebraic data types with pattern matching. The compiler requires exhaustive case analysis, preventing unhandled absence.

**Limitations:** Option/Maybe is binary -- a value is either present or absent. It does not distinguish *kinds* of absence. Monadic chaining (`flatMap`/`>>=`) propagates None without explaining why. The type system cannot encode "absent because deleted" vs "absent because never invoked" vs "absent because pruned but recoverable."

**Relevance:** Option types solve the *type safety* problem (no null-pointer exceptions) but not the *semantic truthfulness* problem that primordial addresses. The 8-state ontology is a domain-specific extension of Option that adds provenance-relevant semantics to absence. This is a genuine extension of the prior art, not a rediscovery.

### Meyer (1986) - Design by Contract (Eiffel)

**Key contribution:** Operationalized Hoare logic into a practical programming paradigm where classes carry executable preconditions, postconditions, and class invariants. Contracts are checked at runtime, providing both documentation and enforcement.

**Method:** Embedded assertions in the Eiffel language with runtime checking and inheritance rules for contract strengthening/weakening.

**Limitations:** Runtime checking only (not compile-time proofs). Contract violations detected at point of failure, not at point of cause. No provenance -- when a postcondition fails, you know *what* failed but not the causal chain.

**Relevance:** The forge tools' validation layer (validate_record, validate_field) is functionally a Design by Contract system for agent artifacts. The innovation is that the contracts enforce *absence-type correctness* rather than value-range correctness. The transition rules between absence states are invariants in Meyer's sense.

### W3C (2013) - PROV Data Model and PROV-O Ontology

**Key contribution:** Standardized a domain-independent model for representing provenance. Three core types: Entity (things with provenance), Activity (things that happen), Agent (things responsible for activities). Six core relations: wasGeneratedBy, used, wasAttributedTo, wasDerivedFrom, wasAssociatedWith, actedOnBehalfOf.

**Method:** Formal ontology in OWL2, with serializations in RDF, JSON, and XML.

**Limitations:** General-purpose -- does not model absence states, compaction, or context-window-specific concerns. No concept of "pruned_recoverable" or grounded return paths. Entity lifecycle is simpler (generated, used, invalidated) than the 8-state ontology. Does not address the cost of provenance tracking under resource constraints.

**Relevance:** PROV provides the closest existing standard for what forge_trace_codec.py implements. The forge provenance chain (parent_id, source_refs, artifact hashes) is a domain-specific projection of PROV's derivation and generation relations. Key difference: forge provenance is designed to survive compaction, while PROV assumes the provenance graph is persistent and fully addressable. PROV-AGENT (2025 extension) brings this closer to agent-specific workflows but still lacks absence typing.

### Packer et al. (2023) - MemGPT: Towards LLMs as Operating Systems

**Key contribution:** Introduced virtual context management for LLM agents, drawing analogy from OS virtual memory with paging. The LLM manages its own context window through function calls that move data between "main context" (in-window) and "external context" (out-of-window archival/recall memory).

**Method:** Two-tier memory hierarchy with self-directed paging. The LLM decides what to evict and what to retrieve, using function calls as the paging mechanism.

**Limitations:** The LLM's self-management of context introduces its own failure modes -- the model may page out important information or fail to retrieve it. No formal guarantee of what survives compaction. No typed absence -- paged-out information simply becomes inaccessible until explicitly retrieved. No provenance chain linking compacted summaries back to source material. Performance degrades with very long conversations as the management overhead grows.

**Relevance:** MemGPT solves the *mechanism* of context management (how to page) but not the *semantics* (what was lost and whether it can be recovered). The primordial project's recoverable compaction addresses exactly this gap. Where MemGPT says "this was paged out," primordial says "this was pruned_recoverable with source_refs=[...] and recovery_path=[...]." The combination of MemGPT-style paging with forge-style provenance tracking would be the ideal architecture.

### Liu et al. (2023/2024) - Lost in the Middle: How Language Models Use Long Contexts

**Key contribution:** Demonstrated that LLM performance on information retrieval tasks degrades significantly when relevant information is positioned in the middle of long contexts, rather than at the beginning or end. Measured 30%+ accuracy drop on multi-document QA.

**Method:** Controlled experiments on multi-document QA and key-value retrieval with varying document position.

**Limitations:** Focused on retrieval tasks, not generation or reasoning. Newer models (GPT-4-turbo, Claude 3+) show improved but not eliminated middle-degradation. The effect varies with task type.

**Relevance:** Directly motivates the compaction problem. If LLMs degrade on middle-positioned information, then long agent traces will lose effective access to mid-session context even before explicit compaction occurs. This means compaction is not just a token-budget concern but an *attention-quality* concern. Typed absence (marking information as pruned_recoverable vs simply invisible due to attention degradation) gives the system a way to distinguish "I compacted this intentionally" from "this information is present but I cannot effectively attend to it."

### Kang et al. (2025) - ACON: Optimizing Context Compression for Long-Horizon LLM Agents

**Key contribution:** Framework for dynamically compressing environment observations and interaction histories for long-horizon agents. Uses guideline optimization: given paired trajectories where full context succeeds but compressed context fails, an LLM analyzes failure causes and updates compression guidelines.

**Method:** Natural-language guideline optimization pipeline. Compresses observations selectively based on task-specific importance. Can distill the compression policy into smaller models.

**Limitations:** Compression is lossy and task-optimized -- the guidelines are tuned for specific task types. No formal guarantee of information preservation. No provenance linking compressed output back to original observations. No typed absence -- compressed-away information simply disappears from the context.

**Relevance:** ACON demonstrates the state-of-the-art in agent context compression without provenance. Achieves 26-54% memory reduction but with no guarantee that compacted information can be recovered or traced. The primordial project's forge_reversible_summary.py addresses exactly this gap -- compaction with grounded return paths. The 87% compression achieved by the forge tools on MockLM suggests that provenance-preserving compaction can be competitive with or superior to provenance-destroying compression.

## Recent Developments

| Paper | Authors | Year | Advance | Impact on Our Work |
|---|---|---|---|---|
| "Tiny" Silent Hallucinations in Agentic AI | (OpenReview submission) | 2025 | Formalizes silent hallucinations as system-level reliability problem; identifies compounding downstream effects | Validates our RQ2 -- typed absence and provenance are a structural defense against exactly this failure mode. Silent hallucinations thrive when absence is untyped. |
| Detecting Silent Failures in Multi-Agentic AI Trajectories | Pathak et al. | 2025 | First systematic study of anomaly detection in multi-agent traces; curated benchmark datasets; 96-98% detection accuracy | Provides detection baselines for comparison. Our approach is structural (protocol-level) rather than statistical (trajectory analysis). Both are complementary. |
| Agent Contracts: Formal Framework for Resource-Bounded AI | Ye et al. | 2026 | Formal tuple (I,O,S,R,T,Phi,Psi) for agent governance; 90% token reduction; conservation laws for delegated budgets | Closest formal framework to our approach. Agent Contracts govern resource bounds; our work governs state semantics. These are orthogonal and composable. |
| Agent Behavioral Contracts | (arXiv:2602.22302) | 2026 | Runtime enforcement of behavioral specifications for autonomous agents | Extends contract idea to behavioral (not just resource) specifications. Our state-transition rules are a specific kind of behavioral contract. |
| Audit Trails for Accountability in LLMs | (arXiv:2601.20727) | 2026 | Hash-chain-backed audit trails for LLM interactions | Validates the provenance approach. Our forge_trace_codec.py implements artifact-level hashing; this work does interaction-level hashing. |
| AuditableLLM: Hash-Chain Compliance Framework | Electronics 15(1):56 | 2025 | Decoupled audit layer with tamper-evident logging | Parallel development to our approach. Their hash chains verify interaction integrity; our provenance chains verify artifact lineage. |
| Prompt Provenance Model (PPM) | Procko et al. | 2025 | W3C PROV extended for prompt/completion lineage | Bridges PROV into LLM space. Our work extends further by adding typed absence states to provenance nodes. |
| PROV-AGENT | (emergentmind) | 2025 | W3C PROV extended with agent-centric entities and LLM telemetry | Most relevant PROV extension for our domain. Does not address absence typing or compaction recoverability. |
| LLM Agents for Interactive Workflow Provenance | (arXiv:2509.13978) | 2025 | Agent architecture for runtime provenance capture across workflows | Demonstrates feasibility of runtime provenance in agent systems. Does not address what happens when provenance chains are compacted. |
| JetBrains Context Management Research | JetBrains Research Blog | 2025 | Systematic comparison of observation masking vs LLM summarization for agent context | Identifies the core tradeoff our work addresses: masking preserves fidelity but grows unbounded; summarization is bounded but lossy. |

## Known Limiting Cases

| Limit | Known Result | Source | Verified By |
|---|---|---|---|
| Binary absence (Option/Maybe) | Eliminates null-pointer exceptions; insufficient for semantic absence distinctions | ML (1973), Haskell (1990), Rust (2015) | Decades of PL research |
| Zero compaction (full trace retention) | Perfect provenance and recoverability; grows without bound; hits context window limits | Trivially true | First principles |
| Full compaction (summary-only) | Bounded memory; destroys provenance; vulnerable to "lost in the middle" even before compaction | Liu et al. 2024; ACON (Kang et al. 2025) | Empirical measurement |
| Controlled environment (MockLM) | 100% provenance reachability, 6/6 violations detected, 87% compression | This project (experiment_results.json) | 103 passing tests |
| No instrumentation baseline | 0/6 violations detected by vanilla logging | This project (vanilla_baseline_results.json) | Direct comparison |

## Open Questions

1. **Sufficiency of 8 states** -- Is the current ontology (not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable, resolved) sufficient for real agent workflows? The docs already flag timed_out and interrupted as candidates. Real Zarathustra runs may surface additional absence modes not anticipated by the MockLM experiment.

2. **Provenance cost under real context pressure** -- The MockLM experiment showed 87% compression, but MockLM never hit genuine context limits. Under real 128K-200K token contexts with forced compaction, provenance metadata itself consumes tokens. What is the overhead of provenance preservation as a fraction of the available context budget?

3. **Compaction recoverability semantics** -- Should recoverability be binary (recoverable / not recoverable) or graded (full recovery / partial recovery / summary-only recovery / metadata-only recovery)? The current ontology uses binary (pruned_recoverable vs deleted), but real compaction may produce intermediate states.

4. **Interaction with attention degradation** -- "Lost in the middle" effects mean information can be effectively absent even when nominally present in context. Should the absence ontology have a state for "present but attention-degraded"? Or is this an orthogonal concern?

5. **State assignment correctness** -- The ontology's value depends on correct state assignment. Who/what assigns absence states in a real agent runtime? If the LLM itself must choose between not_invoked and unknown, the assignment may be unreliable. This is the "quis custodiet" problem for typed absence.

6. **Compositionality of provenance** -- When agent A calls agent B which calls tool C, and B's context is compacted, what happens to A's provenance chain? The forge tools handle single-agent traces; multi-agent provenance composition is an open problem per PROV-AGENT research.

7. **False positive rate** -- The MockLM experiment caught 6/6 deliberate violations with 0 false positives. Real agent workflows are noisier. What is the false positive rate of typed-absence enforcement on real (non-deliberately-corrupted) agent traces?

## Notation Conventions in the Literature

| Quantity | Standard Symbol(s) | Variations | Our Choice | Reason |
|---|---|---|---|---|
| Absence/null state | `null`, `None`, `Nothing`, `nil`, `undefined` | Language-dependent; semantics vary wildly | `AbsenceState` enum with 8 members | Explicit enumeration avoids ambiguity |
| Provenance relation | `wasDerivedFrom` (PROV), `parent_id` (trace systems) | PROV uses formal RDF relations; most systems use ad-hoc parent pointers | `parent_id` + `source_refs` | Simpler than full PROV; sufficient for single-runtime lineage |
| Provenance reachability | Not standardized | PROV uses graph reachability; some systems use "depth" | `provenance_reachability_fraction` = (reachable artifacts) / (total artifacts) | Directly measurable; maps to the project's core metric |
| Context compaction | "summarization", "compression", "eviction", "paging" | MemGPT: "paging"; ACON: "compression"; LangChain: "summarization" | "compaction" | Emphasizes both reduction and potential recoverability; distinguishes from lossy summarization |
| Violation | "error", "fault", "anomaly", "failure", "hallucination" | Varies by community; SE uses "fault/error/failure" chain; AI uses "hallucination" | "structural violation" | Specific to protocol violation (state-transition illegality), not to content correctness |

## Theoretical Framework

### Governing Theory

This project sits at the intersection of three established fields, each contributing a specific formalism:

| Framework | Scope | Key Concepts | Regime of Validity |
|---|---|---|---|
| Type theory / algebraic data types | Classification of absence | Sum types, pattern matching, exhaustive case analysis | Compile-time or validation-time enforcement |
| Data provenance (W3C PROV) | Lineage tracking | Entity-Activity-Agent, derivation, generation, invalidation | Requires consistent instrumentation; degrades under partial coverage |
| Reversible/recoverable computation | Information-preserving compaction | Landauer's principle, bijective mappings, grounded references | Applies when compaction preserves sufficient metadata for reconstruction |

### Mathematical Prerequisites

| Topic | Why Needed | Key Results | References |
|---|---|---|---|
| Finite state machines | State-transition rules for absence ontology | Reachability analysis, invariant checking | Hopcroft, Motwani & Ullman (2006) |
| Graph reachability | Provenance chain analysis | BFS/DFS from any artifact to root; orphan detection | Standard algorithms |
| Information theory | Compaction bounds | Shannon entropy, Kolmogorov complexity, rate-distortion theory | Cover & Thomas (2006) |
| Hoare logic | Contract correctness | Hoare triples, weakest preconditions, loop invariants | Hoare (1969); Dijkstra (1975) |

### Symmetries and Conservation Laws (by analogy)

| Property | Conserved Quantity | Implications for Methods |
|---|---|---|
| Provenance completeness | Every artifact has a reachable root | No orphan artifacts after any operation including compaction |
| State-transition legality | Absence state transitions follow the legal graph | No illegal transitions (e.g., deleted -> resolved without explicit restoration) |
| Compaction grounding | Every pruned_recoverable artifact has source_refs | No ungrounded summaries; recovery path must be verifiable |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|---|---|---|---|
| Absence representation | 8-state typed ontology | Binary Option/Maybe | Insufficient semantic granularity for agent runtime needs (cannot distinguish "never ran" from "ran but failed" from "ran but was pruned") |
| Absence representation | 8-state typed ontology | Unconstrained string tags | No type safety; no transition rules; impossible to verify invariants |
| Provenance model | Lightweight parent_id + source_refs | Full W3C PROV-O graph | PROV-O's RDF overhead is excessive for real-time agent instrumentation; the full ontology is broader than needed |
| Provenance model | Lightweight parent_id + source_refs | No provenance (log-only) | Vanilla logging proved 0/6 violation detection vs 6/6 with forge (per MockLM experiment) |
| Compaction approach | Provenance-preserving reversible summary | Summary-only (destroy source refs) | Destroys recoverability; the core hypothesis of RQ3 |
| Compaction approach | Provenance-preserving reversible summary | No compaction (retain everything) | Unbounded growth; hits context window limits; attention degradation on long contexts |
| Violation detection | Structural protocol enforcement (typed absence + transition rules) | Statistical trajectory analysis (Pathak et al.) | Statistical approaches require labeled training data; structural enforcement works from first principles. Complementary, not competing. |
| Violation detection | Structural protocol enforcement | Hash-chain integrity only (AuditableLLM) | Hash chains detect tampering but not semantic violations (e.g., wrong absence state assignment) |

## Sources

- Hoare, C.A.R. (1969). "An Axiomatic Basis for Computer Programming." CACM 12(10):576-580. -- Foundation for contract-based verification
- Hoare, C.A.R. (2009). "Null References: The Billion Dollar Mistake." QCon London keynote. -- Motivates typed absence
- Meyer, B. (1986). "Design by Contract." Technical Report TR-EI-12/CO, ISE. -- Operationalized Hoare logic into executable contracts
- Landauer, R. (1961). "Irreversibility and Heat Generation in the Computing Process." IBM J. Res. Dev. 5(3):183-191. -- Thermodynamic cost of information erasure; motivates reversible compaction
- Bennett, C.H. (2003). "Notes on Landauer's Principle, Reversible Computation, and Maxwell's Demon." Studies in History and Philosophy of Modern Physics 34(3):501-510. -- Reversible computation theory
- W3C (2013). "PROV-DM: The PROV Data Model." W3C Recommendation. https://www.w3.org/TR/prov-dm/ -- Standard provenance ontology
- W3C (2013). "PROV-O: The PROV Ontology." W3C Recommendation. https://www.w3.org/TR/prov-o/ -- OWL2 encoding of PROV
- Liu, N.F. et al. (2024). "Lost in the Middle: How Language Models Use Long Contexts." TACL 2024. arXiv:2307.03172. -- Attention degradation in long contexts
- Packer, C. et al. (2023). "MemGPT: Towards LLMs as Operating Systems." arXiv:2310.08560. -- Virtual context management for LLM agents
- Kang, M. et al. (2025). "ACON: Optimizing Context Compression for Long-horizon LLM Agents." arXiv:2510.00615. -- State-of-the-art context compression without provenance
- Pathak, D. et al. (2025). "Detecting Silent Failures in Multi-Agentic AI Trajectories." arXiv:2511.04032. -- Silent failure detection benchmark
- "Tiny Silent Hallucinations in Agentic AI." OpenReview (ICLR 2026 submission). -- Formalizes silent hallucinations as reliability problem
- Ye, Q. et al. (2026). "Agent Contracts: A Formal Framework for Resource-Bounded Autonomous AI Systems." arXiv:2601.08815. -- Formal contracts for agent governance
- "Agent Behavioral Contracts." arXiv:2602.22302. -- Runtime behavioral contract enforcement
- "Audit Trails for Accountability in Large Language Models." arXiv:2601.20727. -- Hash-chain audit trails for LLMs
- "AuditableLLM: A Hash-Chain-Backed, Compliance-Aware Auditable Framework." Electronics 15(1):56. -- Tamper-evident LLM audit framework
- Procko, T. et al. (2025). "Prompt Provenance: Toward Traceable LLM Interactions." SSRN. -- W3C PROV extended for prompt lineage
- Hopcroft, J., Motwani, R. & Ullman, J. (2006). "Introduction to Automata Theory, Languages, and Computation." 3rd ed. -- Finite state machines
- Cover, T. & Thomas, J. (2006). "Elements of Information Theory." 2nd ed. Wiley. -- Information-theoretic compaction bounds
