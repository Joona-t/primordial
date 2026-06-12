# Phase 2.1: Genuine LLM Compaction Experiments -- Experimental Protocol

**Status:** Research complete, protocol ready for review
**Date:** 2026-03-27
**Predecessor:** v1.0 Phase 4 (simulated compaction, structural reachability 0.93-0.25)
**Research Question:** RQ3b -- Does structural reachability hold under genuine LLM context-window compaction (not simulated)?

---

## 1. Executive Summary

v1.0 established that forge provenance chains are structurally resilient under
simulated compaction (programmatic deletion): 82% reachability at 50% deletion,
backtracking threshold at 80%. But simulated deletion is a lower bound. The
critical gap: we do not know what happens when a real LLM summarizes the context
window, because summarization is fundamentally different from deletion. It may
preserve artifact IDs (boosting reachability) or it may paraphrase them away
(destroying provenance). Only genuine measurement can resolve this.

This protocol defines three experimental tracks:

- **Track A (API-Controlled):** Use Anthropic's `compact_20260112` API with
  `pause_after_compaction` to capture exact before/after state at the compaction
  boundary. Full control, full observability. N=60 trials.

- **Track B (Agent Benchmark):** Run forge-instrumented agent on SWE-Bench
  Verified Hard tasks to trigger natural compaction under realistic coding
  workloads. Ecological validity. N=30 trials.

- **Track C (Ablation):** Test compaction survival under varied conditions:
  custom summarization instructions, different trigger thresholds, degraded
  models. Mechanism identification. N=90 trials.

Total: 180 experimental trials, ~$800-1200 API cost (Sonnet-heavy design).

---

## 2. Background: How Real LLM Compaction Works

### 2.1 Anthropic's compact_20260112 API

The Anthropic Messages API provides server-side compaction via the
`compact_20260112` beta strategy. Key mechanics:

1. **Trigger:** When input tokens exceed a configurable threshold (default
   150,000; minimum 50,000), the API automatically generates a summary.
2. **Compaction block:** The API returns a content block with
   `"type": "compaction"` containing the summary text.
3. **History replacement:** On subsequent requests, the API drops all message
   blocks prior to the compaction block, continuing from the summary only.
4. **Pause mode:** Setting `pause_after_compaction: true` causes the API to
   return with `stop_reason: "compaction"` after generating the summary,
   allowing the client to inspect and modify before continuing.
5. **Custom instructions:** The `instructions` parameter replaces the default
   summarization prompt entirely.

**Default summarization prompt:**
```
You have written a partial transcript for the initial task above. Please write
a summary of the transcript. The purpose of this summary is to provide
continuity so you can continue to make progress towards solving the task in a
future context, where the raw history above may not be accessible and will be
replaced with this summary. Write down anything that would be helpful,
including the state, next steps, learnings etc. You must wrap your summary
in a <summary></summary> block.
```

**Compaction block JSON format:**
```json
{
  "content": [
    {
      "type": "compaction",
      "content": "Summary of the conversation: ..."
    },
    {
      "type": "text",
      "text": "Based on our conversation so far..."
    }
  ]
}
```

**Supported models:** Claude Opus 4.6, Claude Sonnet 4.6.

**Key parameter for this experiment:** `pause_after_compaction: true` gives us
the exact compaction boundary -- we can snapshot forge state before and after.

### 2.2 What Compaction Preserves and Destroys

From the Anthropic cookbook (automatic context compaction, March 2026):

**Preserved:** Ticket/entity IDs, categories, priorities, routing decisions,
progress status, key patterns, brief outcomes.

**Lost:** Full knowledge base article text, complete drafted responses, detailed
classification reasoning, intermediate tool results.

**Empirical measurements (cookbook):** Without compaction: 208,838 tokens across
37 turns. With compaction (5K threshold): 86,446 tokens across 26 turns with 2
compaction events. 58.6% token reduction.

### 2.3 Knowledge Objects Paper (Zahn & Chana, March 2026)

The paper "Facts as First-Class Objects: Knowledge Objects for Persistent LLM
Memory" (arXiv:2603.17781) provides the most rigorous measurement of compaction
information loss:

- **60% fact loss per compaction pass** (summarization destroys 60% of stored
  facts)
- **54% of project constraints eroded** through cascading compaction
- **Architectural, not model-specific** -- replicated across four frontier models
- Tested Claude Sonnet 4.5 from 10 to 7,000 facts
- Capacity limits at 8,000 facts
- Multi-hop reasoning: 78.9% with Knowledge Objects vs 31.6% with in-context

**Relevance to our experiment:** The 60% fact loss rate is the existing
measurement for unstructured facts. Our forge artifacts are structured with
explicit IDs and refs. The key question is whether structured provenance
metadata survives better than unstructured facts.

