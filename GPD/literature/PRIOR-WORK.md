# Prior Work: Live Validation of Agent-Runtime Integrity Protocols

**Surveyed:** 2026-06-12
**Domain:** LLM agent reliability — context compaction fidelity, silent failure measurement, agentic provenance, agent memory benchmarks
**Confidence:** HIGH on existence and headline claims of the core papers (each verified against arXiv abstracts or primary pages this session); MEDIUM on internal experimental details not inspected beyond abstracts (flagged per-entry)
**Milestone scope:** v3.0 "Live Validation" only — RQ3b (genuine compaction fidelity / SPF), RQ2b-live (natural violation rate on real runs), RQ5 (instrumentation overhead <20%). Validated v1.0–v2.x results (ontology, D-type detection, mock-backend campaigns, cross-architecture transfer) are treated as internal baselines and were NOT re-researched.

---

## Key Results

| Result | Expression / Value | Conditions | Source | Year | Confidence |
| --- | --- | --- | --- | --- | --- |
| Single-pass summarization fact loss | ~60% of facts destroyed by compaction summarization | Fact-recall workload; Claude Sonnet 4.5 primary, replication on 4 frontier models | Zahn & Chana, arXiv:2603.17781 | 2026 | HIGH (headline verified from abstract; per-pass protocol details not inspected) |
| Cascading compaction goal drift | 54% of project constraints eroded; model continues "with full confidence" | Repeated compaction cycles, same study | Zahn & Chana, arXiv:2603.17781 | 2026 | HIGH (headline) |
| In-context ceiling (zero-compaction limit) | 100% exact-match accuracy, 10 → 7,000 facts (97.5% of 200K window) | No compaction; facts fully in context; Claude Sonnet 4.5 | Zahn & Chana, arXiv:2603.17781 | 2026 | HIGH |
| Knowledge Objects vs in-context, multi-hop | KO 78.9% vs in-context 31.6%; KOs 100% on fact recall at ~252× lower cost | Hash-addressed fact tuples, O(1) retrieval | Zahn & Chana, arXiv:2603.17781 | 2026 | HIGH (headline) |
| Long-horizon meltdown rates | 13–19% meltdown at very-long horizons (≥120 min) for top-performing models | 10 open-source models, 23,392 episodes, 396 tasks; meltdown = entropy spike in tool-call sequences | Khanal, Tao & Zhou, arXiv:2603.29231 | 2026 | HIGH (verified in full-text fetch) |
| Graceful-degradation collapse in SWE tasks | GDS 0.90 → 0.44 short→very-long horizon (software engineering); document processing stable 0.74 → 0.71 | Same study; ReAct scaffold | Khanal, Tao & Zhou, arXiv:2603.29231 | 2026 | HIGH |
| Naive memory scaffolds do not help | "The memory scaffold never helps": 6/10 models hurt, 4/10 neutral (±0.03 GDS); worst −0.14 GDS | Episodic memory-augmented scaffold vs ReAct, long + very-long horizons | Khanal, Tao & Zhou, arXiv:2603.29231 §6.5, Table 13 | 2026 | HIGH (verified quote) |
| Entropy growth model for silent failure | S(t) = S₀·e^(αt); 22 intrinsic properties across 6 lifecycle layers | 40,000 controlled trials + 100,000+ production agent interactions claimed | Liu, arXiv:2606.08162 | 2026 | MEDIUM (single author; abstract gives model, not rates; not peer-reviewed; see caveats below) |
| Production LLM span error rate | 2% of LLM spans errored (Mar 2026); 5% (Feb 2026); rate limits = 1/3 to 60% of errors | Telemetry across thousands of Datadog customers; explicit errors only — silent failures NOT quantified | Datadog, State of AI Engineering | 2026 | HIGH for what it covers |
| Multi-agent system failure rates | ~41–86.7% task failure across analyzed multi-agent systems (MAST taxonomy) | Pre-dates this milestone; background anchor | Cemri et al., arXiv:2503.13657 (background knowledge, corroborated by secondary 2026 sources; primary not re-fetched this session) | 2025 | MEDIUM |
| Claude Code compaction trigger | ~89% of window; formula `contextWindow − min(maxOutput, 20k) − 13k`; 5 mechanisms incl. microcompact, tool-output clearing, user "Compact Instructions" | Practitioner reverse-engineering, 7-agent comparison; updated 2026-06-12 | Vaughan, codex.danielvaughan.com (2026-04-10) | 2026 | MEDIUM (practitioner source; version-sensitive — re-verify empirically in Phase 1) |
| Compaction cost per event | ~$0.40 per compaction ≈ 21 follow-up turns at cached rates | Same practitioner analysis | Vaughan (2026-04-10) | 2026 | MEDIUM |
| Memory benchmark ↔ agentic-task gap | Models near-saturated on LoCoMo drop to 40–60% on interdependent multi-session agentic tasks | MemoryArena: web nav, constrained planning, progressive search, sequential formal reasoning | He, Wang et al., arXiv:2602.16313 | 2026 | HIGH (headline) |
| Best agentic-memory system accuracy | AMA-Agent 57.22% on AMA-Bench (+11.16 over strongest baseline) | Real + synthetic agent trajectories; failure modes: lossy similarity retrieval, missing causal/objective info | Zhao et al. (12 authors), arXiv:2602.22769 | 2026 | HIGH (headline) |
| Provenance capture overhead | PROV-AGENT paper reports NO measured overhead ("preliminary evaluation"); Flowcept docs claim <5% wall-clock | e-Science 2025 paper verified to lack overhead numbers; <5% is a vendor-docs claim | Souza et al., arXiv:2508.02866; flowcept.org | 2025–26 | HIGH that the gap exists; MEDIUM on the <5% claim |
| Generic tracing overhead | OTel GenAI span instrumentation <1 ms per LLM call, <1% app impact | Vendor/community blogs (Uptrace, FutureAGI); LLM latency (100 ms–30 s) dominates | OTel GenAI ecosystem posts | 2026 | MEDIUM (vendor claims, no peer-reviewed measurement found) |

