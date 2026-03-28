# Genuine LLM Compaction Report -- RQ3b Assessment

**Generated:** 2026-03-28T05:01:19.501299+00:00
**Data mode:** dry-run
**Total trials:** 6
**Track A:** 6 | **Track B:** 0 | **Track C:** 0

## 1. Executive Summary

> **NOTE: All data is DRY-RUN (synthetic compaction).** Results validate the analysis pipeline but do NOT measure genuine LLM context-window compaction. All metrics below are from deterministic synthetic compaction (midpoint-split). Live API execution (ANTHROPIC_API_KEY) is required for genuine measurement.

**RQ3b Verdict: PARTIAL**

- Data is dry-run (synthetic), not genuine LLM compaction
- Pipeline validated: 6 trials processed
- Metrics computed: reachability=0.2500
- Forbidden proxy fp-simulated-only is VIOLATED: analysis on dry-run data only

*Criteria:* PARTIAL because data_mode='dry-run' -- genuine LLM compaction data required for PASS/FAIL
*Sample size caveat:* N=6 (all dry-run; live API data required)
*Confidence:* [LOW]

## 2. Track A Results (Pilot)

### 2.1 Aggregate Metrics

| Metric | Mean | Std | 95% CI | N | CI Method |
|--------|------|-----|--------|---|-----------|
| structural_reachability | 0.25 | 0.0 | [0.25, 0.25] | 6 | bootstrap_small_n |
| artifact_id_survival | 0.25 | 0.0 | [0.25, 0.25] | 6 | bootstrap_small_n |
| semantic_fidelity | 0.0161 | 0.0 | [0.0161, 0.0161] | 6 | bootstrap_small_n |
| degraded_fraction | 0.25 | 0.0 | [0.25, 0.25] | 6 | bootstrap_small_n |
| compression_ratio | 214.55 | 0.0 | [214.55, 214.55] | 6 | bootstrap_small_n |

### 2.2 Per-Category Breakdown

| Category | structural_reachability | artifact_id_survival | semantic_fidelity | degraded_fraction | compression_ratio |
|----------|----------------------|---------------------|-------------------|-------------------|-------------------|
| coding | 0.25 | 0.25 | 0.0161 | 0.25 | 214.55 |
| debugging | 0.25 | 0.25 | 0.0161 | 0.25 | 214.55 |
| specification | 0.25 | 0.25 | 0.0161 | 0.25 | 214.55 |

### 2.3 Provenance-Aware Delta

| Category | Aware Survival | Default Survival | Delta |
|----------|---------------|-----------------|-------|
| coding | 0.25 | 0.25 | 0.0 |
| debugging | 0.25 | 0.25 | 0.0 |
| specification | 0.25 | 0.25 | 0.0 |

## 3. Hypothesis Tests

### 3.1 one_sample_t_test_structural_reachability

- **H0:** structural_reachability <= 0.5
- **H1:** structural_reachability > 0.5
- **Statistic:** -inf
- **p-value:** 1.0
- **Effect size d:** -inf
- **Mean:** 0.25
- **95% CI:** [0.25, 0.25]
- **N:** 6
- **Reject H0:** False
- **Interpretation:** Fail to reject H0: insufficient evidence that structural_reachability > 0.5 (t=-inf, p=1.000000, d=-inf, N=6)

### 3.2 one_sample_t_test_artifact_id_survival

- **H0:** artifact_id_survival <= 0.5
- **H1:** artifact_id_survival > 0.5
- **Statistic:** -inf
- **p-value:** 1.0
- **Effect size d:** -inf
- **Mean:** 0.25
- **95% CI:** [0.25, 0.25]
- **N:** 6
- **Reject H0:** False
- **Interpretation:** Fail to reject H0: insufficient evidence that artifact_id_survival > 0.5 (t=-inf, p=1.000000, d=-inf, N=6)

### 3.3 instruction_delta_artifact_id_survival

- **H0:** delta(artifact_id_survival) <= 0
- **H1:** delta(artifact_id_survival) > 0
- **Statistic:** 4.5
- **p-value:** 1.0
- **p-value (Bonferroni):** 1.0
- **Effect size d:** 0.0
- **Mean:** 0.0
- **95% CI:** [0.0, 0.0]
- **N:** 3
- **Reject H0:** False
- **Interpretation:** Fail to reject H0: no significant improvement from provenance-aware instructions on artifact_id_survival (delta=0.0000, p_raw=1.000000, p_corrected=1.000000, d=0.000, test=mann_whitney_u, N=3)

## 4. Track C Ablation Results

**No Track C data available.** Track C ablation framework (Plan 04) 
is built and ready for execution. Live API data required.

## 5. Anchor Comparisons