### 2.4 ACON Framework (Kang et al., October 2025)

ACON (Agent Context Optimization, arXiv:2510.00615) treats compression as an
optimization problem:

- **Paired trajectory analysis:** Compare full-context vs compressed-context
  runs; use capable LLM to identify what compression lost that caused failure.
- **26-54% memory reduction** while preserving 95%+ task accuracy.
- **Gradient-free:** Works with closed-source models.
- Tested on AppWorld, OfficeBench, and Multi-objective QA.

**Relevance:** ACON's paired trajectory methodology directly applies to our
experimental design -- we can compare forge metric values before/after
compaction using the same paired analysis approach.

### 2.5 Context Drift in Production

Industry data (2025-2026): 65% of enterprise AI failures attributed to context
drift or memory loss during multi-step reasoning -- not raw context exhaustion.
This validates the research importance: context compaction is a real production
failure mode, not a theoretical concern.

---

## 3. Benchmark Selection

### 3.1 Primary Benchmark: Direct API with compact_20260112

**Rationale:** Maximum experimental control. We control the exact trigger
threshold, we can pause at the compaction boundary, we can capture full
before/after state, and we can vary the summarization instructions.

No existing benchmark (SWE-Bench, WebArena, GAIA) provides hooks into the
compaction boundary. They evaluate task completion, not information preservation.
We need to build our own measurement layer on top of the API.

### 3.2 Secondary Benchmark: SWE-Bench Verified Hard (Ecological Validity)

**Selection:** SWE-Bench Verified Hard subset (45 tasks taking >1 hour for
professional engineers).

**Why SWE-Bench Verified Hard, not other variants:**

| Benchmark | Tasks | Avg Files | Duration | Compaction? | Verdict |
|-----------|-------|-----------|----------|-------------|---------|
| SWE-Bench Lite | 300 | 1-2 | <15 min | Unlikely | Too short |
| SWE-Bench Verified (easy) | 196 | 1-2 | <15 min | Unlikely | Too short |
| SWE-Bench Verified (hard) | 45 | 3+ | >1 hr | Likely | **Selected** |
| SWE-Bench Pro | 1,865 | 4.1 avg | Hours-days | Very likely | Too expensive for N=30 |
| WebArena | 812 | N/A | Web tasks | Possible | Wrong domain |
| GAIA Level 3 | ~60 | N/A | Multi-tool | Possible | Wrong domain |
| AgentBench | Varies | N/A | Multi-turn | Possible | Too heterogeneous |
| TAU-bench | Varies | N/A | Transactional | Possible | Wrong domain |

**SWE-Bench Pro note:** 3.73M tokens per problem on average, ~98 turns. Would
definitely trigger compaction (multiple times) but at significant cost. Reserve
for follow-up if Track B results are promising.

**Why not WebArena/GAIA:** Our forge tools are designed for coding/patching
workflows (the OpenClaw domain). SWE-Bench tasks exercise the same propose ->
validate -> fail -> retry loop that our task corpus targets. Web browsing and
multi-tool tasks are a different domain that would require new forge adapters.

### 3.3 Rejected Alternatives

- **Claude Code session transcripts:** Cannot control compaction timing, cannot
  pause at boundary, cannot reproduce. Good for post-hoc analysis but not for
  controlled experiments.
- **OpenClaw VM execution:** v1.0 found the queue worker layer has no LLM
  compaction. The inner execution layer is uncharacterized. Too many unknowns.
- **Custom synthetic tasks only:** Would not satisfy the "real agent task"
  requirement and would be a forbidden proxy (fp-short-tasks).

---

## 4. Task Corpus Design

### 4.1 Track A Tasks (API-Controlled, N=60)

Track A uses the `compact_20260112` API directly. We construct conversations
that contain forge artifacts embedded in the message history, force compaction,
and measure what survives.

**Task structure:** Each trial follows this pattern:

```
Phase 1 (Pre-compaction): Build up context with forge-instrumented
  multi-step coding work until near the trigger threshold.
Phase 2 (Compaction): API triggers compaction; we capture
  before/after snapshots via pause_after_compaction.
Phase 3 (Post-compaction): Continue the task; measure whether
  forge refs in the summary are still resolvable.
```

**Task categories (20 trials each):**

**A1. Coding with embedded provenance (N=20):**
Multi-file refactoring tasks where each step produces a forge artifact with
source_refs pointing to previous steps. Forge artifact IDs and refs are
embedded in tool_use results and assistant messages. After compaction, measure
which artifact IDs survive in the summary.

