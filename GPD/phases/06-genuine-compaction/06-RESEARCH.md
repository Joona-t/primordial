# Phase 6 Research: Genuine Compaction Experiments

## Status: RESEARCH COMPLETE — ready for /gpd:plan-phase

## Phase Goal

Test whether Primordial's provenance chains survive genuine LLM context-window compaction (not simulated deletion). Establish Semantic Provenance Fidelity (SPF) metric.

## Research Questions

- **RQ3b:** Does structural reachability hold under genuine LLM context-window compaction?
- **SPF-01:** Can semantic fidelity of recovered artifacts be measured via embeddings?

## v1.0 Baseline to Beat

- Simulated compaction: structural reachability 0.93 (10% deletion) → 0.25 (90% deletion)
- Backtracking threshold at 80% deletion
- MockLM ceiling: 100% provenance reachability
- Genuine compaction: UNTESTED (the gap)

## Key Literature

- **Knowledge Objects (Zahn & Chana, March 2026):** 60% fact loss per LLM compression pass
- **MemGPT/Letta:** Paging mechanism but no provenance semantics
- **ACON (2025):** 26-54% compression, destroys provenance
- **LLMLingua (2023):** Token-level compression, not structure-aware

## Experimental Protocol

**Full protocol:** `docs/phase-2.1-genuine-compaction-protocol.md` (924 lines)

### Key Discovery: `compact_20260112` API

Anthropic's compaction API provides `pause_after_compaction: true` which returns `stop_reason: "compaction"` with full boundary capture. This enables controlled genuine compaction experiments with exact before/after observability. Min trigger: 50K tokens, default 150K.

### 3-Track Design (180 trials, ~$800-1200)

**Track A (N=60):** API-controlled using `compact_20260112` with `pause_after_compaction: true`. Three task categories. Trigger at 80K tokens.

**Track B (N=30):** SWE-Bench Verified Hard (45 tasks, >1hr for professionals, avg 3.73M tokens/98 turns). Natural compaction at 150K threshold. Ecological validity.

**Track C (N=90):** Ablation — varying summarization instructions (default vs provenance-aware vs minimal), trigger thresholds (50K/80K/120K), and models (Sonnet vs Opus).

**Key hypothesis:** Provenance-aware custom instructions ("Preserve all artifact IDs matching artifact:*:r*") will significantly improve structural reachability.

### New Metrics Beyond v1.0

- `artifact_id_survival_rate`: fraction of forge IDs found in summary text
- `SPF_embedding`: cosine similarity via sentence-transformers
- Population of "degraded" ref tier (empty under simulated deletion, populated under genuine compaction)

### Timeline: 6 weeks from approval

## Risks

- SWE-Bench tasks may not be long enough to trigger compaction on modern 200K context windows
- Genuine compaction may be opaque (no access to before/after snapshots)
- API costs for 50+ long-running agent sessions

## Dependencies

- Agent framework with observable compaction (Claude Code, ChatGPT, or custom harness)
- Embedding model for SPF metric (text-embedding-3-large or similar)
- Compute budget for 200+ agent runs