---

## Foundational Work

### Zahn & Chana (2026) — Facts as First-Class Objects: Knowledge Objects for Persistent LLM Memory

**Reference:** arXiv:2603.17781, submitted 2026-03-18. Verified via arXiv abstract fetch this session.
**Key contribution:** The direct quantitative anchor for RQ3b. Establishes the three production failure modes of in-context memory: capacity overflow (~8,000 facts), compaction loss (summarization destroys ~60% of facts), and goal drift (cascading compaction erodes 54% of project constraints while the model continues confidently). Contrasts with Knowledge Objects — discrete, hash-addressed fact tuples with O(1) retrieval — achieving 100% accuracy at ~252× lower cost; multi-hop 78.9% vs 31.6%. Grounds the loss theoretically in Linear Associative Memory interference growing with N·ρ (fact count × pairwise semantic similarity).
**Method:** Fact-storage benchmark, 10–7,000 facts, Claude Sonnet 4.5 primary with cross-model replication on four frontier models; adversarial fact scenarios; comparison against neural memory (Titans).
**Limitations:** Fact-recall workload, not live coding-agent sessions; the compaction procedure is the authors' own summarization pipeline, not a host agent's native compaction (e.g., Claude Code's `/compact`). The 60%/54% numbers are therefore an upper-bound analogue, not a measurement of the mechanism v3.0 targets. Per-pass protocol details were not inspected beyond the abstract this session.
**Relevance:** v3.0's SPF metric measures exactly what this paper measures by proxy — but through GENUINE host-agent compaction in real Claude Code sessions with forge provenance. No published follow-up replicating or refining the 60%-per-pass figure was found as of 2026-06-12 (searched explicitly); the replication-through-native-compaction niche appears open.

### Khanal, Tao & Zhou (2026) — Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents

**Reference:** arXiv:2603.29231, submitted 2026-03-31. Verified via abstract + full-text HTML fetch this session.
**Key contribution:** Reliability-science metric suite for long-horizon agents: Reliability Decay Curve (RDC), Variance Amplification Factor (VAF), Graceful Degradation Score (GDS), Meltdown Onset Point (MOP). Defines meltdown behaviorally (looping tool calls, contradicting earlier observations, hallucinating tool outputs) and detects it via sliding-window entropy of tool-call sequences. Frontier-class models show the HIGHEST meltdown rates (DeepSeek V3 19%, MiniMax M2.5 13% at very-long horizons) despite best average performance. SWE-domain GDS collapses 0.90 → 0.44 with horizon length.
**Method:** 396 tasks × 4 duration buckets (≤5 min to ≥120 min) × 3 domains (SWE, web research, document processing); 10 open-source models, k=3 repetitions, 2 scaffolds, 23,392 episodes.
**Limitations:** Open-source models only (no Claude/GPT-class API models); meltdown detection is entropy-heuristic, not ground-truth state inspection; memory scaffold tested is a single naive episodic design.
**Relevance:** Two-fold. (1) Methodological template for RQ2b-live: their duration-bucket design and entropy-based degradation detection are the closest published analogue to measuring natural violation rates as a function of session length. (2) **Strongest disconfirming-adjacent result for the project premise**: "the memory scaffold never helps" (§6.5; 6/10 models hurt, 4/10 neutral). The v3.0 paper MUST engage this. The distinction to draw precisely: their scaffold INJECTS retrieved episodic summaries into context (adding load and interference); forge protocols track typed state and provenance WITHOUT injecting summaries — integrity instrumentation, not memory augmentation. If v3.0 overhead or interference data blurs that distinction, the claim weakens.

### Souza et al. (2025) — PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows

**Reference:** arXiv:2508.02866; Proceedings of the 21st IEEE International Conference on e-Science, Chicago, 2025 (ORNL/UT-Battelle, DOE). Verified via abstract + full-text HTML fetch this session.
**Key contribution:** W3C PROV extension with agent-/LLM-centric entities, activities, and relations; integrates prompts, responses, tool calls, model invocations, and telemetry into one provenance graph via MCP and the Flowcept observability framework (`@flowcept_agent_tool` decorators, LLM-call wrappers). Demonstrates five query classes: full decision lineage, decision/reasoning retrieval, prompt/response recovery on hallucination, decision→downstream-activity influence, and root-cause analysis of error propagation.
**Method:** Cross-facility deployment (edge, cloud, HPC) on an agentic additive-manufacturing workflow; near-real-time capture.
**Limitations (verified):** The paper explicitly does NOT report measured provenance-capture overhead — it self-describes as a "preliminary evaluation." Flowcept's documentation claims <5% wall-clock overhead, but that number is a vendor-docs claim, not in the peer-reviewed paper. Scientific-workflow setting, not consumer coding agents; no integrity semantics (no typed absence, no violation detection — capture and query only).
**Relevance:** State of the art for (c). v3.0's RQ5 (overhead <20%) would supply exactly the measurement PROV-AGENT omits, in a different deployment class (live subprocess-driven Claude Code sessions). forge_trace_codec is positioned downstream of PROV: not just capture, but integrity verdicts over the captured graph.

### Liu (2026) — Silent Failure in LLM Agent Systems: The Entropy Principle and the Inevitable Disorder of Autonomous Agents

**Reference:** arXiv:2606.08162, submitted 2026-06-06. Verified via abstract fetch this session.
**Key contribution:** Closest direct precedent for RQ2b-live. Claims silent failures (deviations under normal conditions, misattributed to bugs/config) are intrinsic, identifying 22 system properties across six lifecycle layers; proposes exponential entropy accumulation S(t) = S₀·e^(αt) with α "measured empirically across multiple architectures," where entropy = measurable loss of output consistency, task accuracy, and cross-session coherence. Claims 40,000 controlled trials + 100,000+ production agent interactions.
**Method:** Mixed controlled trials + long-term production observation; proposes "PIG Engine" and "ADE protocol suite" as countermeasures.
**Limitations / caveats:** Single-author preprint, days old, not peer-reviewed; the abstract provides the model but no concrete per-condition violation rates; countermeasure branding suggests possible product orientation. Treat quantitative claims as unconfirmed until the full text is audited (Phase 1 reading task).
**Relevance:** Establishes that "natural disorder rate on live agents" is now an active topic — v3.0's RQ2b is timely, not redundant: Liu measures aggregate behavioral entropy; Primordial measures TYPED protocol violations with a 64-entry transition table, which is a sharper, falsifiable observable. Also a framing risk: if Liu's "inevitability" thesis holds, Primordial's CC-015 reframe (structural prevention) is the natural counter-position — prevention via typed state contradicts inevitability.

### Vaughan (2026) — Context Compaction Showdown / Deep Dive (practitioner series)

**Reference:** codex.danielvaughan.com, 2026-04-10 (showdown, 7 agents) and 2026-04-14 (deep dive: Codex CLI, Claude Code, OpenCode); showdown updated 2026-06-12. Verified via direct fetch this session.
**Key contribution:** Only found source that systematically documents NATIVE compaction mechanics across coding agents. Trigger thresholds: Gemini CLI ~50%; Roo Code ~86–92% (`window × 0.9 − maxOutputTokens`); Claude Code ~89% (`contextWindow − min(maxOutput, 20k) − 13k`); Codex CLI ~90%; Pi ~92%; OpenCode ~96–99%; OpenHands event-based (100 events). Claude Code uses five mechanisms (microcompact inline cleanup, tool-output clearing, user-guided Compact Instructions, plus full summarization). Most agents use destructive extract-pattern summarization — "summary of a summary" compounding. One compaction ≈ $0.40 ≈ 21 cached follow-up turns. Structured preservation checklists before compaction increased summary length 1,643 → 2,455 tokens (+49%) — note: a LENGTH proxy, not a fidelity measurement.
**Limitations:** Practitioner blog, not peer-reviewed; internals are version-sensitive (e.g., Claude Code 2.0.64 reportedly made compaction "instant" per secondary sources); no semantic fidelity measurement anywhere in the series.
**Relevance:** Operational ground truth for v3.0 experiment design: it tells you WHERE the compaction trigger sits (~89%), so live sessions can be driven deterministically across it, and confirms nobody has published per-pass semantic fidelity through Claude Code's real `/compact` / auto-compact. Re-verify thresholds empirically against the installed Claude Code version in Phase 1 — do not hard-code the blog's formulas.

### Rasheed, Banerjee, Mukherjee & Hazra (2026) — From Fluent to Verifiable: Claim-Level Auditability for Deep Research Agents

**Reference:** arXiv:2602.13855, submitted 2026-02-14. Verified via abstract fetch this session.
**Key contribution:** Proposes the Auditable Autonomous Research (AAR) standard with four measures — provenance coverage, provenance soundness, contradiction transparency, audit effort — plus persistent, queryable provenance graphs encoding claim–evidence relations with continuous validation during synthesis. Distills recurring failure modes: objective drift, transient constraints, unverifiable inference.
**Limitations:** Abstract-level inspection only; no quantitative results visible on the abstract page; research-report agents, not coding agents.
**Relevance:** Closest published metric family to SPF. v3.0 should define SPF so it is comparable to (or explicitly distinct from) "provenance coverage" and "provenance soundness" — and check for naming collisions before the paper milestone. Their "objective drift" and "transient constraints" map directly onto Zahn & Chana's goal-drift finding and Primordial's typed-absence states.

---

## Recent Developments (2026, by question area)

| Paper / Source | Authors | Date | Advance | Impact on v3.0 |
| --- | --- | --- | --- | --- |
| (a) Facts as First-Class Objects (arXiv:2603.17781) | Zahn & Chana | 2026-03 | 60%/54% compaction-loss anchors; KO alternative | SPF baseline; replicate through NATIVE compaction |
| (a) Memori: A Persistent Memory Layer (arXiv:2603.19935) | not inspected | 2026-03 | Persistent memory layer for context-aware agents | Listed for completeness; NOT inspected — verify before citing |
| (b) Silent Failure / Entropy Principle (arXiv:2606.08162) | Liu | 2026-06 | Entropy model of silent failure on 100K+ live interactions | Direct RQ2b precedent and framing counter-position |
| (b) Beyond pass@1 (arXiv:2603.29231) | Khanal, Tao & Zhou | 2026-03 | RDC/VAF/GDS/MOP metrics; 13–19% meltdowns; memory scaffolds never help | Methodology template + must-engage counterargument |
| (b) State of AI Engineering | Datadog | 2026-02/03 | 2–5% explicit LLM-span error rate at production scale; silent failures explicitly unquantified | Quantifies the explicit-error floor; the silent gap IS RQ2b |
| (c) PROV-AGENT (arXiv:2508.02866) | Souza et al. | 2025 (e-Science) | W3C PROV + MCP agent provenance; no overhead numbers | RQ5 fills its stated gap; cite as capture-layer SOTA |
| (c) LLM Agents for Interactive Workflow Provenance (arXiv:2509.13978, SC'25 workshops) | Souza-group line | 2025 | Reference architecture for querying provenance via agents | Adjacent; shows the ORNL line continuing — watch for 2026 successor with overhead numbers |
| (c) From Fluent to Verifiable (arXiv:2602.13855) | Rasheed et al. | 2026-02 | AAR: provenance coverage/soundness/contradiction/audit-effort metrics | SPF metric-design comparator |
| (c) OTel GenAI semantic conventions | OTel community | 2026 (experimental status as of ~03/2026) | Standard agent/LLM span schema; <1 ms/call overhead claims (vendor) | forge_trace_codec should emit/align with OTel GenAI spans for comparability |
| (d) Context Compaction Showdown/Deep Dive | Vaughan | 2026-04 (upd. 06) | 7-agent native-compaction mechanics, thresholds, costs | Experiment-design ground truth for live Claude Code runs |
| (e) MemoryArena (arXiv:2602.16313) | He, Wang, Zhi, Hu, ... McAuley, Choi, Pentland (14 authors; Stanford/UCSD/UIUC/Princeton) | 2026-02 | Interdependent multi-session tasks; LoCoMo-saturated models drop to 40–60% | Shows passive-recall benchmarks overstate integrity; supports live-task evaluation choice |
| (e) AMA-Bench (arXiv:2602.22769) | Zhao et al. (12 authors) | 2026-02 | Long-horizon memory on real agent trajectories; best system 57.22% | Candidate task source / comparison point for live runs |
| (e) MemoryAgentBench (arXiv:2507.05257, ICLR 2026) | Hu, Wang & McAuley | 2025/26 | Four competencies: accurate retrieval, test-time learning, long-range understanding, conflict resolution | Conflict-resolution competency overlaps typed-absence semantics |
| (e) Memory survey (arXiv:2603.07670) | Du (single author) | 2026-03 | Write-manage-read loop taxonomy incl. context-resident compression, contradiction handling | Related-work scaffolding for the paper milestone |
| (e) Long-Term Memory Security survey (arXiv:2604.16548) | Lin et al. (8 authors) | 2026-04 | Memory-lifecycle threat framework; proposes "Verifiable Memory Governance"; memory integrity as one of four security objectives | Terminology adjacency to forge_chamber — check for collisions; note title changed between versions (earlier: "Toward Mnemonic Sovereignty") |

---

## Known Limiting Cases

| Limit | Known Result | Source | Use in v3.0 |
| --- | --- | --- | --- |
| Zero-compaction (all facts in window) | 100% exact-match recall up to 7,000 facts / 97.5% of 200K window | Zahn & Chana 2026 | Control condition: live sessions kept below the ~89% trigger should show SPF ≈ 1; if not, instrumentation itself is confounding |
| Single summarization pass | ~60% fact loss | Zahn & Chana 2026 | SPF after 1 native compaction should be compared against this; native compaction (with Compact Instructions, microcompact) plausibly loses LESS — that delta is a publishable result either way |
| Cascading passes | 54% of constraints eroded; compounding "summary of a summary" | Zahn & Chana 2026; Vaughan 2026 | Dose-response curve target; compare shape to v2.x simulated-deletion reachability 0.93→0.25 (internal baseline) |
| Explicit-error floor in production | 2–5% of LLM spans (dominated by rate limits) | Datadog 2026 | Live natural-violation measurements must separate forge-typed violations from this mundane error background |
| Instrumentation overhead floor | <1 ms/call, <1% (OTel span capture, vendor claims); <5% wall-clock (Flowcept docs) | OTel ecosystem; flowcept.org | RQ5's 20% budget is conservative vs ecosystem claims; reporting measured overhead near or below 5% would be competitive, >20% would be a real negative result |
| Very-long-horizon behavior | 13–19% meltdown rates, GDS 0.90→0.44 (SWE) | Khanal et al. 2026 | Expected base rate of behavioral collapse in long live sessions — plan session counts so violation rates are estimable against this noise |

---

## Open Questions (literature gaps that v3.0 directly addresses)

1. **Per-pass semantic fidelity through NATIVE coding-agent compaction is unmeasured.** Zahn & Chana measured their own summarization pipeline; Vaughan documented mechanics without fidelity numbers; no peer-reviewed measurement of fact/constraint survival through Claude Code's actual auto-compact or `/compact` was found (searched 2026-06-12). This is RQ3b's exact niche.
2. **Silent-failure rates are quantified only behaviorally or not at all.** Datadog explicitly measures only explicit errors; Liu (2606.08162) measures aggregate entropy, not typed protocol violations; Khanal et al. measure meltdown heuristically. A typed-violation rate (per the 64-entry transition table) on live non-mock runs does not exist in the literature. This is RQ2b-live's niche — and converts Primordial's 0/321 mock-backend result (CP 95% upper 1.14%) into a live claim or refutes it.
3. **Provenance-capture overhead in agentic settings has no peer-reviewed measurement.** PROV-AGENT (verified) reports none; Flowcept's <5% is a docs claim; OTel numbers are vendor blogs. RQ5 with a rigorous protocol fills a stated gap in the flagship provenance paper's own evaluation.
4. **Does integrity instrumentation help or hurt at long horizons?** Khanal et al.'s "memory scaffold never helps" result makes this contested. Whether NON-injecting integrity layers (typed absence + provenance, no context stuffing) avoid the scaffold penalty is open — v3.0's overhead + fidelity data speaks directly to it, and the paper must draw the scaffold-vs-instrumentation distinction explicitly.
5. **Unverified claim to avoid:** "65% of enterprise AI failures in 2025 traced to context degradation" circulates on SEO-grade pages (e.g., claude-code-examples.vercel.app); no primary source located this session. Do NOT cite without finding the original survey.

---

## Notation Conventions in the Literature

| Quantity | Standard term(s) | Variations | Our choice | Reason |
| --- | --- | --- | --- | --- |
| Context reduction event | "compaction" (Claude Code, Vaughan, Zahn & Chana) | "context compression" (ACON, oneuptime), "summarization", "context management" | compaction | Matches host-agent terminology and Zahn & Chana; reserve "compression" for token-level methods |
| Undetected failure | "silent failure" | Liu: deviation under normal conditions; Latitude/observability: tool error swallowed without surfacing; Primordial: typed D-fault | Define all three, measure typed violations | Three incompatible definitions in the wild — the paper must disambiguate or reviewers will conflate them |
| Fidelity through compaction | (none standard) | "fact retention" (Zahn & Chana), "provenance coverage/soundness" (AAR, 2602.13855), GDS (2603.29231) | SPF (semantic preservation fidelity), defined against AAR terms | SPF is project-coined; position it relative to AAR coverage/soundness to avoid appearing to reinvent them |
| Provenance vocabulary | W3C PROV (Entity/Activity/Agent, wasDerivedFrom, ...) | PROV-AGENT extensions; OTel GenAI spans | W3C PROV core + PROV-AGENT extension names; emit OTel-compatible spans | Comparability with PROV-AGENT queries Q1–Q5 and 2026 observability tooling |
| Long-horizon collapse | "meltdown" (entropy spike in tool calls) | "goal drift" (Zahn & Chana), "objective drift" (AAR), "entropy accumulation" (Liu) | Report typed violations; map to meltdown/drift in discussion | Keeps the observable falsifiable while staying citable against all three framings |

---

## Sources

Verified this session (arXiv abstract or full-text fetched directly):

- Zahn, O. & Chana, S. (2026). "Facts as First Class Objects: Knowledge Objects for Persistent LLM Memory." arXiv:2603.17781 (2026-03-18) — compaction-loss anchors (60%, 54%), in-context ceiling, KO comparison.
- Khanal, A., Tao, Y. & Zhou, J. (2026). "Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents." arXiv:2603.29231 (2026-03-31) — RDC/VAF/GDS/MOP, meltdown rates, memory-scaffold negative result (full text inspected).
- Liu, D. (2026). "Silent Failure in LLM Agent Systems: The Entropy Principle and the Inevitable Disorder of Autonomous Agents." arXiv:2606.08162 (2026-06-06) — entropy model; quantitative details pending full-text audit.
- Souza, R., Gueroudji, A., DeWitt, S., Rosendo, D., Ghosal, T., Ross, R., Balaprakash, P., Ferreira da Silva, R. (2025). "PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows." 21st IEEE e-Science, Chicago. arXiv:2508.02866 — provenance model + verified absence of overhead measurement.
- Rasheed, R. A., Banerjee, S., Mukherjee, A. & Hazra, R. (2026). "From Fluent to Verifiable: Claim-Level Auditability for Deep Research Agents." arXiv:2602.13855 (2026-02-14) — AAR metrics.
- Zhao, Y. et al. (2026). "AMA-Bench: Evaluating Long-Horizon Memory for Agentic Applications." arXiv:2602.22769 (2026-02-26).
- He, Z., Wang, Y. et al. (2026). "MemoryArena: Benchmarking Agent Memory in Interdependent Multi-Session Agentic Tasks." arXiv:2602.16313 (2026-02-18).
- Hu, Y., Wang, Y. & McAuley, J. (2026). "Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions" (MemoryAgentBench). ICLR 2026; arXiv:2507.05257.
- Du, P. (2026). "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers." arXiv:2603.07670 (2026-03-08).
- Lin, Z. et al. (2026). "A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle." arXiv:2604.16548 (2026-04-17).
- Vaughan, D. (2026). "Context Compaction Showdown" (2026-04-10, updated 2026-06-12) and "Context Compaction Deep Dive" (2026-04-14). codex.danielvaughan.com — practitioner; thresholds and mechanics.
- Datadog (2026). "State of AI Engineering." datadoghq.com/state-of-ai-engineering — Feb–Mar 2026 production span error rates.
- Flowcept documentation (flowcept.org / flowcept.readthedocs.io) — <5% wall-clock overhead claim (vendor docs, MEDIUM).
- OpenTelemetry GenAI observability ecosystem posts (opentelemetry.io blog 2026; Uptrace; Greptime 2026-05-09) — span conventions and overhead claims (vendor/community, MEDIUM).

Background (training-data knowledge, NOT re-fetched this session — verify before load-bearing citation):

- Cemri, M. et al. (2025). "Why Do Multi-Agent LLM Systems Fail?" arXiv:2503.13657 (MAST taxonomy; 41–86.7% failure rates) — corroborated by secondary 2026 sources this session.
- Laban, P. et al. (2025). "LLMs Get Lost in Multi-Turn Conversation." arXiv:2505.06120 (~39% average multi-turn degradation) — pre-milestone background for the paper's related-work section.

Listed but NOT inspected (existence verified via search results only — fetch before citing):

- "Memori: A Persistent Memory Layer for Efficient, Context-Aware LLM Agents." arXiv:2603.19935.
- "AMemGym: Interactive Memory Benchmarking for Assistants in Long-Horizon Conversations." arXiv:2603.01966.
- "Evaluating Memory Structure in LLM Agents." arXiv:2602.11243.
- "EvoClaw: Evaluating AI Agents on Continuous Software Evolution." arXiv:2603.13428.
- "ACON: Optimizing Context Compression for Long-Horizon LLM Agents." OpenReview (ID 7JbSwX6bNL).