**A2. Debugging chains (N=20):**
Bug-fix tasks with hypothesis -> test -> fail -> revise chains. Each
hypothesis is a forge artifact. The chain depth (5-8 steps) ensures
rich provenance. After compaction, measure whether the chain structure
(which hypothesis led to which fix) is recoverable from the summary.

**A3. Specification compliance (N=20):**
Tasks where the context includes a specification document with numbered
requirements. Each requirement maps to a forge artifact. Implementation
produces child artifacts linked to requirements via source_refs. After
compaction, measure how many requirement->implementation links survive.

**Token budget per trial:** Set trigger threshold to 80,000 tokens (well below
the 200K window, ensuring compaction fires reliably after ~60-80K of real work).

**Expected duration per trial:** 15-30 minutes of API time.

### 4.2 Track B Tasks (SWE-Bench, N=30)

Use 30 tasks from SWE-Bench Verified Hard. Run each task through a
forge-instrumented coding agent that:

1. Reads the issue description and repository context
2. Plans a solution (forge artifact: plan)
3. Implements changes across files (forge artifacts: per-file patches)
4. Runs tests (forge artifact: test results)
5. Iterates on failures (forge artifacts: revision chain)

The agent uses Claude Sonnet 4.6 with `compact_20260112` enabled at the default
150K threshold. Natural compaction events during long runs provide ecological
validity.

**Task selection criteria:**
- Must involve 3+ files (ensures non-trivial provenance depth)
- Must have test suite (enables automated success verification)
- Must be from Python repositories (our forge tools are Python)
- Prefer tasks with known multi-step solutions (more provenance depth)

**Expected compaction events per task:** 1-3 (based on SWE-Bench Pro data
showing 3.73M tokens per problem).

### 4.3 Track C Tasks (Ablation, N=90)

Reuse Track A task templates with systematic variation of:

| Variable | Levels | Trials per level |
|----------|--------|------------------|
| Summarization instructions | Default, provenance-aware, minimal | 30 each |
| Trigger threshold | 50K, 80K, 120K | 30 each |
| Model | Sonnet 4.6, Opus 4.6 | 45 each |

**Provenance-aware instructions (the key ablation):**
```
Preserve all artifact IDs (strings matching "artifact:*:r*"), all source_ref
links between artifacts, and all absence state labels. These are provenance
metadata that must survive summarization intact. Also preserve task state,
next steps, and key decisions.
```

**Hypothesis:** Provenance-aware instructions will significantly improve
structural reachability post-compaction compared to default instructions.

---

## 5. Instrumentation Plan

### 5.1 The Compaction Boundary Instrument

The core measurement instrument captures exact state before and after each
compaction event.

```python
# compaction_instrument.py -- Pseudocode for the boundary instrument

class CompactionBoundaryInstrument:
    """Captures forge state at the exact compaction boundary."""

    def __init__(self, forge_chamber, trigger_threshold=80_000):
        self.chamber = forge_chamber
        self.threshold = trigger_threshold
        self.snapshots = []  # List of (pre, post, summary_text) tuples

    def run_trial(self, task_messages, tools):
        """Execute a task with compaction instrumentation."""
        client = anthropic.Anthropic()
        messages = list(task_messages)

        while not task_complete(messages):
            response = client.beta.messages.create(
                betas=["compact-2026-01-12"],
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=messages,
                tools=tools,
                context_management={
                    "edits": [{
                        "type": "compact_20260112",
                        "trigger": {
                            "type": "input_tokens",
                            "value": self.threshold
                        },
                        "pause_after_compaction": True,
                    }]
                },
            )

            if response.stop_reason == "compaction":
                # COMPACTION BOUNDARY -- take snapshots
                pre_snapshot = CompactionSnapshot.from_chamber(self.chamber)

                # Extract the summary text from the compaction block
                summary_text = self._extract_summary(response.content)

                # Parse the summary for surviving artifact IDs
                surviving_ids = self._extract_artifact_ids(summary_text)

                # Build post-compaction chamber state
                post_chamber = self._simulate_summary_state(
                    self.chamber, surviving_ids, summary_text
                )
                post_snapshot = CompactionSnapshot.from_chamber(post_chamber)

                self.snapshots.append((pre_snapshot, post_snapshot, summary_text))

                # Continue the conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
            else:
                # Normal response -- process tool use, update forge chamber
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                self._process_tool_results(response, messages)

        return self.snapshots

    def _extract_summary(self, content_blocks):
        """Extract summary text from compaction block."""
        for block in content_blocks:
            if hasattr(block, 'type') and block.type == 'compaction':
                return block.content
        return ""

    def _extract_artifact_ids(self, summary_text):
        """Find all forge artifact IDs preserved in the summary."""
        import re
        pattern = r'artifact:[a-zA-Z0-9_:.-]+:r\d+'
        return set(re.findall(pattern, summary_text))
```

