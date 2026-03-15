# Known Pitfalls Research

**Domain:** Typed absence, provenance tracking, and recoverable compaction in agentic systems
**Researched:** 2026-03-15
**Confidence:** MEDIUM-HIGH

---

## Critical Pitfalls

### Pitfall 1: The MockLM-to-Real-LLM Validity Gap

**What goes wrong:**
All 103 existing tests pass against MockLM, which returns deterministic, pre-scripted responses. When moving to a real LLM (Zarathustra/OpenClaw), the agent produces nondeterministic outputs, may ignore instructions, generate malformed structures, or hit actual context limits. Every forge tool invariant that held under MockLM could break under real nondeterminism -- not because the invariant is wrong, but because the integration surface is different. The project charter explicitly identifies this as the weakest assumption: "MockLM never hit genuine memory limits."

**Why it happens:**
MockLM removes precisely the variables that make real agents fail: stochastic decoding, variable output formatting, genuine context pressure, actual latency, and emergent tool-call patterns. Tests that mock the LLM test the protocol logic, not the protocol's robustness to real agent behavior. This is the "testing pyramid" gap documented by Block Engineering (2025): unit tests with mocked LLM calls cover logic correctness but miss integration failure modes entirely.

**How to avoid:**
- Design a staged validation campaign: MockLM regression suite (existing) -> recorded-response playback (new) -> live LLM with short tasks -> live LLM with compaction-triggering tasks. Each stage introduces one new variable.
- Record real Zarathustra sessions and replay them through forge tools as a middle ground between MockLM and live integration.
- Define explicit "integration-specific" test cases that exercise real LLM output parsing, not just protocol logic.
- Accept that some MockLM tests will need adaptation: real agents may produce outputs that are structurally correct but semantically different from canned responses.

**Warning signs:**
- Forge tools reject a high percentage of real agent outputs as "malformed" when they are actually valid but unexpected.
- Tests pass under MockLM but the system fails silently under real LLM because validation exceptions are caught too broadly.
- Compaction scenario C (which uses `_fake_count_tokens` to force compaction at 5 messages) behaves completely differently under real token counting.

**Phase to address:**
The integration and baseline establishment phase. Before instrumenting Zarathustra fully, run a "smoke test" campaign with real LLM calls on simple tasks to calibrate expectations. This must precede the full measurement campaign.

**References:**
- Block Engineering, "Testing Pyramid for AI Agents" (2025): https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents
- MLOps Community, "Effective Practices for Mocking LLM Responses" (2025): https://home.mlops.community/public/blogs/effective-practices-for-mocking-llm-responses-during-the-software-development-lifecycle

---

### Pitfall 2: Compaction Destroys Provenance While Appearing to Preserve It

**What goes wrong:**
When context windows fill up under real pressure, the LLM runtime summarizes older context to make room. This summarization replaces specific artifact IDs, file paths, exact values, and source references with paraphrased approximations. The forge `source_refs` pointing to `artifact:run200:stage:architect:r1` survive in the trace codec's compressed representation, but the actual content those refs point to has been lossy-summarized by the LLM. The refs resolve structurally (they exist in the artifact_index) but are semantically degraded -- the content behind the ref is no longer the original content. The project's `verify_trace()` checks hash integrity of the *trace encoding* but cannot detect that the *semantic content* was lossy-summarized before encoding.

This is the project charter's identified "weakest anchor": compaction under real context pressure.

**Why it happens:**
Compaction in real LLM systems (Claude Code, OpenAI agents, Google ADK) replaces message history with a summary. As Lethain (2026) documents: "Compaction destroys specifics: file paths, exact values, config details, reasoning chains." The forge trace codec preserves structural integrity (refs, hashes, dedup) but operates *after* the LLM has already performed lossy summarization. There are two layers of compaction -- the LLM's context management (lossy) and forge's trace codec (lossless) -- and conflating them produces false confidence.

**How to avoid:**
- Distinguish clearly between forge trace compression (lossless, hash-verified) and LLM context compaction (lossy, semantic).
- Instrument the compaction boundary: when the LLM runtime triggers compaction, forge must record a `pruned_recoverable` absence state on affected artifacts *before* summarization occurs, capturing what was pruned and where the original lives.
- Measure "semantic reachability" separately from "structural reachability": can you actually recover the original content from a pruned_recoverable ref, or just confirm the ref ID existed?
- Design the compaction survival test to measure content fidelity, not just ref resolution. Compare post-compaction artifact content against pre-compaction originals.

