# Primordial Computing: Typed Absence and Structural Provenance for Agent Runtime Integrity

## Paper Outline — arXiv Preprint / Workshop Paper

**Target venues:** AGENT 2026 (ICSE workshop), MemAgents (ICLR 2026), arXiv cs.SE / cs.AI
**Page limit:** 8-10 pages (workshop), unlimited (arXiv)

---

### Abstract (~200 words)

Long-horizon autonomous agents routinely collapse meaningful kinds of absence—unknown, not-invoked, deleted, compacted—into generic null states, making their computations harder to audit, debug, and recover. We present Primordial Computing, a protocol framework that treats absence as a typed computational object, enforces structural provenance through hash-verified reference chains, and preserves grounded recovery paths through compaction. We formalize an 8-state absence ontology with a complete transition table verified by 300K+ adversarial property-based transitions and 99% mutation score. We validate the framework on a real autonomous agent runtime (OpenClaw) with three tiers of baselines, a 9-type fault injection campaign, and simulated compaction experiments. Key findings: (1) the ontology is formally sound (RQ1: PASS), (2) the detection mechanism works on injected faults (+0.444 differential, 0% FPR) but zero naturally-occurring violations were observed on 30 runs (RQ2: PARTIAL—honest negative finding), (3) structural provenance degrades gracefully under simulated compaction (0.93→0.25 over 10-90% deletion) but genuine LLM compaction remains untested (RQ3: PARTIAL). We contribute a falsifiable methodology including a "forbidden proxy" framework that prevents self-deception, and discuss implications for agent reliability engineering.

---

### 1. Introduction (1.5 pages)

- The problem: agent systems narrate continuity while losing structure
- Motivating examples: compaction amnesia, orphaned artifacts, silent null collapse
- Three subclaims: typed absence, explicit provenance, recoverable compaction
- Contributions:
  1. 8-state absence ontology with formal transition rules
  2. Structural provenance protocol for agent runtimes
  3. Empirical evaluation on a real agent runtime with honest negative findings
  4. Falsifiable methodology with forbidden proxy framework

---

### 2. Background and Related Work (1.5 pages)

#### 2.1 Null Semantics in Databases and Programming Languages
- Codd (1979): two null types (missing-applicable, missing-inapplicable)
- Zaniolo (1984): multi-valued nulls
- Belnap (1977): four-valued logic
- SQL three-valued logic problems
- Option/Maybe/Result types (binary present/absent)
- **Gap:** None treats absence as a typed ontology for agent runtime state

#### 2.2 Agent Provenance and Observability
- W3C PROV (2013)
- PROV-AGENT (Souza et al., 2025)
- LangSmith, Langfuse, Braintrust (industry tools)
- **Gap:** Capture provenance but don't enforce structural integrity

#### 2.3 Context Compaction and Memory
- MemGPT/Letta (2023-2026): paging mechanism
- ACON (2025): 26-54% compression
- Knowledge Objects (Zahn & Chana, 2026): 60% fact loss per pass
- **Gap:** Compress but don't preserve grounded recovery paths

#### 2.4 Formal Methods for Agent Systems
- AgentSpec (Wang & Poskitt, ICSE 2026): action guards
- FAME Framework: statistical silent failure detection
- **Gap:** Guard actions, not data structure; statistical, not structural

---

### 3. The Primordial Protocol (2 pages)

#### 3.1 Typed Absence Ontology
- 8 states with semantic definitions
- Transition table (45 legal, 19 illegal, generated from 3 structural rules)
- Validation: `validate_record()` rejects ambiguous empties
- Absence state vs. ref state distinction (CC-001)

#### 3.2 Structural Provenance
- Artifact envelopes: id, type, hash, refs, producer metadata
- Chamber-scoped registration with index validation
- Dangling ref detection at registration time
- Context derivation (`get_context_view()`)

#### 3.3 Recoverable Compaction
- SummaryView with mandatory source_refs
- Structural trace compression (ref-based dedup, hash verification)
- Round-trip guarantee: `encode_trace()` → `decode_trace()` exact match
- `pruned_recoverable` state with recovery path metadata

#### 3.4 Protocol Dictionary
- 25 codes across 6 domains (ABSENCE, STOP, ERROR, CRITIQUE, REVISION, REF)
- Machine-readable + human-decodable
- Versioned lifecycle

---

### 4. Methodology (1.5 pages)

#### 4.1 Falsifiable Research Design
- Research questions with pre-stated acceptance criteria
- Scoping contract with stop/rethink conditions
- Forbidden proxy framework (prevents substituting easy measurements for hard ones)