### 5.2 Metrics Collection Pipeline

For each compaction event, collect:

```python
# Per-compaction-event metrics
{
    # Identity
    "trial_id": "A1-007",
    "compaction_index": 0,  # 0th compaction in this trial
    "track": "A",
    "task_category": "A1",

    # Token counts
    "pre_compaction_tokens": 82341,
    "post_compaction_tokens": 8921,
    "compression_ratio": 9.23,

    # Forge chamber state
    "pre_artifact_count": 12,
    "post_artifact_count_surviving": 7,
    "pre_ref_count": 18,
    "post_ref_count_resolved": 11,
    "post_ref_count_degraded": 3,
    "post_ref_count_broken": 4,

    # Reachability metrics (from compaction_harness.py)
    "pre_structural_reachability": 1.0,
    "post_structural_reachability": 0.778,
    "pre_semantic_fidelity": 1.0,
    "post_semantic_fidelity": 0.611,
    "pre_bfs_reachability": 1.0,
    "post_bfs_reachability": 0.857,

    # Content fidelity (new metric for genuine compaction)
    "artifact_id_survival_rate": 0.583,  # fraction of IDs found in summary
    "ref_mention_survival_rate": 0.444,  # fraction of ref links mentioned
    "state_label_survival_rate": 0.667,  # fraction of absence states preserved

    # Embedding similarity
    "cosine_similarity_pre_post": 0.847,  # embedding of pre vs post summary

    # Summary analysis
    "summary_length_tokens": 1247,
    "summary_contains_artifact_ids": true,
    "summary_contains_source_refs": false,
    "summary_contains_state_labels": true,

    # Task outcome
    "task_completed_post_compaction": true,
    "task_correctness_post_compaction": 0.85,
}
```

### 5.3 Three-Tier Ref Classification (Extended for Genuine Compaction)

The existing `classify_refs()` in `compaction_harness.py` already supports three
tiers. For genuine compaction, the "degraded" tier becomes populated:

| Tier | Simulated (v1.0) | Genuine (Phase 2.1) |
|------|------------------|---------------------|
| **Resolved** | Artifact exists, hash matches | Artifact ID in summary, content semantically equivalent |
| **Degraded** | Never occurs (deletion is binary) | Artifact ID in summary but content paraphrased/abbreviated |
| **Broken** | Artifact removed entirely | Artifact ID not in summary, provenance chain broken |

**Detection method for genuine compaction:**
1. **Resolved:** Artifact ID appears in summary text AND content hash of the
   reconstructed artifact matches the pre-compaction hash (exact preservation).
2. **Degraded:** Artifact ID appears in summary text BUT content has been
   modified (paraphrased, abbreviated). Detected by ID regex match + hash
   mismatch. Requires embedding similarity > 0.7 to confirm degraded (not
   broken with coincidental ID mention).
3. **Broken:** Artifact ID does NOT appear in summary text. The provenance
   chain to this artifact is severed.

### 5.4 New Metric: Artifact ID Survival Rate

The signature metric for genuine compaction:

```
artifact_id_survival_rate = |{IDs found in summary}| / |{IDs in pre-compaction state}|
```

This is distinct from structural_reachability (which measures ref graph
connectivity) and semantic_fidelity (which measures content hash preservation).
Artifact ID survival measures whether the compaction model recognizes and
preserves the structured identifiers that make provenance chains work.

### 5.5 Embedding Similarity Measurement

For each compacted artifact, compute cosine similarity between:
- The original artifact content (pre-compaction)
- The portion of the summary that mentions or describes that artifact

**Implementation:**
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embedding_similarity(original_content: str, summary_excerpt: str) -> float:
    """Cosine similarity between original artifact and its summary mention."""
    embeddings = model.encode([original_content, summary_excerpt])
    from numpy import dot
    from numpy.linalg import norm
    return float(dot(embeddings[0], embeddings[1]) /
                 (norm(embeddings[0]) * norm(embeddings[1])))
