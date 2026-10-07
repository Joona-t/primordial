# Phase 7 Research: Adversarial Task Design and Natural Violation Campaign

## Status: COMPLETE

## Phase Goal

Design a task corpus that stresses the failure modes typed absence should catch. Run 200+ instrumented agent sessions across diverse task categories. Either find natural violations or tighten the upper bound to <= 2%.

## Research Questions

- **RQ2b:** Do natural violations occur at detectable rates on longer/harder/more diverse agent tasks?

## v1.0 Baseline

- 0/30 natural violations on coding/patching tasks
- Clopper-Pearson 95% upper bound: 11.6%
- 44.4% detection rate on D1-D9 injected faults (4 of 9 types: D1, D2, D5, D9)
- 0% false positive rate
- Tasks: 3 short (S1-S3, <15K tokens) + 3 long (L1-L3, 128K+ tokens), all coding/patching domain

## Target Improvement

- 200+ runs to tighten CP upper bound to ~1.5% if still 0 natural violations
- 5+ task categories beyond coding/patching
- Tasks designed to stress specific violation types per the D1-D9 taxonomy
- At minimum, resolve whether violations are genuinely rare or whether v1.0 tasks were too easy

---

## 1. Literature Review: Chaos Engineering for Agent Systems

### 1.1 Direct Precedent: MAS-FIRE (Feb 2026)

MAS-FIRE [arxiv:2602.19843] is the closest methodological analogue to what Phase 7 needs. It defines a 15-fault taxonomy across two categories:

**Intra-agent faults (7 types):** Inexecutable Plan, Critical Information Loss, Memory Loss, Context Length Violation, Hallucination, Parameter Filling Error, Tool Selection Error.

**Inter-agent faults (8 types):** Role Ambiguity, Blind Trust, Instruction Logic Conflict, Instruction Ambiguity, Message Cycle, Message Storm, Message Broadcast Amplification.

Key methodological insight: MAS-FIRE uses three non-invasive injection mechanisms -- prompt modification, response rewriting, and message routing manipulation. Their finding that "failures rarely manifest as explicit crashes; instead, they appear as 'soft' semantic deviations" directly validates the Primordial thesis: structural violations propagate silently. Detection rates vary wildly by architecture: linear workflows drop to 0% robustness under configuration faults, while iterative architectures neutralize 40%+ of those same faults.

**Relevance to D1-D9:** MAS-FIRE's "Memory Loss" and "Critical Information Loss" map to D7 (trace data loss). "Context Length Violation" maps to D8 (content corruption). "Hallucination" maps to D2 (ungrounded summary). The taxonomy does NOT cover null-discipline violations (D5) or seal violations (D9) because these are forge-specific structural invariants.

### 1.2 ReliabilityBench (Jan 2026)

ReliabilityBench [arxiv:2601.06112] defines the reliability surface R(k, epsilon, lambda) across three dimensions: consistency (k), robustness (epsilon), and fault tolerance (lambda). Their fault injection taxonomy includes:

- **Network faults:** TransientTimeout, ConnectionReset, SoftRateLimit, HardRateLimit
- **Data faults:** PartialResponse, SchemaDrift, StaleData, EmptyResponse

Key finding: Rate limiting is the most damaging fault type (2.5% degradation below baseline). EmptyResponse and PartialResponse are recoverable. The chaos-engineering-style framework operates across 4 domains (scheduling, travel, support, e-commerce) with 1,280 episodes.

**Relevance to D1-D9:** EmptyResponse maps directly to D1 (empty output without typed absence). PartialResponse maps to D5 (null discipline violations -- bare None in semantic fields). SchemaDrift maps to D8 (content corruption). StaleData could produce D3 (dangling references to stale artifacts).

### 1.3 Agentic AI Fault Taxonomy (Mar 2026)

The most comprehensive empirical fault taxonomy to date [arxiv:2603.06847] analyzed 385 faults from 40 open-source agent repositories, validated by 145 practitioners (mean relevance 3.97/5, Cronbach alpha 0.904). Five architectural dimensions:

1. **Agent Cognition & Orchestration** (83 faults): LLM integration, agent lifecycle and state management
2. **Tooling, Integration & Actuation** (66 faults): tool execution, external connectivity, resource manipulation
3. **Perception, Context & Memory** (72 faults): context persistence, input interpretation
4. **Runtime & Environment Grounding** (87 faults): dependency management, platform compatibility
5. **System Reliability & Observability** (67 faults): error recovery, UI defects

Key finding: "Failures in agentic AI systems frequently traverse architectural boundaries." Token management issues leading to authentication failures showed lift = 181.5 in association rule mining, confirming cross-cutting failure propagation.

