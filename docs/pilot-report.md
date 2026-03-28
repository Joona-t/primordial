# Pilot Track A Report

**Date:** 2026-03-28
**Mode:** dry-run
**Trials:** 6/6
**Trials with LLM compaction events:** 6

> **NOTE:** This report is based on dry-run data (synthetic LLM compaction).
> Dry-run validates pipeline logic but NOT genuine LLM behavior.
> Live API trials required before making go/no-go decision.
> See forbidden proxy fp-dry-run-only in Plan 03 contract.

## Go/No-Go Recommendation: **BLOCKED**

**Reason:** Dry-run only — live API required for go/no-go decision

| Criterion | Status |
|-----------|--------|
| pipeline_valid | PASS |
| compaction_fires | PASS |
| metrics_measurable | PASS |
| live_mode | FAIL |

## Global Statistics (pilot N=6)

| Metric | Mean | Min | Max | Range | N |
|--------|------|-----|-----|-------|---|
| artifact_id_survival | 0.25 | 0.25 | 0.25 | 0.0 | 6 |
| structural_reachability | 0.25 | 0.25 | 0.25 | 0.0 | 6 |
| degraded_fraction | 0.25 | 0.25 | 0.25 | 0.0 | 6 |
| compression_ratio | 214.55 | 214.55 | 214.55 | 0.0 | 6 |
| semantic_fidelity | 0.0161 | 0.0161 | 0.0161 | 0.0 | 6 |

## Per-Category Breakdown

### Coding

| Metric | Mean | Min | Max |
|--------|------|-----|-----|
| artifact_id_survival | 0.25 | 0.25 | 0.25 |
| structural_reachability | 0.25 | 0.25 | 0.25 |
| degraded_fraction | 0.25 | 0.25 | 0.25 |
| compression_ratio | 214.55 | 214.55 | 214.55 |
| semantic_fidelity | 0.0161 | 0.0161 | 0.0161 |

### Debugging

| Metric | Mean | Min | Max |
|--------|------|-----|-----|
| artifact_id_survival | 0.25 | 0.25 | 0.25 |
| structural_reachability | 0.25 | 0.25 | 0.25 |
| degraded_fraction | 0.25 | 0.25 | 0.25 |
| compression_ratio | 214.55 | 214.55 | 214.55 |
| semantic_fidelity | 0.0161 | 0.0161 | 0.0161 |

### Specification

| Metric | Mean | Min | Max |
|--------|------|-----|-----|
| artifact_id_survival | 0.25 | 0.25 | 0.25 |
| structural_reachability | 0.25 | 0.25 | 0.25 |
| degraded_fraction | 0.25 | 0.25 | 0.25 |
| compression_ratio | 214.55 | 214.55 | 214.55 |
| semantic_fidelity | 0.0161 | 0.0161 | 0.0161 |

## Provenance-Aware Delta

| Category | Survival Delta | Aware | Unaware | Reachability Delta |
|----------|---------------|-------|---------|-------------------|
| coding | +0.0000 | 0.25 | 0.25 | +0.0000 |
| debugging | +0.0000 | 0.25 | 0.25 | +0.0000 |
| specification | +0.0000 | 0.25 | 0.25 | +0.0000 |

**Interpretation:** Positive delta means provenance-aware instructions help.
Note: N=1 per cell — no statistical significance on pilot data.

## Anchor Comparisons

### 1. MockLM Ceiling (controlled condition)

- MockLM ceiling: survival=1.0, reachability=1.0
- Pilot mean survival: 0.25
- Pilot mean reachability: 0.25
- Delta from ceiling (survival): -0.75
- Delta from ceiling (reachability): -0.75
- **Expected:** Genuine < MockLM (real LLM compaction is lossy)

### 2. Knowledge Objects (Zahn & Chana, March 2026)

- Knowledge Objects: 60% fact loss per LLM compression pass
- Expected unstructured survival: 0.4 (40%)
- Pilot mean artifact_id_survival: 0.25
- Comparison: worse_or_equal
- **If survival > 0.4:** Structured provenance survives better than unstructured facts

### 3. v1.0 Simulated Compaction

- v1.0 at 50% random deletion: reachability = 0.82
- Pilot mean reachability: 0.25
- Note: Comparison requires matching compression ratio from pilot to simulated deletion percentage

## Tier Distribution

| Tier | Count | Fraction |
|------|-------|----------|
| resolved | 0 | 0.0000 |
| degraded | 30 | 0.2500 |
| broken | 90 | 0.7500 |

**Note:** First-ever population of degraded tier under LLM compaction.
v1.0 simulated compaction produced zero degraded refs (all resolved or broken).

## Variance Estimate (pilot N=6)

- artifact_id_survival range: 0.0
- structural_reachability range: 0.0
- **Note:** N=6 is insufficient for variance estimation.
  Pilot serves to detect gross failures, not estimate population parameters.

## Limitations

1. **N=6 is not statistical:** No p-values, no confidence intervals, no hypothesis tests.
2. **Pilot validates pipeline, not hypothesis:** Full Track A (N=60) needed for statistical claims.
3. **DRY-RUN ONLY:** All data is synthetic. Live API calls required for genuine measurements.
   Forbidden proxy fp-dry-run-only is TRIGGERED. claim-pipeline-valid is BLOCKED.