```

**Threshold calibration:**
- > 0.9: Near-exact preservation (resolved)
- 0.7 - 0.9: Paraphrased but semantically intact (degraded)
- < 0.7: Significant information loss (broken or absent)

---

## 6. Metrics Definition

### 6.1 Primary Metrics (Hypothesis Tests)

| Metric | Definition | Range | Hypothesis |
|--------|-----------|-------|------------|
| **structural_reachability** | (resolved + degraded) / total refs | [0, 1] | > 0.5 (above backtracking threshold) |
| **semantic_fidelity** | resolved / total refs | [0, 1] | > 0.3 (meaningful preservation) |
| **artifact_id_survival** | IDs in summary / IDs pre-compaction | [0, 1] | > 0.5 under default instructions |
| **provenance_aware_delta** | survival(custom) - survival(default) | [-1, 1] | > 0.15 (instructions help) |

### 6.2 Secondary Metrics (Characterization)

| Metric | Definition | Purpose |
|--------|-----------|---------|
| **bfs_reachability** | BFS reachable fraction | Comparison with v1.0 baseline |
| **compression_ratio** | pre_tokens / post_tokens | Compaction aggressiveness |
| **summary_length** | Token count of summary | Correlation with survival |
| **embedding_similarity** | Cosine(original, summary) | Content fidelity |
| **task_completion_rate** | Task success after compaction | Ecological impact |
| **degraded_fraction** | degraded / total refs | New tier population |
| **compaction_count** | Compactions per trial | Cascading effects |

### 6.3 Cross-Reference Metrics (v1.0 Comparison)

| Metric | v1.0 Simulated | Phase 2.1 Genuine | Comparison |
|--------|---------------|-------------------|------------|
| structural_reachability | 0.93 (10% del) to 0.25 (90% del) | Measured | Gap analysis |
| semantic_fidelity | = structural_reach (no degraded) | Measured | Degraded tier population |
| bfs_reachability | Always 1.0 | Measured | May differ for genuine |
| backtracking_threshold | 80% deletion | Measured | Where does genuine cross 0.5? |

---

## 7. Statistical Analysis Plan

### 7.1 Sample Sizes and Power

**Track A (N=60, 20 per category):**
- Primary test: One-sample t-test, H0: structural_reachability <= 0.5
- Power calculation: For effect size d=0.5 (medium), alpha=0.05, power=0.80,
  required N=27. We use N=60 for robustness and per-category analysis.
- If structural_reachability is near 0.5 (ambiguous), we can detect a 0.12
  difference from the threshold with N=60.

**Track B (N=30):**
- Primary test: One-sample t-test on structural_reachability
- Power: For d=0.5, alpha=0.05, power=0.80, N=27 needed. N=30 provides margin.
- Secondary: Paired comparison with v1.0 simulated results at comparable
  compression ratios.

**Track C (N=90, 30 per instruction variant):**
- Primary test: One-way ANOVA across instruction variants
- Power: For f=0.3 (medium effect), 3 groups, alpha=0.05, power=0.80,
  required N=36 per group. We use N=30 per group (slight under-power
  acceptable for ablation study; increase to N=40 if results are ambiguous).
- Post-hoc: Tukey HSD for pairwise comparisons.

### 7.2 Confidence Intervals

| Condition | CI Method | Justification |
|-----------|-----------|---------------|
| Boundary values (0.0 or 1.0) | Clopper-Pearson | Exact binomial; matches v1.0 convention |
| Interior values, N >= 10 | Bootstrap (B=10000, seed=42) | Matches v1.0 convention |
| Interior values, N < 10 | Wilson score | Better coverage than Wald for small N |
| Between-group comparisons | Bootstrap permutation | Non-parametric; robust to non-normality |

### 7.3 Pre-Registration

Before running experiments, pre-register:
1. All primary hypotheses and their acceptance criteria
2. The analysis pipeline (no post-hoc metric definitions)
3. The stopping rule: stop at N=60/30/90 unless power < 0.60, then extend

### 7.4 Multiple Comparisons

Track C tests 3 instruction variants x 3 thresholds x 2 models = 18
conditions. Apply Bonferroni correction for the 3 primary comparisons
(instruction variants). Report both corrected and uncorrected p-values.

---

## 8. Experimental Procedures

### 8.1 Track A Procedure (API-Controlled)

```
FOR each trial in A1..A3 (60 total):
  1. Initialize clean forge chamber
  2. Construct task messages with forge artifacts embedded
  3. Set compact_20260112 with trigger=80000, pause_after_compaction=true
  4. Execute task via Messages API loop:
     a. Send messages
     b. IF stop_reason == "compaction":
        i.   Take pre-compaction snapshot (CompactionSnapshot.from_chamber)
        ii.  Extract summary text from compaction block
        iii. Parse summary for surviving artifact IDs (regex)
        iv.  Build post-compaction snapshot
        v.   Compute all metrics (classify_refs, measure_reachability, etc.)
        vi.  Store (pre, post, summary, metrics) tuple
        vii. Append response to messages; continue
     c. IF stop_reason == "end_turn" or "tool_use":
        i.   Process tool results
        ii.  Update forge chamber with new artifacts
        iii. Append to messages; continue
     d. IF task complete or max turns reached: break
  5. Record trial-level metrics (aggregated across compaction events)
  6. Record raw data: full message history, all snapshots, summary texts