**Relevance to D1-D9:** Category 3 (Context & Memory) directly produces D7 (trace data loss through context persistence failures), D2 (ungrounded summaries from state serialization defects), and D1 (empty outputs from input interpretation failures). Category 1 (Agent Lifecycle & State) maps to D6 (post-seal registration from defective termination) and D9 (seal violation from state inconsistencies).

### 1.4 Context Compression and State Loss

Factory.ai's evaluation of context compression strategies (2026) measured probe-based functional quality across 36,611 production engineering sessions. Key finding: **artifact tracking scored only 2.19-2.45 out of 5.0 across all compression strategies** (Factory, OpenAI, Anthropic). This means the specific type of information forge tracks -- provenance references, artifact chains -- is the weakest point in all existing compression approaches.

The ACON framework (Oct 2025) showed 26-54% peak token reduction on AppWorld, OfficeBench, and Multi-objective QA, but measures task completion, not provenance integrity.

Industry data: Nearly 65% of enterprise AI failures in 2025 were attributed to context drift or memory loss during multi-step reasoning -- not raw context exhaustion.

### 1.5 Error Compounding in Multi-Agent Systems

DeepMind's Science of Scaling research found that uncoordinated multi-agent systems ("bag of agents") exhibit 17.2x error amplification. The math: a 10-step process with 99% per-step success yields only 90.4% end-to-end success. For the Primordial violation detection question, this means: if each step has a 1% chance of producing a structural violation, a 10-step task has approximately 10% probability of surfacing at least one.

### 1.6 Jepsen Analogy

Jepsen tests distributed systems by generating load, introducing failures (network partitions, process crashes, clock skew), and checking whether stated guarantees hold. The Primordial analogue: generate agent workload, introduce environmental stress (context pressure, tool failures, ambiguous outputs), check whether structural invariants (D1-D9) hold.

Key methodological lesson from Jepsen: **the faults must be realistic**. Jepsen tests real network partitions, not simulated ones. Phase 7 should inject stress conditions that actually occur in production agent sessions, not artificial corner cases.

---

## 2. Taxonomy of Task Categories Ranked by Violation Likelihood

### Mapping: Task Stress Factor to Violation Type