**Warning signs:**
- Provenance reachability scores are 100% but the agent cannot actually retrieve original content from pruned refs.
- `verify_trace()` reports `valid: True` on traces where the underlying content was lossy-summarized.
- The system reports "compaction survived" but post-compaction outputs show the agent operating on paraphrased rather than original information.

**Phase to address:**
The compaction measurement phase. This is the central experimental question and must be addressed with explicit semantic fidelity metrics, not just structural integrity checks.

**References:**
- Lethain, "Building an internal agent: Context window compaction" (2026): https://lethain.com/agents-context-compaction/
- Factory.ai, "Evaluating Context Compression" (2025): https://factory.ai/news/evaluating-compression
- Morph, "Compaction vs Summarization" (2025): https://www.morphllm.com/compaction-vs-summarization

---

### Pitfall 3: Typed Absence Adds Complexity Without Catching Real Failures

**What goes wrong:**
The 8-state absence ontology (not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable, not_generated) successfully catches synthetic violations (Scenario D: 6/6 detected). But real agent failures may not manifest as typed-absence violations at all. Real failures include: the agent producing *wrong* content (not absent content), the agent hallucinating a source_ref that structurally validates but points to fabricated content, or the agent silently dropping a constraint without any empty field appearing. The project charter explicitly lists this as a falsifier: "typed absence adds complexity without measurable reliability gains."

**Why it happens:**
Typed absence enforces that empty values are explicitly annotated. But the most dangerous agent failures are not about empty values -- they are about *wrong* values that look correct. The MAST taxonomy (Cemri et al., 2025) identifies 14 failure modes in multi-agent systems; only a fraction involve null/empty state. Most involve "inter-agent misalignment" and "task verification" failures where agents produce plausible but incorrect results. The forge null discipline catches the easy cases (bare None, empty string) while the hard cases (confidently wrong output, hallucinated refs) sail through validation.

**How to avoid:**
- Frame typed absence as a necessary-but-not-sufficient layer. It prevents ambiguity about *whether* something was produced; it does not validate *what* was produced.
- Design measurement criteria that separate absence-detection value (preventing "is this field empty or was it never requested?") from correctness-detection value (preventing "is this output right?").
- Document explicitly which failure classes typed absence catches and which it does not. This prevents overclaiming.
- Ensure the experimental design includes tasks where the agent produces wrong output, not just missing output, to demonstrate where the boundary of typed absence lies.

**Warning signs:**
- All forge violations detected are of the same class as Scenario D (synthetic nulls, structural violations).
- No naturally-occurring violations are caught during the real agent campaign, even though the agent makes observable errors.
- The team conflates "zero forge violations" with "zero failures."

**Phase to address:**
The violation detection measurement phase. The acceptance criterion is "at least 1 naturally-occurring violation detected" -- if this threshold is not met, the project must honestly report that typed absence catches structural but not semantic failures.

**References:**
- Cemri, Pan, Yang et al., "Why Do Multi-Agent LLM Systems Fail?" arXiv:2503.13657 (2025)
- AgentErrorTaxonomy in "Where LLM Agents Fail" arXiv:2509.25370 (2025)

---

### Pitfall 4: Provenance Chain Breaks Under Recursive or Revision Cycles

**What goes wrong:**
The orchestrator's revision cycle (critic triggers builder revision, re-registers stages) creates provenance chains with growing complexity. Each revision adds new artifact IDs that reference all prior stages via `_build_source_refs`, which returns ALL upstream artifacts. For a 3-seat chamber with 2 revision cycles, the critic's second pass has source_refs pointing to 7+ artifacts. Under real agent behavior with deeper recursion (Scenario B), the source_ref lists grow combinatorially. This creates three failure modes: (1) ref lists become so large they contribute to context pressure, accelerating compaction; (2) the semantic meaning of "this summary was derived from these sources" degrades when the source list is everything upstream; (3) under real compaction, some of these refs may point to artifacts whose content was already summarized away, creating structurally valid but semantically broken chains.

**Why it happens:**
The current `_build_source_refs` implementation takes the full `available_artifact_ids` set minus the chamber ID. This is correct for structural provenance (the stage *could* have been influenced by any upstream artifact) but imprecise for semantic provenance (the stage was *actually* derived from specific upstream artifacts). The AgentAsk paper (2025) calls this "Referential Drift" -- when references accumulate but their actual causal relationship weakens.