```

### 8.2 Track B Procedure (SWE-Bench)

```
FOR each of 30 SWE-Bench Verified Hard tasks:
  1. Set up Docker environment (SWE-bench harness)
  2. Initialize forge chamber for the task
  3. Run forge-instrumented coding agent:
     a. Agent reads issue + repo context
     b. Agent plans, implements, tests (normal agentic loop)
     c. compact_20260112 enabled at 150K threshold
     d. pause_after_compaction=true for boundary capture
  4. At each compaction event:
     a. Capture before/after snapshots
     b. Log all metrics
  5. After task completion:
     a. Evaluate task success (SWE-bench eval harness)
     b. Compute aggregate provenance metrics
     c. Record: task_id, success, compaction_count, all metrics
```

### 8.3 Track C Procedure (Ablation)

```
FOR each ablation condition (9 conditions x 10 trials = 90):
  1. Select task template (cycle through A1..A3 templates)
  2. Configure compaction parameters per ablation condition
  3. Execute using Track A procedure
  4. Record condition-specific metrics
```

---

## 9. Equipment and API Requirements

### 9.1 API Access

| Resource | Specification | Cost Estimate |
|----------|--------------|---------------|
| Anthropic API key | With `compact-2026-01-12` beta access | -- |
| Claude Sonnet 4.6 | Primary model for Tracks A, B, C | ~$0.003/1K input, ~$0.015/1K output |
| Claude Opus 4.6 | Ablation model for Track C subset | ~$0.015/1K input, ~$0.075/1K output |

**Cost estimate per track:**
- Track A: 60 trials x ~80K tokens x $0.003/1K = ~$14 input + output overhead ~$150 total
- Track B: 30 trials x ~500K tokens avg = ~$300 total
- Track C: 90 trials x ~80K tokens = ~$200 total + Opus ablation ~$150
- **Total: ~$800 (conservative), ~$1,200 (with retries and overhead)**

### 9.2 Software Dependencies

```
# Python packages
anthropic>=0.52.0          # compact_20260112 beta support
sentence-transformers      # Embedding similarity (all-MiniLM-L6-v2)
numpy                      # Vector operations
scipy                      # Statistical tests (t-test, ANOVA)
statsmodels                # Power analysis, multiple comparisons
swebench>=2.0              # SWE-bench harness (Track B only)
docker                     # SWE-bench Docker environments
tiktoken                   # Token counting validation