| Metric | MockLM Ceiling | Knowledge Objects | v1.0 Simulated (50% del) | Phase 6 Genuine |
|--------|---------------|-------------------|--------------------------|-----------------|
| structural_reachability | 1.0 | N/A | 0.8214285714285715 | 0.25 |
| artifact_id_survival | 1.0 | 0.4 (inferred) | N/A | 0.25 |
| semantic_fidelity | 1.0 | N/A | N/A | 0.0161 |
| degraded_fraction | 0.0 | N/A | 0.0 (always) | 0.25 |

### 5.1 MockLM Ceiling

- Gap (reachability): 0.75
- Gap (survival): 0.75
- Interpretation: Genuine reachability is 75.0% below MockLM ceiling. Genuine survival is 75.0% below MockLM ceiling. Expected direction: genuine < ceiling.

### 5.2 Knowledge Objects (Zahn & Chana, March 2026)

- Expected unstructured survival: 0.4
- Genuine survival: 0.25
- Delta from KO: -0.15
- Structured beats unstructured: False
- Interpretation: Artifact ID survival (0.250) is AT OR BELOW the Knowledge Objects baseline (0.4). Structured provenance does NOT demonstrably outperform unstructured facts.

### 5.3 v1.0 Simulated Compaction

- v1.0 at 50% deletion: 0.8214285714285715
- v1.0 at 80% deletion: 0.4375
- v1.0 backtracking crossing: 0.8
- Genuine reachability: 0.25
- Gap (genuine vs v1.0 50%): -0.571429
- Interpretation: Genuine reachability (0.250) vs v1.0 simulated at 50% deletion (0.821): delta = -0.571. Genuine compaction is worse than or equal to simulated deletion. Note: comparison requires matching compression ratios for fair assessment.

**Overall anchor verdict:** fail

## 6. Three-Tier Ref Classification

| Tier | Count | Fraction |
|------|-------|----------|
| Resolved | 0 | 0.0 |
| Degraded | 30 | 0.25 |
| Broken | 90 | 0.75 |
| **Total refs** | 120 | |

**Key finding:** The degraded tier is populated for the first time. v1.0 simulated compaction (programmatic deletion) always produced degraded_count=0 because deletion removes artifacts entirely (broken) rather than summarizing them (degraded). Genuine LLM compaction can produce degraded refs where content is paraphrased but the artifact ID survives.

## 7. RQ3b Verdict

**Verdict: PARTIAL**

**Criteria:** PARTIAL because data_mode='dry-run' -- genuine LLM compaction data required for PASS/FAIL
**Confidence:** [LOW]
**Sample size:** N=6 (all dry-run; live API data required)

**Instruction Effect Verdict: PARTIAL**

- Data is dry-run: synthetic compaction ignores instructions
- Delta = 0.0000 (expected 0 in dry-run)
- Live API data required to test instruction effect

## 8. Forbidden Proxy Audit

| Proxy ID | Status | Evidence |
|----------|--------|----------|
| fp-cherry-picked | **REJECTED** | All conditions reported: tracks=['A'], categories=['coding', 'debugging', 'specification'], provenance_aware=['False', 'True'] |
| fp-simulated-only | **VIOLATED** | All 6 trials are mode='dry-run'. No live API data. |
| fp-short-tasks | **REJECTED** | 6/6 trials triggered compaction events. |

**fp-cherry-picked:** Analysis includes all available conditions. No cherry-picking.

**fp-simulated-only:** This forbidden proxy IS triggered. Dry-run data validates pipeline but does not constitute genuine LLM compaction measurement. Live API execution required via ANTHROPIC_API_KEY.

**fp-short-tasks:** Compaction events are necessary for measurement validity.

## 9. Limitations

1. **Sample size:** Pilot data only (N=6). Insufficient for statistical significance. Full Track A (N=60) required.

2. **Dry-run data:** All data is from synthetic compaction (midpoint-split). This validates the pipeline but does NOT measure genuine LLM compaction. The forbidden proxy fp-simulated-only is VIOLATED.

3. **Track B status:** No Track B data. SWE-Bench Docker setup required.

4. **Threshold calibration:** The 80K token trigger threshold is based on Anthropic API documentation. Actual compaction behavior may vary with model version and API updates.

5. **Model version dependency:** Results are specific to the model version used. Different model versions may produce different compaction behaviors.

## 10. Recommendations

- **Set ANTHROPIC_API_KEY and run live pilot** (`python3 tools/run_pilot_track_a.py`).
- Estimated cost: $12-30 for 6 pilot trials.
- Live pilot data is required before any verdict can be rendered.
- Pipeline is validated and ready for live execution.

---

*Generated by `tools/compaction_analysis.py` | Phase: 06-genuine-compaction, Plan: 05*