**How to avoid:**
- Distinguish between "structural provenance" (what was available) and "causal provenance" (what was actually used). The current implementation conflates them.
- Consider limiting source_refs to direct causal inputs rather than the full upstream set. The builder's revision should reference the critic's findings and the original architect plan, not every intermediate artifact.
- Measure provenance chain depth and width as part of the experiment. If chains grow O(n^2) in stages, this indicates a design problem.
- Test revision cycles of depth 3+ under real conditions, not just the max_revisions=3 policy limit.

**Warning signs:**
- source_refs lists grow linearly or superlinearly with stage count.
- Provenance reachability is 100% but provenance *specificity* is near 0% (every artifact claims derivation from everything).
- Under compaction, provenance chains that were "100% reachable" degrade to partial reachability because the refs pointed to summarized content.

**Phase to address:**
The baseline measurement phase (establish what provenance chains look like under real conditions) and the provenance survival measurement phase.

**References:**
- AgentAsk, arXiv:2510.07593 (2025): edge-level error taxonomy including "Referential Drift"

---

### Pitfall 5: Measuring Against a Straw-Man Baseline

**What goes wrong:**
The vanilla RLM logger has zero invariant checks by design -- it is a plain event logger. Comparing forge (with typed absence, provenance, trace compression) against vanilla (with nothing) will always show forge detecting more violations. This is true but trivially true. The risk is that the experiment demonstrates "typed absence is better than no checking at all" rather than the intended claim that "typed absence catches failures that go undetected without it." Any reasonable observability layer (structured logging with schema validation, OpenTelemetry traces, Langfuse spans) would also catch some of these violations.

**Why it happens:**
The experimental design uses a deliberately minimal baseline to make the comparison stark. This was appropriate for the MockLM proof-of-concept but becomes a false progress trap when moving to real agents. The Scenario D test (6 deliberate violations, 0 vanilla detection) proves that forge_nulls.py works, not that it solves a problem the community lacks tools for.

**How to avoid:**
- Add a "structured logging baseline" that uses schema validation and structured event recording (similar to what Langfuse, Braintrust, or OpenTelemetry provide) but without typed absence or provenance. This intermediate baseline separates the value of *typed absence specifically* from the value of *any validation at all*.
- Focus the real-agent measurement on *naturally occurring* violations, not deliberately injected ones. The acceptance criterion already requires this ("at least 1 naturally-occurring violation").
- Report results with appropriate framing: "forge detected X violations that the vanilla logger missed AND Y violations that a structured logger also missed."

**Warning signs:**
- All reported gains come from Scenario D-style deliberate violations, not naturally occurring ones.
- The experimental write-up claims forge prevents failures that any reasonable logging framework would also catch.
- No comparison is made against existing observability tools.

**Phase to address:**
The baseline establishment phase. Design the baseline comparison to be scientifically meaningful, not just favorable.

**References:**
- Langfuse, "AI Agent Observability" (2024): https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse
- Braintrust, "Agent Observability: Tracing Tool Calls" (2025): https://www.braintrust.dev/articles/agent-observability-tracing-tool-calls-memory

---

## Approximation Shortcuts

Shortcuts that seem reasonable but introduce systematic errors.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
| -------- | ----------------- | -------------- | --------------- |
| Using `_fake_count_tokens` to simulate compaction pressure | Deterministic test control | Completely bypasses real token counting behavior; real compaction triggers at different points with different content | Unit tests only; never for measurement |
| Treating structural ref resolution as provenance proof | Simple boolean check | Conflates "ref exists" with "content is recoverable" -- false confidence in compaction survival | Early development; must add semantic checks before measurement |
| Measuring only short tasks and claiming compaction works | Faster iteration, higher pass rates | Never exercises genuine context limits; project charter explicitly rejects this as false progress | Never -- this is a named false progress trap |
| Using source_refs=ALL_UPSTREAM as causal provenance | Correct by construction (never misses a dependency) | Destroys provenance specificity; every artifact depends on everything; useless for debugging | Acceptable as structural completeness check; must not be reported as causal provenance |
| Counting ForgeNullError exceptions as "violations detected" | Easy metric | Conflates compile-time type errors with runtime detection of agent failures | Development testing; must separate "protocol enforcement" from "failure detection" in measurements |