| Stress Factor | Primary D-Type Targets | Secondary Targets | Mechanism |
|---|---|---|---|
| Empty/timeout LLM responses | **D1** (empty output) | D5 (null fields) | LLM returns empty string or times out mid-generation |
| Long provenance chains (10+ steps) | **D2** (ungrounded summary) | D7 (trace data loss) | Summarization drops source_refs; trace buffer overflow |
| Branching/backtracking execution | **D3** (dangling reference) | D2, D7 | Refs to abandoned branch artifacts that get pruned |
| Parallel/concurrent sub-agent calls | **D4** (duplicate artifact ID) | D3 (cross-ref to other agent's artifacts) | Race condition in ID generation; refs across agent boundaries |
| Partial/malformed tool outputs | **D5** (null discipline) | D1, D8 | Tool returns partial JSON; fields missing |
| Error recovery after completion | **D6** (post-seal registration) | D9 (seal violation) | Agent "done" then forced to retry; late callback |
| Context window filling + compaction | **D7** (trace data loss) | D2, D3 | Compaction drops provenance-critical tokens |
| Encoding edge cases + format mixing | **D8** (content corruption) | D5 | Binary data, Unicode, mixed formats corrupt artifact content |
| Task resumption after interruption | **D9** (seal violation) | D6, D3 | Sealed session reopened; stale refs |

### Task Category Rankings (by expected violation surface area)

**Tier A -- Highest violation likelihood (targets 4+ D-types each):**

| Rank | Category | D-Types Stressed | Rationale |
|---|---|---|---|
| 1 | Multi-step tool chains with compaction pressure | D1, D2, D3, D5, D7, D8 | Longest sessions, most context pressure, most tool interactions |
| 2 | Backtracking/retry-heavy tasks | D2, D3, D5, D6, D7, D9 | Creates abandoned branches, forces re-registration after completion signals |
| 3 | Parallel sub-agent coordination | D1, D3, D4, D5, D7 | Concurrent ID generation, cross-agent refs, merged outputs |
| 4 | Error recovery after nominal completion | D3, D5, D6, D8, D9 | Post-seal writes, re-opened sessions, stale references |

**Tier B -- Moderate violation likelihood (targets 2-3 D-types each):**

| Rank | Category | D-Types Stressed | Rationale |
|---|---|---|---|
| 5 | Ambiguous/partial tool outputs | D1, D5, D8 | Missing fields, partial JSON, empty responses |
| 6 | Long-horizon reasoning chains | D2, D7 | Summarization drops provenance; trace grows large |
| 7 | Context window overflow tasks | D7, D8 | Compaction event is the primary stress |
| 8 | Format/encoding edge case tasks | D5, D8 | Unicode, binary, mixed encodings corrupt content |

**Tier C -- Low but nonzero violation likelihood:**

| Rank | Category | D-Types Stressed | Rationale |
|---|---|---|---|
| 9 | Simple single-step tasks (control) | D1 (only if LLM fails) | Baseline: should produce 0 violations |
| 10 | Read-only analysis tasks (control) | None expected | Pure analysis, no state mutation |

---

## 3. Specific Task Examples (Adversarial Corpus)

### Category A1: Multi-Step Tool Chains with Compaction Pressure

**TASK-A1a: Full-Stack Feature Implementation**
Execute a 15-step feature addition across frontend, backend, database, and tests. Steps: (1) read spec, (2) design schema, (3) create migration, (4) write model, (5) write API endpoint, (6) write validation, (7) write frontend component, (8) write frontend API client, (9) write unit tests for model, (10) write unit tests for API, (11) write integration test, (12) run linter, (13) fix lint errors, (14) run all tests, (15) generate summary. Each step depends on outputs of previous steps. Target: 150K+ tokens.
*Stress mechanism:* By step 10, early artifacts (schema design from step 2) may be compacted. The provenance chain must survive.

**TASK-A1b: Repository-Wide Refactoring**
Rename a core data structure used in 20+ files across a codebase. Steps: identify all usages, plan change order, execute changes file-by-file, update imports, update tests, run tests, fix failures, re-run. Expected: 200K+ tokens with 10+ retry cycles.
*Stress mechanism:* Each file change references the plan artifact. After compaction, dangling refs to the plan emerge.

**TASK-A1c: Multi-File Bug Investigation**
Given a failing test, trace the bug through 8+ files across 4 modules. Read each file, build a dependency graph, identify the root cause, propose fix, test fix, iterate if wrong. Expected: 5-8 investigation rounds.
*Stress mechanism:* Each investigation round produces artifacts with refs to all previously read files. The provenance DAG grows wide and deep.

### Category A2: Backtracking/Retry-Heavy Tasks

**TASK-A2a: Adversarial Linting Gauntlet**
Write code that must pass 12 custom lint rules, where rules conflict (e.g., "max line length 80" vs "no line continuation"). Agent must produce code, run linter, fail, backtrack, revise, re-run. Expected: 7-15 retry cycles.
*Stress mechanism:* Each failed attempt creates artifacts that are "abandoned" -- refs to them from the retry must be correctly typed as superseded. D3 (dangling ref to abandoned attempt) and D6 (re-registration after "done" signal from linter pass).

**TASK-A2b: Test-Driven Development with Moving Target**
Write implementation to pass tests, but tests are updated after each submission to add edge cases. Agent: read tests, implement, run, pass some, get new tests, implement more, run, iterate. Expected: 5-10 rounds.
*Stress mechanism:* Agent must maintain references to evolving test specifications. Older test refs become stale (D3). Summary of "what tests require" may lose grounding (D2).

**TASK-A2c: Configuration Debugging**
Fix a deployment configuration where 3 of 12 settings are wrong, but changing one may break another. Agent must try combinations, roll back failed changes, track which combinations have been tried. Expected: 8-20 iterations.
*Stress mechanism:* Backtracking requires referencing earlier states. If the "rollback target" artifact has been compacted, D3 (dangling ref) and D7 (trace data loss) surface.

### Category A3: Parallel Sub-Agent Coordination

**TASK-A3a: Divide-and-Conquer Code Review**
Split a 500-line PR into 5 logical chunks. Dispatch sub-analysis for each chunk concurrently. Merge findings into unified review. Each chunk-analysis produces artifacts with IDs.
*Stress mechanism:* Concurrent ID generation must avoid D4 (duplicate IDs). Cross-chunk references (e.g., "this change in chunk 3 conflicts with chunk 1") require refs across sub-agent boundaries (D3 if the other agent's artifacts are not visible).

**TASK-A3b: Parallel Test Execution and Aggregation**
Run 6 test suites concurrently, collect results, identify failures, aggregate into a single report with references to each suite's output.
*Stress mechanism:* If one suite times out (empty output), D1 surfaces. If results arrive out of order, late arrivals after the "report sealed" event produce D6.

### Category A4: Error Recovery After Completion

**TASK-A4a: Deploy-Then-Rollback**
Complete a deployment task (write config, apply, verify). Mark as done. Then inject a failure signal (health check fails). Agent must reopen the "completed" task, diagnose, and rollback.
*Stress mechanism:* Direct D6 (post-seal registration) and D9 (seal violation). The agent must register new artifacts in a chamber that was sealed.

**TASK-A4b: Review-Approve-Reject Cycle**
Agent writes code, submits for "review" (automated reviewer). Reviewer approves. Task sealed. Then reviewer sends "actually, I found a problem" -- agent must re-enter the sealed context.
*Stress mechanism:* The re-entry after approval-seal tests D9 directly. References to the "approved" state from the rejection path test D3.

### Category B5: Ambiguous/Partial Tool Outputs

**TASK-B5a: API with Intermittent Failures**
Query an API that returns valid JSON 80% of the time, empty responses 10%, and malformed JSON 10%. Agent must handle all cases, retry on failure, and report results.
*Stress mechanism:* Empty responses should be typed as `not_generated` or `invalid`, not bare null. Tests D1 directly. Malformed JSON tests D5 and D8.

**TASK-B5b: File Read with Encoding Issues**
Read a file that contains mixed UTF-8 and Latin-1 encoding. Extract structured data. Some fields will decode to empty strings or garbage.
*Stress mechanism:* Empty decoded fields test D5 (null discipline -- is the field absent or empty?). Garbage content tests D8.

### Category B6: Long-Horizon Reasoning Chains

**TASK-B6a: Multi-Hop Research Synthesis**
Given 10 documents, answer a question that requires chaining facts across 5+ documents. Each document read is an artifact. The final answer must cite source_refs to specific documents.
*Stress mechanism:* If the agent summarizes intermediate findings, the summary may lose source_refs (D2). The provenance chain is 5+ hops deep.

**TASK-B6b: Iterative Data Analysis Pipeline**
Load dataset, clean, transform, analyze, visualize, interpret, report. Each step produces artifacts depending on the previous. 10+ sequential steps.
*Stress mechanism:* By step 10, step 1 artifacts (raw data load) may be compacted. References from the report to early steps test D3 and D7.

### Category B7: Context Window Overflow

**TASK-B7a: Large Codebase Exploration**
Navigate a 50-file codebase to answer an architecture question. Agent must read 20+ files. By file 15, the context window fills and compaction triggers.
*Stress mechanism:* Post-compaction, refs to files read in the first batch may dangle (D3). Trace metadata from early reads may be lost (D7).

### Category C9: Control -- Simple Single-Step (Baseline)

**TASK-C9a: Add License Header** (same as v1.0 TASK-S1)
**TASK-C9b: Fix One-Line Bug** (same as v1.0 TASK-S2)
**TASK-C9c: Write Three Unit Tests** (same as v1.0 TASK-S3)

These are the v1.0 control tasks. Expected: 0 violations. Serves as the negative control.

---

## 4. Statistical Power Analysis

### 4.1 Core Question

"How many runs do we need to detect a violation rate of p% with adequate statistical power?"

The detection model: each run is a Bernoulli trial with probability p of producing at least one natural violation. We observe the total count of violation-producing runs.

### 4.2 Runs Needed to Detect Violation Rate p with Power (1-beta)

The minimum N to guarantee P(at least 1 violation in N runs) >= power:

| True Rate (p) | Power = 0.80 | Power = 0.90 | Power = 0.95 | Power = 0.99 |
|---|---|---|---|---|
| 1% | 161 | 230 | 299 | 459 |
| 2% | 80 | 114 | 149 | 228 |
| 3% | 53 | 76 | 99 | 152 |
| 5% | 32 | 45 | 59 | 90 |
| 10% | 16 | 22 | 29 | 44 |
| 15% | 10 | 15 | 19 | 29 |
| 20% | 8 | 11 | 14 | 21 |

### 4.3 Clopper-Pearson Upper Bounds (if 0 violations observed)

Given N clean runs with 0 violations, the 95% confidence upper bound on the true rate:

| N (runs) | CP 95% Upper Bound |
|---|---|
| 30 (v1.0) | 9.50% |
| 50 | 5.82% |
| 59 | 4.95% |
| 100 | 2.95% |
| 150 | 1.98% |
| 200 | 1.49% |
| 300 | 0.99% |
| 500 | 0.60% |

**Interpretation:** v1.0 with 30 runs cannot rule out rates up to ~10%. To get below 5%, we need 59 runs. To get below 2%, we need 149 runs. To get below 1%, we need 299 runs.

### 4.4 Power at Specific Campaign Sizes

| N | p=2% | p=5% | p=10% | p=15% | p=20% |
|---|---|---|---|---|---|
| 30 (v1.0) | 45.5% | 78.5% | 95.8% | 99.2% | 99.9% |
| 50 | 63.6% | 92.3% | 99.5% | ~100% | ~100% |
| 100 | 86.7% | 99.4% | ~100% | ~100% | ~100% |
| 150 | 95.2% | ~100% | ~100% | ~100% | ~100% |
| 200 | 98.2% | ~100% | ~100% | ~100% | ~100% |
| 300 | 99.8% | ~100% | ~100% | ~100% | ~100% |

**Key insight:** At N=200, we have 98.2% power to detect a 2% violation rate. This is the campaign target.

### 4.5 Bayesian Perspective

Using a uniform Beta(1,1) prior, the posterior after 0 violations in N runs is Beta(1, N+1). The posterior probability that the true rate exceeds a threshold:

| N | P(rate > 1%) | P(rate > 2%) | P(rate > 5%) | P(rate > 10%) |
|---|---|---|---|---|
| 30 | 0.732 | 0.535 | 0.204 | 0.038 |
| 50 | 0.599 | 0.357 | 0.073 | 0.005 |
| 100 | 0.362 | 0.130 | 0.006 | ~0 |
| 200 | 0.133 | 0.017 | ~0 | ~0 |

**At N=200 with 0 violations:** Only 1.7% posterior probability that the true rate exceeds 2%. This is a strong negative result.

### 4.6 Recommended Campaign Size

**Primary target: N = 200 runs.**
- If violations found: characterize rate, identify which task categories produce them
- If 0 violations: CP upper bound = 1.49%, Bayesian P(rate > 2%) = 1.7%
- Either outcome is a publishable result

**Stretch target: N = 300 runs.**
- CP upper bound < 1% (if 0 violations)
- 99.8% power to detect a 2% rate
- Only pursue if 200 runs is operationally feasible and 0 violations observed

---

## 5. Task Corpus Specification

### 5.1 Corpus Size and Distribution

**Total: 20 task templates, 200 runs minimum.**

Distribution across categories (weighted by violation likelihood):

| Category | Task Count | Runs Per Task | Total Runs | Weight | Rationale |
|---|---|---|---|---|---|
| A1: Multi-step chains + compaction | 3 | 12 | 36 | 18% | Highest D-type surface area (6 types) |
| A2: Backtracking/retry | 3 | 12 | 36 | 18% | Creates abandoned refs + post-seal writes |
| A3: Parallel coordination | 2 | 10 | 20 | 10% | Concurrent ID conflicts |
| A4: Error recovery post-completion | 2 | 10 | 20 | 10% | Direct D6/D9 stress |
| B5: Ambiguous/partial outputs | 2 | 10 | 20 | 10% | Direct D1/D5 stress |
| B6: Long-horizon reasoning | 2 | 10 | 20 | 10% | Provenance chain depth |
| B7: Context overflow | 2 | 10 | 20 | 10% | Compaction-triggered data loss |
| B8: Format/encoding edge cases | 1 | 8 | 8 | 4% | D8 stress |
| C9: Control (v1.0 tasks) | 3 | 7 | 21 | 10% | Baseline comparison |
| **Total** | **20** | -- | **201** | 100% | |

### 5.2 Task Difficulty Tiers

| Tier | Token Range | Steps | Retry Cycles | Example Tasks |
|---|---|---|---|---|
| SHORT | <32K | 1-3 | 0-1 | C9a-c, B5b |
| MEDIUM | 32K-128K | 4-8 | 1-3 | B5a, B6a, A3b, A4b |
| LONG | 128K-256K | 9-15 | 3-8 | A1a, A1b, A2a, A2b, B7a |
| EXTREME | 256K+ | 15+ | 8+ | A1c (if investigation loops), A2c |

### 5.3 Task Template Schema

Each task template includes:

```
{
  "task_id": "TASK-A1a",
  "category": "A1-multistep-chains",
  "tier": "LONG",
  "title": "Full-Stack Feature Implementation",
  "prompt": "<exact prompt text>",
  "workspace_setup": {
    "files": ["<list of files to provide>"],
    "tools": ["<list of tools available>"],
    "constraints": ["<rate limits, timeouts, etc.>"]
  },
  "success_criteria": ["<automated checks>"],
  "expected_steps": 15,
  "expected_tokens": "150K-250K",
  "expected_retries": "3-7",
  "target_violations": ["D2", "D3", "D7"],
  "stress_mechanism": "<description of how stress is applied>",
  "control_variant": "<same task without stress, for comparison>"
}
```

### 5.4 Instrumentation Requirements

Every run must record:

1. **Forge chamber** (existing): Full provenance DAG, artifact states, refs, seals
2. **Raw LLM transcript**: Complete input/output for every LLM call (for post-hoc analysis)
3. **Tool call log**: Every tool invocation with input, output, timing, errors
4. **Compaction events**: When and how context was compacted (if observable)
5. **Token counts**: Per-call and cumulative, to confirm tier classification
6. **Wall clock time**: Start, end, per-step timing
7. **Agent framework version**: Exact version of runtime under test

### 5.5 Violation Detection Pipeline

For each completed run:

1. **Post-hoc chamber validation** (existing `validate_chamber()`): D1, D2, D5, D9
2. **Extended validation** (new, Phase 7 deliverable):
   - D3: Check all refs resolve to existing artifacts (not just structural validity)
   - D4: Check all artifact IDs are unique within the chamber
   - D6: Check no registrations occur after seal timestamp
   - D7: Compare tool call log against trace -- flag any tool calls missing from trace
   - D8: Content hash verification on all artifacts with known-good checksums
3. **Statistical analysis**: Per-task, per-category, and aggregate violation rates with CIs

---

## 6. Control Conditions

### 6.1 Within-Task Controls

Each Tier A/B task has a **defanged variant** (same task, no stress):
- A1a-control: Same 15-step task but workspace is pre-configured to succeed on first try (no retries expected)
- A2a-control: Same linting task but with non-conflicting rules (no backtracking)
- A3a-control: Same code review but sequential, not parallel
- B5a-control: Same API but always returns valid JSON (no failures)

**Purpose:** If adversarial tasks show violations but controls do not, the stress mechanism is the cause. If both show violations, the task structure itself produces violations regardless of stress.

### 6.2 Cross-Framework Controls

If feasible (depends on Phase 8 adapter availability):
- Run the same adversarial corpus on 2+ agent frameworks (e.g., OpenClaw/Zarathustra, LangChain ReAct, Claude Code native)
- Compare violation rates across frameworks
- This isolates framework-specific bugs from fundamental LLM-level violations

### 6.3 Baseline Comparison

- **v1.0 rate:** 0/30 = 0% (CP upper 9.5%)
- **v2.0 control rate:** 0/21 expected (C9 tasks, same as v1.0)
- **v2.0 adversarial rate:** Target of analysis
- **Statistical test:** Fisher's exact test comparing adversarial vs control violation counts

### 6.4 Injection Sanity Check

Run 10 adversarial tasks WITH injected faults (D1-D9) to confirm the extended detection pipeline catches them. This is the positive control -- if injected faults are missed, the pipeline has a detection gap before the natural campaign even starts.

---

## 7. Adversarial Prompt Design Principles

### 7.1 Fairness Criterion

Adversarial tasks must satisfy:

1. **Realistic:** The task could plausibly appear in a real agent workflow. No "write a program that crashes the forge." Tasks should be things developers actually ask agents to do.
2. **Stress, not sabotage:** The task creates conditions where violations CAN occur, but does not force them. An ideal agent could complete the task with 0 violations.
3. **Observable:** The violation, if it occurs, is detectable by the forge validation pipeline. We do not design tasks targeting undetectable violations (that is circular).
4. **Graduated:** Each category has easy, medium, and hard variants. This lets us identify the difficulty threshold where violations start appearing.

### 7.2 Anti-Patterns to Avoid

- **Prompt injection masquerading as adversarial testing:** Do not inject instructions that tell the agent to corrupt its own output. The goal is to stress the SYSTEM, not trick the LLM.
- **Impossible tasks:** Tasks that cannot be completed do not test violation detection -- they test error handling. The task must be solvable, but difficult enough to stress the agent's state management.
- **Micro-benchmarks:** Single-call tests do not exercise the provenance chain. Every adversarial task must involve at least 3 dependent steps.
- **Framework-specific exploits:** Do not design tasks that exploit known bugs in a specific agent framework. The violations should be structural, not framework-specific.

### 7.3 Stress Calibration

Use the ReliabilityBench epsilon/lambda framework for calibration:

- **epsilon (perturbation intensity):** 0.0 (control), 0.1 (mild), 0.2 (moderate) -- applied to task ambiguity
- **lambda (fault probability):** 0.0 (control), 0.1 (mild), 0.2 (moderate), 0.3 (heavy) -- applied to tool failure rates

Each adversarial task should be run at multiple stress levels:
- Control (epsilon=0, lambda=0): 3 runs
- Mild (epsilon=0.1, lambda=0.1): 3 runs
- Moderate (epsilon=0.2, lambda=0.2): 3 runs
- Heavy (epsilon=0.1, lambda=0.3): 3 runs
- Total per task: 12 runs at 4 stress levels

---

## 8. Expected Outcomes and Decision Tree

### 8.1 Outcome A: Natural Violations Detected (>=1)

If violations are found:
1. Characterize: Which D-types? Which task categories? Which stress levels?
2. Compute violation rate with CI
3. Compare adversarial vs control rates (Fisher's exact)
4. Identify the minimum stress level that triggers violations
5. **Verdict:** RQ2b PASS -- natural violations exist at rate p [CI]. Forge detection is solving a real problem.

### 8.2 Outcome B: Zero Natural Violations (0/200)

If no violations found:
1. CP upper bound: 1.49% (significantly tighter than v1.0's 11.6%)
2. Bayesian posterior: P(rate > 2%) = 1.7%
3. **Verdict:** RQ2b NEGATIVE (strong) -- natural violations occur at rate < 1.5% even on adversarial tasks. This is either:
   - (a) The LLM runtime already prevents structural violations internally, OR
   - (b) The forge detection pipeline misses natural violations that DO occur (detection gap)

To disambiguate (a) vs (b), examine raw transcripts for violations the pipeline missed.

### 8.3 Decision Rule for Stretch to N=300

If 0 violations at N=200 AND manual transcript review finds candidate violations the pipeline missed: extend to N=300 WITH improved detection pipeline. Otherwise, accept the negative finding and proceed to Phase 8.

---

## 9. Existing Benchmarks: What to Borrow

### 9.1 SWE-Bench / SWE-Bench Pro

**What to borrow:** Multi-file, multi-step coding tasks that require reading, modifying, and testing. SWE-Bench Pro specifically targets long-horizon tasks.
**What NOT to borrow:** The evaluation methodology (test pass/fail). We do not care if the agent solves the task -- we care about structural integrity of the provenance chain DURING the attempt.
**Adaptation:** Select 5-10 SWE-Bench issues known to require 5+ file modifications and 3+ retry cycles. Instrument with forge. Do not modify the tasks -- use them as-is.

Relevant finding: 24.4% of SWE-Bench patches were incorrectly evaluated as passed, indicating widespread silent errors that structural validation could catch.

### 9.2 TAU-Bench / TAU2-Bench

**What to borrow:** Multi-turn tool-use tasks with dual-control scenarios (agent and user manipulate shared state). The distinction between reasoning errors and coordination errors is valuable.
**Adaptation:** Use the retail and airline domains (highest failure rates). Instrument tool calls with forge provenance tracking.

Key finding: Even state-of-the-art agents succeed on <50% of TAU-bench tasks, with pass@8 < 25% in retail. These high-failure-rate tasks are prime candidates for violation detection.

### 9.3 CyBench

**What to borrow:** Multi-step CTF tasks requiring reconnaissance, tool use, and persistence. The subtask structure maps well to provenance depth.
**Adaptation:** Use 3-5 medium-difficulty CTF tasks (first-solve-time 5-30 minutes). These are inherently multi-step with dead-end investigation paths -- perfect for D3 (dangling refs to abandoned investigation branches).

### 9.4 WebArena

**What to borrow:** Real web interaction tasks with nondeterministic outcomes. Tool failures (page load errors, timeouts) are natural.
**Adaptation:** WebArena-Verified tasks in e-commerce and forum domains. The nondeterminism means each run may follow a different path -- good for testing provenance chain robustness across variable execution paths.

### 9.5 GAIA

**What to borrow:** Multi-hop reasoning tasks requiring tool use (web search, calculation, document reading). Level 2-3 tasks require 5+ reasoning steps.
**Adaptation:** Level 2-3 GAIA tasks that require chaining facts across multiple documents. Instrument each document access as a forge artifact. The final answer must have source_refs -- a natural test of D2 (ungrounded summary).

---

## 10. Implementation Roadmap

### Phase 7a: Detection Pipeline Extension (prerequisite)

Extend `validate_chamber()` to cover D3, D4, D6, D7, D8 (currently only D1, D2, D5, D9):
- D3: Ref target existence check (all refs resolve to artifacts in the chamber)
- D4: Unique artifact ID enforcement
- D6: Post-seal timestamp check (no registrations after seal time)
- D7: Tool-call-log-to-trace completeness check
- D8: Content hash re-verification

**Acceptance criterion:** Injected faults for D3, D4, D6, D7, D8 are detected at >= 90% on the injection sanity check (Section 6.4).

### Phase 7b: Task Corpus Construction

Implement all 20 task templates with workspace setup scripts. Each task:
- Automated workspace provisioning
- Automated success criteria checking
- Forge instrumentation hooks
- Transcript recording

### Phase 7c: Campaign Execution

Run 201 sessions across 20 tasks at 4 stress levels:
- Tier A tasks: 12 runs each (3 per stress level) x 10 tasks = 120 runs
- Tier B tasks: 10 runs each (varying stress) x 7 tasks = 70 runs
- Tier C tasks: 7 runs each (control only) x 3 tasks = 21 runs
- Total: 211 runs (exceeds 200 target)

### Phase 7d: Analysis and Reporting

1. Per-task violation counts with CIs
2. Per-category violation rates
3. Adversarial vs control comparison (Fisher's exact)
4. Stress level dose-response analysis
5. D-type distribution of any found violations
6. Manual transcript review of highest-stress runs (regardless of violation status)
7. Updated RQ2b verdict

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Natural violations genuinely rare (<1%) | HIGH | Medium -- negative finding is still publishable | Accept negative finding with strong statistical bound |
| Detection pipeline still misses natural violations | MEDIUM | High -- undercounts the real rate | Manual transcript review of 20+ runs as validation |
| Task corpus too easy (agents handle stress gracefully) | MEDIUM | Medium -- wasted compute | Include extreme-tier tasks; calibrate difficulty via pilot runs |
| Agent framework masks violations internally | LOW | High -- violations occur but are never externalized | Compare 2+ frameworks; inspect framework internals |
| Cost/time prohibitive (200+ instrumented runs) | MEDIUM | Medium -- may need to reduce N | Prioritize Tier A tasks; reduce if pilot shows early signal |

---

## 12. Key References

### Direct Precedent
- [MAS-FIRE: Fault Injection and Reliability Evaluation for LLM-Based Multi-Agent Systems](https://arxiv.org/abs/2602.19843) (Feb 2026)
- [ReliabilityBench: Evaluating LLM Agent Reliability Under Production-Like Stress Conditions](https://arxiv.org/abs/2601.06112) (Jan 2026)
- [Characterizing Faults in Agentic AI: A Taxonomy of Types, Symptoms, and Root Causes](https://arxiv.org/abs/2603.06847) (Mar 2026)

### Chaos Engineering Methodology
- [Assessing and Enhancing the Robustness of LLM-based Multi-Agent Systems Through Chaos Engineering](https://arxiv.org/abs/2505.03096) (May 2025)
- [LLM-Powered Fully Automated Chaos Engineering](https://arxiv.org/abs/2511.07865) (Nov 2025, ASE 2025)
- [ChaosEater: Fully Automating Chaos Engineering with Large Language Models](https://openreview.net/forum?id=8pbyay0prT)
- [Jepsen: Distributed Systems Safety Research](https://jepsen.io/)

### Agent Benchmarks
- [SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?](https://arxiv.org/abs/2509.16941)
- [Are "Solved Issues" in SWE-bench Really Solved Correctly?](https://software-lab.org/publications/icse2026_SWE-bench-correctness.pdf) (ICSE 2026)
- [TAU-Bench: A Benchmark for Tool-Agent-User Interaction](https://arxiv.org/abs/2406.12045)
- [Cybench: A Framework for Evaluating Cybersecurity Capabilities](https://arxiv.org/abs/2408.08926) (ICLR 2025)
- [WebArena-Verified](https://github.com/ServiceNow/webarena-verified) (NeurIPS 2025)
- [GAIA Benchmark](https://huggingface.co/gaia-benchmark)

### Context Management and State Loss
- [Evaluating Context Compression for AI Agents](https://factory.ai/news/evaluating-compression) (Factory.ai, 2026)
- [ACON: Optimizing Context Compression](https://openreview.net/pdf?id=7JbSwX6bNL) (Oct 2025)
- [AI Agent Context Compression: Strategies for Long-Running Sessions](https://zylos.ai/research/2026-02-28-ai-agent-context-compression-strategies) (Zylos, Feb 2026)
- [Context compression - Agent Development Kit](https://google.github.io/adk-docs/context/compaction/) (Google ADK)

### Backtracking and Recovery
- [Task Memory Engine: Enhancing State Awareness for Multi-Step LLM Agent Tasks](https://arxiv.org/abs/2504.08525)
- [From Spark to Fire: Modeling and Mitigating Error Cascades in LLM-Based Multi-Agent Collaboration](https://arxiv.org/abs/2603.04474) (Mar 2026)

### Error Compounding
- [Why Your Multi-Agent System is Failing: Escaping the 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/) (DeepMind Science of Scaling, 2026)

---

_Research completed: 2026-03-27_
_Statistical analysis: scipy.stats exact binomial + Clopper-Pearson + Bayesian Beta posterior_
_Literature: 15+ papers and frameworks from 2025-2026_