# System requirements
Docker Desktop             # 8+ CPUs, 16GB RAM, 120GB disk (SWE-bench)
Python 3.11+               # Matching primordial project requirement
```

### 9.3 Existing Tools to Extend

| Tool | Location | Extension Needed |
|------|----------|-----------------|
| `compaction_harness.py` | `tools/compaction_harness.py` | Add genuine compaction mode (API calls) |
| `CompactionSnapshot` | `tools/compaction_harness.py` | No change -- already supports genuine |
| `classify_refs()` | `tools/compaction_harness.py` | Add summary-text-based classification |
| `measure_reachability()` | `tools/compaction_harness.py` | No change -- works on snapshots |
| `openclaw_adapter.py` | `tools/openclaw_adapter.py` | Extend for API message history parsing |
| `forge_chamber.py` | `tools/forge_chamber.py` | No change -- chamber model is generic |
| `forge_nulls.py` | `tools/forge_nulls.py` | No change -- absence states unchanged |

### 9.4 New Tools to Build

| Tool | Purpose | Estimated Size |
|------|---------|---------------|
| `compaction_instrument.py` | API-level compaction boundary capture | ~300 lines |
| `genuine_compaction_runner.py` | Orchestrates Track A/B/C experiments | ~400 lines |
| `summary_parser.py` | Extracts artifact IDs, refs, states from summary text | ~150 lines |
| `embedding_similarity.py` | Cosine similarity for content fidelity | ~80 lines |
| `swebench_forge_agent.py` | Forge-instrumented SWE-bench coding agent | ~500 lines |
| `compaction_analysis.py` | Statistical analysis and reporting | ~300 lines |

---

## 10. Expected Outcomes

### 10.1 What Would Each Outcome Prove or Disprove?

**Outcome 1: structural_reachability > 0.5 under default instructions**
- **Proves:** Forge provenance chains survive genuine LLM compaction at a
  practically useful level. The compaction model preserves enough structural
  information for provenance chains to remain navigable.
- **Implies:** RQ3b receives a positive answer. The v1.0 simulated results
  (lower bound) were conservative, and real compaction performs better.
- **Action:** Proceed to paper writing with genuine compaction data.

**Outcome 2: structural_reachability <= 0.5 under default, > 0.5 with provenance-aware instructions**
- **Proves:** Forge provenance chains are fragile under naive compaction but
  can be rescued by provenance-aware summarization. The mechanism matters.
- **Implies:** RQ3b is conditionally positive -- provenance survives IF the
  compaction strategy is provenance-aware. This is a publishable finding with
  practical implications (custom compaction instructions as a mitigation).
- **Action:** Proceed to paper with both negative (default) and positive
  (provenance-aware) results. Develop a "provenance-preserving compaction
  prompt" as a practical artifact.

**Outcome 3: structural_reachability <= 0.5 under all conditions**
- **Proves:** Genuine LLM compaction is fundamentally destructive to
  structural provenance. The 60% fact loss from Knowledge Objects applies
  equally to structured metadata.
- **Implies:** RQ3b receives a negative answer. The approach of embedding
  provenance in the context window is insufficient. Alternative architectures
  needed (Knowledge Objects, external stores, or forge's own
  `pruned_recoverable` with external artifact store).
- **Action:** This is a significant negative finding. Write it up honestly.
  Pivot to external provenance storage (forge artifacts in a sidecar DB, not
  in the context window). This would be the forge equivalent of Knowledge
  Objects.

**Outcome 4: artifact_id_survival > structural_reachability**
- **Proves:** The compaction model preserves individual IDs but not the
  relationships between them (the refs). IDs survive as isolated mentions;
  the DAG structure is lost.
- **Implies:** Partial provenance survival -- you can know WHAT existed but
  not HOW things are connected. This is the "degraded" tier in action.
- **Action:** Investigate whether ref-preserving instructions can close the
  gap between ID survival and structural reachability.

### 10.2 Anchor Comparisons

| Metric | MockLM Ceiling | v1.0 Simulated (50% del) | Phase 2.1 Target |
|--------|---------------|-------------------------|-----------------|
| structural_reachability | 1.0 | 0.821 | > 0.5 |
| semantic_fidelity | 1.0 | 0.821 | > 0.3 |
| degraded_fraction | 0.0 | 0.0 | > 0 (first population) |
| bfs_reachability | 1.0 | 1.0 | Measured |
| artifact_id_survival | 1.0 | N/A (new metric) | > 0.5 |

### 10.3 Backtracking Threshold Assessment

If structural_reachability < 0.5 across all Track A conditions AND Track C
provenance-aware instructions do not lift it above 0.5:

**Backtracking is triggered for RQ3b.** The conclusion would be that in-context
provenance is insufficient for genuine compaction survival, and external
provenance storage is required. This is not a project failure -- it is a
meaningful finding that redirects the architecture.

---

## 11. Integration Approaches

### 11.1 Live Instrumentation (Primary for Track A/C)

The `pause_after_compaction` API parameter enables live instrumentation:

1. Client detects `stop_reason == "compaction"`
2. Client captures full message history (pre-compaction state)
3. Client parses compaction block for summary text
4. Client continues conversation (post-compaction state)
5. Both states are captured in real-time -- no reconstruction needed

**Pros:** Exact boundary capture. No ambiguity about what was in context.
**Cons:** Requires API-level integration (not applicable to opaque runtimes).

### 11.2 Post-Hoc JSONL Analysis (Primary for Track B)

For SWE-Bench runs where we cannot pause at the compaction boundary:

1. Log all API requests and responses to JSONL (including compaction blocks)
2. After the run, parse the JSONL to identify compaction events
3. Reconstruct pre/post state from the message history at each compaction point
4. Apply the same metrics pipeline as live instrumentation

**Pros:** Non-invasive. Works with any agent that logs API calls.
**Cons:** Message history reconstruction may miss some state. Cannot modify
post-compaction behavior.

**Detection of compaction events in JSONL:**
```python
def detect_compaction_events(jsonl_path):
    """Find compaction events in API response logs."""
    events = []
    for line in open(jsonl_path):
        response = json.loads(line)
        for block in response.get("content", []):
            if block.get("type") == "compaction":
                events.append({
                    "timestamp": response["timestamp"],
                    "summary": block["content"],
                    "pre_message_count": response["pre_message_count"],
                    "post_message_count": response["post_message_count"],
                })
    return events