## Convention Traps

Common mistakes when interpreting or comparing results across the codebase.

| Convention Issue | Common Mistake | Correct Approach |
| ---------------- | -------------- | ---------------- |
| v1 canonical `state` vs legacy `absence_state` | Mixing old and new field names in test assertions or bridges | Always normalize through `normalize_absent_object()` before comparison; the `forge_v1_bridge` handles this but test code may bypass it |
| `pruned` vs `pruned_recoverable` | Using deprecated `pruned` alias in new code, triggering DeprecationWarning without noticing | Always use `pruned_recoverable`; the alias exists only for legacy ingress compatibility and should never appear in new test fixtures |
| Provenance "score" vs provenance "reachability" | Reporting `reversibility_score = 1.0` as "100% provenance" when it measures structural completeness only | Separate structural reachability (all refs resolve) from semantic reachability (content behind refs is intact) and report both |
| Trace compression ratio vs overhead ratio | Confusing `compression_ratio` (trace codec dedup savings) with `vs_vanilla_pct` (total size comparison against vanilla logger) | These measure different things: compression_ratio is internal forge efficiency; vs_vanilla_pct is the external overhead of adding provenance |
| Chamber `artifact_index` as set vs list | JSON serialization converts set to sorted list; deserialization converts back; but intermediate code may compare set to list | Always normalize to set before comparison; `load_chamber()` handles this but manual JSON parsing does not |

## Numerical Traps

Patterns that work for simple cases but fail for realistic calculations.

| Trap | Symptoms | Prevention | When It Breaks |
| ---- | -------- | ---------- | -------------- |
| SHA-256 hash comparison for round-trip verification | Hash mismatch despite identical content | Ensure deterministic JSON serialization (`sort_keys=True, ensure_ascii=True`) and consistent float formatting | When any step in the pipeline introduces non-deterministic JSON serialization (different Python versions, different JSON libraries, float precision) |
| Linear scan for `get_artifact_by_id` | Acceptable performance | Chamber stages list grows linearly; each lookup is O(n) | Chambers with 100+ stages (realistic for long agent sessions with revision cycles); consider building an ID->stage dict index |
| SQLite index for chamber persistence | Works for single-process demo | SQLite has file-locking limitations under concurrent access | Multi-agent or parallel experiment runs writing to the same data directory; use separate base_dirs or add proper connection pooling |
| `_generate_run_id` global counter | Deterministic in single-process demo | Counter resets on import; IDs collide across separate processes or test runs | Any multi-process experiment setup; use UUIDs or timestamp-based IDs for real experiments |
| Token counting as compaction trigger | Compaction fires predictably | Real token counting is model-dependent, non-linear with message structure, and may include system prompts not visible to the forge tools | Real LLM integration where forge cannot observe the full token budget |

## Interpretation Mistakes

Domain-specific errors in interpreting results beyond computational bugs.

| Mistake | Risk | Prevention |
| ------- | ---- | ---------- |
| Interpreting "0 forge violations on real tasks" as "the system has no failures" | Typed absence only catches structural absence violations; agent can fail without triggering any forge check | Design experiments that include known-failing tasks; if forge does not detect the failure, that IS a finding (negative result) |
| Interpreting high compression ratio as evidence of efficient provenance | Compression ratio measures dedup of repeated structures (producers, refs); it does not measure information preserved after LLM-level compaction | Report trace codec compression separately from LLM compaction survival; they are independent metrics |
| Interpreting MockLM experiment results as predictions for real LLM performance | MockLM provides a ceiling under ideal conditions (100% provenance, 6/6 violations, 87% compression); real performance will be strictly lower | Frame MockLM results as an upper bound anchor, not a prediction; measure the gap explicitly |
| Equating "provenance chain exists" with "you can recover the original" | A `pruned_recoverable` ref may point to content that was lossy-summarized; the ref exists but the content is degraded | Implement and measure an actual recovery operation: given a pruned_recoverable ref, can you retrieve content that matches the original hash? |
| Reporting results only for tasks that complete successfully | Survivorship bias -- the most interesting data comes from tasks that fail or trigger compaction | Include incomplete tasks, timeout cases, and error-halted chambers in measurements |

## "Looks Correct But Is Not" Checklist

Things that appear right but are missing critical pieces.

