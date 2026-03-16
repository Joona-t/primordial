# Side-by-Side Metrics Comparison

Generated programmatically by `tools/synthesis.py` from source data files.
Every value (except MockLM ceiling anchors) loaded from JSON, not manually transcribed.

## Comparison Table

| Observable | MockLM Ceiling | Uninstrumented Floor | Structured Logging | Forge Instrumented | Gap (Ceiling - Forge) | Differential (Forge - Floor) |
| --- | --- | --- | --- | --- | --- | --- |
| Violation detection (D1-D6 types) | 6/6 | 0/6 | 0/6 | 3/6 | 3 types | +3 types |
| Violation detection (all D1-D9) | N/A | 0/9 | 0/9 | 4/9 | N/A | +4 types |
| Aggregate injection detection rate | N/A | 0.0 | 0.0 | 0.4444444444444444 [0.34444444444444444, 0.5444444444444444] | N/A | +0.4444444444444444 |
| Natural violation count | N/A | 0 | 0 | 0 (CP UB: 11.6%) | N/A | 0 |
| False positive rate | N/A | N/A | N/A | 0.0 (CP UB: 11.6%) | N/A | N/A |
| Pre-compaction reachability | 1.0 | 0.0 | N/A | 1.0 | 0.0 | +1.0 |
| Structural reachability @ 50% simulated deletion | N/A | N/A | N/A | 0.8214285714285715 | N/A | N/A |
| Structural reachability @ 80% simulated deletion | N/A | N/A | N/A | 0.4375 | N/A | N/A |
| Backtracking threshold crossed | N/A | N/A | N/A | 80% deletion | N/A | N/A |
| Forge trace compression | 1.096x | N/A | N/A | 1.1959x | 0.0999x | N/A |
| Provenance depth | N/A | 0 | N/A | 21 | N/A | +21 |
| Violation regression post-compaction | N/A | N/A | N/A | 4/4 (100%) | N/A | N/A |

## Gap Analysis (MockLM Ceiling vs Forge Instrumented)

- **Violation detection (D1-D6 types):** 6/6 vs 3/6 (gap=3) [EXPLAINED] -- MockLM catches D3/D4/D6 at registration time (live validation). Post-hoc validate_chamber() misses hash re-verification (D3), ref correctness beyond existence (D4), and state transition legality (D6). Architectural difference, not quality deficiency.
- **Pre-compaction reachability:** 1.0 vs 1.0 (gap=0.0) [ZERO] -- Pre-compaction reachability matches MockLM ceiling exactly.
- **Forge trace compression:** 1.096x vs 1.1959x (gap=0.0999) [EXPLAINED] -- MockLM compression measured on controlled test data (1.096x). Real forge compression on OpenClaw ledger (1.1959x) uses different data structure with higher repetition. Gap of 0.0999x reflects data composition differences, not forge degradation.

## Consistency Checks

- Three-tier ordering (forge >= structured >= uninstrumented): PASS
- Pre-compaction reachability match (Phase 2 = Phase 4 = MockLM = 1.0): PASS
- Detection rate sum (per-type sum = aggregate): PASS
- Detection rate arithmetic (40/90 = 0.4444444444444444): PASS

## Source Traceability

| Row | Source File | Source Field |
| --- | --- | --- |
| 1. Violation detection (D1-D6 types) | `/Users/darkfire/forge/primordial/data/campaign/campaign-report.json` | `injection_summary.detection_rates.per_type.{D1..D6}.forge.rate` |
| 2. Violation detection (all D1-D9) | `/Users/darkfire/forge/primordial/data/campaign/campaign-report.json` | `injection_summary.detection_rates.per_type.{D1..D9}.forge.rate` |
| 3. Aggregate injection detection rate | `/Users/darkfire/forge/primordial/data/campaign/campaign-report.json` | `injection_summary.detection_rates.aggregate.forge.rate` |
| 4. Natural violation count | `/Users/darkfire/forge/primordial/data/campaign/campaign-report.json` | `clean_summary.natural_violation_candidates` |
| 5. False positive rate | `/Users/darkfire/forge/primordial/data/campaign/campaign-report.json` | `clean_summary.false_positive_rate` |
| 6. Pre-compaction reachability | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `pre_compaction_baseline.reachability_fraction` |
| 7. Structural reachability @ 50% simulated deletion | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `deletion_sweep[fraction=0.5].structural_reachability` |
| 8. Structural reachability @ 80% simulated deletion | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `deletion_sweep[fraction=0.8].structural_reachability` |
| 9. Backtracking threshold crossed | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `anchor_comparison.backtracking_threshold.structural_crossing_fraction` |
| 10. Forge trace compression | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `pre_compaction_baseline.compression_ratio` |
| 11. Provenance depth | `/Users/darkfire/forge/primordial/data/baselines/baseline-report.json` | `tier_metrics.forge_instrumented.provenance_depth.mean` |
| 12. Violation regression post-compaction | `/Users/darkfire/forge/primordial/data/compaction/compaction-report.json` | `violation_regression.all_passed` |

---

_Note: MockLM ceiling values are hardcoded benchmark anchors from tools/experiment_results.json (ref-mock-experiment). All other values are loaded programmatically from the source JSON files listed above._