```

### 11.3 Comparison of Approaches

| Dimension | Live Instrumentation | Post-Hoc JSONL |
|-----------|---------------------|----------------|
| Boundary precision | Exact | Reconstructed |
| State capture | Complete | May miss tool state |
| Runtime overhead | pause_after_compaction adds latency | Zero overhead |
| Applicable to | Track A, C | Track B |
| Reproducibility | Full (deterministic pause) | Depends on log completeness |
| Can modify post-compaction | Yes (inject additional context) | No |

---

## 12. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| compact_20260112 beta changes mid-experiment | Medium | High | Pin SDK version; complete all trials in one batch |
| SWE-bench tasks too short for compaction | Low | Medium | Pre-screen: only use Verified Hard (>1hr); raise threshold if needed |
| API rate limits slow Track B | Medium | Low | Batch overnight; use max_workers=4 for Docker |
| Compaction model changes behavior | Low | High | Record model version in every trial; re-run sample if change detected |
| Artifact IDs too synthetic for summary to preserve | Medium | Medium | Track C ablation with provenance-aware instructions addresses this |
| Cost exceeds budget | Low | Medium | Start with Track A (cheapest); proceed to B/C only if A is informative |
| Non-normal distributions | Medium | Low | Use bootstrap CIs (already standard); add Wilcoxon as non-parametric backup |

---

## 13. Timeline

| Week | Activity | Deliverables |
|------|----------|-------------|
| 1 | Build `compaction_instrument.py`, `summary_parser.py`, `embedding_similarity.py` | New tools, unit tests |
| 2 | Build `genuine_compaction_runner.py`; design Track A task templates | Runner + 3 task templates |
| 3 | Execute Track A (N=60) | Raw data JSONL, per-trial metrics |
| 4 | Build `swebench_forge_agent.py`; execute Track B (N=30) | SWE-bench results + forge metrics |
| 5 | Execute Track C ablation (N=90) | Ablation results |
| 6 | Statistical analysis, report writing | `genuine-compaction-report.md` |

**Total: 6 weeks from approval to final report.**

---

## 14. Forbidden Proxy Audit

| Forbidden Proxy | Status | Evidence |
|-----------------|--------|---------|
| fp-short-tasks | ADDRESSED | Track A uses 80K token threshold; Track B uses SWE-Bench Verified Hard (>1hr tasks) |
| fp-shallow-traces | ADDRESSED | Task templates require provenance depth >= 5; SWE-Bench tasks have multi-step solutions |
| fp-mockml-tasks | ADDRESSED | All tracks use real Claude API with genuine compaction |
| fp-simulated-compaction | ADDRESSED | This IS the genuine compaction experiment that v1.0 deferred |
| fp-synthetic-faults | ADDRESSED | No fault injection; measuring natural compaction behavior |

---

## 15. Reproducibility Contract

All experiments will produce:

1. **Raw data:** JSONL files with complete API request/response logs
2. **Snapshots:** Pre/post CompactionSnapshot JSON for every compaction event
3. **Summary texts:** Full text of every compaction summary
4. **Metrics:** Per-trial and aggregated metrics in JSON format
5. **Analysis scripts:** Complete statistical analysis pipeline
6. **Random seeds:** Seed=42 for all randomized operations
7. **SDK version:** Pinned `anthropic` package version
8. **Model versions:** Recorded in every trial metadata
9. **SWE-bench versions:** Pinned `swebench` package version and task IDs

---

## Appendix A: Compaction API Reference Summary

**Beta header:** `compact-2026-01-12`

**Configuration:**
```json
{
    "context_management": {
        "edits": [{
            "type": "compact_20260112",
            "trigger": {"type": "input_tokens", "value": 80000},
            "pause_after_compaction": true,
            "instructions": "optional custom summarization prompt"
        }]
    }
}
```

**Compaction block in response:**
```json
{
    "type": "compaction",
    "content": "<summary>...</summary>"
}
```

**Stop reason:** `"compaction"` when `pause_after_compaction` is true.

**Models:** `claude-opus-4-6`, `claude-sonnet-4-6`.

**Minimum trigger:** 50,000 tokens. Default: 150,000 tokens.

---

## Appendix B: Related Work Reference Table

| Work | Key Finding | Relevance |
|------|------------|-----------|
| Knowledge Objects (Zahn & Chana, 2026) | 60% fact loss per compaction; 54% constraint erosion | Baseline for expected information loss |
| ACON (Kang et al., 2025) | 26-54% memory reduction, 95%+ accuracy preserved | Methodology for paired trajectory analysis |
| LLMLingua (Microsoft) | 20x compression with 1.5% performance loss | Comparison: extractive vs abstractive |
| SWE-Bench Verified | 500 tasks, 45 hard (>1hr) | Task source for Track B |
| SWE-Bench Pro | 1,865 tasks, 3.73M tokens avg, 98 turns | Context pressure validation |
| Claude compact_20260112 API | Server-side compaction with pause hooks | Core experimental infrastructure |

---

_Protocol drafted: 2026-03-27_
_Based on: v1.0 Phase 4 results (simulated compaction) + web research on benchmarks, compaction mechanisms, and measurement methods_