#### 4.2 Three-Tier Baseline Design
- Uninstrumented floor (vanilla agent logger)
- Structured logging intermediate (standard structured logging)
- Forge-instrumented (full protocol enforcement)
- MockLM ceiling anchor (controlled deterministic conditions)

#### 4.3 Fault Injection Campaign (D1-D9)
- 9 violation types covering null discipline, provenance, integrity, lifecycle
- 90+ injections per campaign run
- Differential detection: forge vs. uninstrumented vs. structured logging

#### 4.4 Simulated Compaction Protocol
- Oldest-first programmatic deletion at 9 fractions (10-90%)
- Three-tier ref classification (resolved, degraded, broken)
- Structural reachability metric (resolved_refs / total_refs)
- BFS reachability for cross-validation

---

### 5. Evaluation (2 pages)

#### 5.1 RQ1: Ontology Formalization — PASS
- 300K+ adversarial Hypothesis transitions, 0 violations
- 99% mutation score (103/104 non-equivalent mutants killed)
- Three design questions resolved (CC-002, CC-003)

#### 5.2 RQ2: Violation Detection — PARTIAL
- **Positive:** 44.4% aggregate detection [CI: 0.344-0.544], 0% FPR
- **Positive:** 4/9 types detected at 100% (D1, D2, D5, D9)
- **Negative:** 0/30 natural violations (CP upper bound 11.6%)
- **Architectural:** 5/9 types undetectable post-hoc (D3, D4, D6, D7, D8)
- Table 1: Side-by-side metrics across all 4 tiers

#### 5.3 RQ3: Compaction Survival — PARTIAL
- Pre-compaction reachability: 1.0 (matches MockLM ceiling)
- Degradation curve: 0.93 → 0.25 over 10-90% deletion
- Backtracking at 80% deletion
- Violation detection stable post-compaction (D1/D2/D5/D9 at 100%)
- **Limitation:** Simulated only—genuine LLM compaction untested

#### 5.4 Consistency Verification
- 4 automated consistency checks, all passing
- 62 programmatic cross-reference checks, all green

---

### 6. Discussion (1 page)

#### 6.1 The Zero-Natural-Violations Finding
- Not a failure of the system; possibly a property of the workload
- Implications: either violations are rare (good for agents), or our detection is incomplete (need registration-time checking)
- What it takes to resolve: harder tasks, larger samples, or reframing to prevention

#### 6.2 Post-Hoc vs. Registration-Time Detection
- MockLM detects 6/6 at registration time; post-hoc detects 3/6
- Gap is architectural, not qualitative
- Implication: live instrumentation > log analysis for full coverage

#### 6.3 Simulated vs. Genuine Compaction
- Simulated deletion is a lower bound argument
- Genuine compaction may preserve more structure (intelligent summarization)
- But also may introduce semantic drift not captured by structural metrics

#### 6.4 Limitations
- Single runtime, single workload type
- Small sample sizes (30 clean runs, 3 chambers for compaction)
- No semantic reachability measurement
- No cross-architecture validation

---

### 7. Future Work (0.5 pages)

- Genuine LLM compaction experiments (128K+ token sessions)
- Adversarial task corpus for natural violation discovery (200+ runs)
- Cross-architecture adapters (LangGraph, CrewAI, OpenHands)
- Semantic Provenance Fidelity metric (embedding-based)
- Theoretical foundations (completeness argument, category-theoretic model)

---

### 8. Conclusion (0.25 pages)

Primordial Computing demonstrates that treating absence, provenance, and compaction as protocol-governed computational objects is both feasible and measurably beneficial for agent runtime integrity. The honest negative finding on natural violations and the simulated-only compaction results define a clear path for validation. We release all code, data, and methodology as open-source.

---

## Data Sources (all exist in primordial/ repo)

| Section | Source File |
|---------|------------|
| Table 1 (metrics) | `docs/cross-reference-report.md` Section 2 |
| RQ1 evidence | Phase 1 Plans 01-02 |
| RQ2 evidence | `data/campaign/campaign-report.json` |
| RQ3 evidence | `data/compaction/compaction-report.json` |
| Consistency checks | `data/synthesis/consistency-checks.json` |
| Transition table | `tools/forge_nulls.py:_build_transition_table()` |
| Protocol dictionary | `tools/forge_protocol_dict.json` |

## Figures Needed

1. Absence state transition diagram (8 states, legal/illegal edges)
2. Architecture diagram (forge tools layered on agent runtime)
3. Structural reachability degradation curve (9 deletion fractions)
4. Side-by-side bar chart (4 tiers × key metrics)
5. Revision cycle diagram (builder → critic → revision loop)