- [ ] **verify_trace():** Reports `valid: True` -- but only checks hash integrity of the encoded trace, not semantic fidelity of content after LLM-level compaction. Verify that `content_match` is tested against pre-compaction originals, not post-compaction summaries.
- [ ] **validate_chamber():** Returns `errors: []` -- but only checks structural invariants (refs resolve, no duplicates, monotonic index). Does not check whether output content is meaningful or whether the agent actually used the upstream artifacts it references.
- [ ] **source_refs completeness:** All refs resolve in artifact_index -- but refs point to every upstream artifact, not just causally relevant ones. 100% reachability with 0% specificity is not useful provenance.
- [ ] **Absence state coverage:** 8 canonical states cover the ontology -- but the open contract question remains: "Should timed_out and interrupted be distinct absence states?" Real agent runs WILL produce timeouts and interruptions. If these get mapped to `unknown` or `invalid`, the type system loses precision exactly where it matters most.
- [ ] **Compaction scenario C:** Reports provenance survived -- but uses `_fake_count_tokens` which returns 200K after 5 messages regardless of content. Real compaction triggers depend on actual token counts, which vary with message length, system prompt, and model-specific tokenization.
- [ ] **Experiment results JSON:** Written to disk with `default=str` serializer -- but this silently converts non-serializable objects (sets, datetimes) to strings, which may mask data structure issues when results are reloaded.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
| ------- | ------------- | -------------- |
| MockLM-to-real gap invalidates test assumptions | MEDIUM | Record real LLM sessions; build a "recorded playback" test tier; re-run forge validation against recorded sessions; update test fixtures |
| Compaction destroys provenance semantically | HIGH | Redesign measurement to separate structural and semantic reachability; add content-hash comparison before and after compaction; may require instrumenting the LLM runtime's compaction hook |
| Typed absence does not catch real failures | LOW | Reframe the contribution honestly; typed absence prevents ambiguity (valuable but limited); add complementary validation layers for semantic correctness |
| Provenance chains over-reference | LOW | Change `_build_source_refs` to capture direct causal inputs from the agent's actual context view rather than all upstream IDs; this is a targeted code change |
| Straw-man baseline undermines credibility | MEDIUM | Add a structured-logging intermediate baseline; re-run comparison with three tiers (vanilla, structured logging, forge); report differential value |

## Pitfall-to-Phase Mapping

How research phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
| ------- | ---------------- | ------------ |
| MockLM-to-real gap | Integration/baseline establishment | Run forge tools against at least 10 recorded real Zarathustra sessions before proceeding to live measurement |
| Compaction destroys provenance | Compaction measurement design | Define and measure "semantic reachability" metric; acceptance: can recover content matching original hash for >50% of pruned_recoverable refs |
| Typed absence insufficient | Violation detection measurement | Include known-failing tasks in campaign; if forge catches 0 naturally-occurring violations, report as negative finding |
| Over-referencing provenance | Baseline measurement | Measure provenance chain width (avg source_refs per stage); if >80% of refs are non-causal, flag for redesign |
| Straw-man baseline | Baseline establishment | Implement structured-logging baseline before running measurements; report three-tier comparison |

## Sources

- Cemri, Pan, Yang et al., "Why Do Multi-Agent LLM Systems Fail?" arXiv:2503.13657 (2025)
- "Where LLM Agents Fail and How They Can Learn From Failures" arXiv:2509.25370 (2025)
- AgentAsk: "Multi-Agent Systems Need to Ask" arXiv:2510.07593 (2025)
- "Characterizing Faults in Agentic AI" arXiv:2603.06847 (2025)
- Lethain, "Building an internal agent: Context window compaction" (2026)
- Factory.ai, "Evaluating Context Compression" (2025)
- Block Engineering, "Testing Pyramid for AI Agents" (2025)
- Langfuse, "AI Agent Observability" (2024)
- Braintrust, "Agent Observability: Tracing Tool Calls" (2025)
- Morph, "Compaction vs Summarization: Agent Context Management Compared" (2025)
- OpenAI, "Shell + Skills + Compaction: Tips for long-running agents" (2025)
- Google ADK, "Context compression" documentation (2025)
- Partnership on AI, "Prioritizing Real-Time Failure Detection in AI Agents" (2025)
- Composio, "Why AI Agent Pilots Fail in Production" (2025)

---

_Known pitfalls research for: Typed absence, provenance tracking, and recoverable compaction in agentic systems_
_Researched: 2026-03-15_
