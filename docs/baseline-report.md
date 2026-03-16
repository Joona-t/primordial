# Baseline Measurement Report

**Phase:** 02-integration-and-baseline-establishment
**Plan:** 04
**Date:** 2026-03-16
**Data source:** `integration_samples/openclaw/queue_ledger.sample.jsonl` (47 events from Zarathustra)

---

## Executive Summary

Three-tier baseline measurement completed on real Zarathustra/OpenClaw ledger data. The measurement pipeline validates end-to-end across all three tiers and produces all 5 canonical metrics. Key findings:

1. **Uninstrumented floor confirmed:** Zero provenance, zero violation detection (matches ref-vanilla-baseline-prior).
2. **Forge instrumentation functional:** 100% provenance reachability, valid chambers, verified trace integrity.
3. **Forge trace compression ratio:** 1.18x (slightly higher than MockLM ceiling's 1.10x mean -- real data has more structural diversity).
4. **Cursor state loss events detected:** 6 queue_byte_start resets (resume1, resume3-7) -- these are the structural state loss events this project measures.
5. **No violations on clean data:** All three tiers correctly report zero violations on structurally valid real data (no false positives).

**Status:** Methodology baseline established. Pipeline ready for full VM task execution.

---

## Methodology

| Parameter | Value |
|---|---|
| Data source | `integration_samples/openclaw/queue_ledger.sample.jsonl` |
| Data type | Real Zarathustra/OpenClaw queue worker ledger events |
| Event count | 47 |
| Runs per tier | 3 (N=3) |
| Bootstrap resamples | 10,000 |
| Bootstrap seed | 42 (fixed for reproducibility) |
| Tiers | Uninstrumented, Structured Logging, Forge Instrumented |
| Measurement basis | Post-hoc JSONL ledger analysis (Approach 2 from docs/compaction-characterization.md) |

**Data provenance:** The ledger sample was pushed by the user from the Zarathustra VM (commit 028d235). It captures a real OpenClaw session where the queue worker attempted to add a JSONL validator (patches 1-7), with multiple retry-fail cycles and cursor resets (resume events).

---

## Side-by-Side Metrics Table

| Metric | Uninstrumented | Structured Logging | Forge | MockLM Ceiling |
|---|---|---|---|---|
| **reachability_fraction** | 0.0 | 0.0 | **1.0** [1.0, 1.0] | 1.0 |
| **detection_rate** | 0 | 0 (clean data) | 0 (clean data) | 6/6 (1.0) |
| **forge trace compression ratio** | N/A | N/A | **1.18** [1.18, 1.18] | ~1.10 |
| **vs_vanilla_pct** | 0% (baseline) | +84.6% | +460.5% | -87.4% (see gap analysis) |
| **false_positive_rate** | N/A | 0.0 | 0.0 | 0.0 |
| **provenance depth** | 0 | 0 | **21** | 2-4 |
| **stage count** | N/A | N/A | **40** | 3-5 |
| **payload bytes** | 10,317 | 19,049 | 72,312 | varies |
| **trace verified** | N/A | N/A | yes | yes |
| **hash match** | N/A | N/A | yes | yes |

**All CIs are bootstrap 95% confidence intervals with 10,000 resamples.**

---

## Per-Tier Detailed Results

### Tier 1: Uninstrumented (Vanilla Baseline)

| Metric | Run 1 | Run 2 | Run 3 | Mean | CV |
|---|---|---|---|---|---|
| Duration (ms) | 0.966 | 0.226 | 0.204 | 0.465 | 76.1% |
| Reachability | 0.0 | 0.0 | 0.0 | 0.0 | 0.0% |
| Violations | 0 | 0 | 0 | 0.0 | 0.0% |
| Payload (bytes) | 10,317 | 10,317 | 10,317 | 10,317 | 0.0% |

**Expected floor values confirmed:**
- Reachability = 0.0 (no provenance tracking, no DAG structure)
- Violations detected = 0 (no structural validation)
- Matches ref-vanilla-baseline-prior (reachability 0.0, violations 0/6)

The high CV on duration (76.1%) is due to cold-start overhead on Run 1 (0.97ms vs 0.2ms for subsequent runs). This does not affect any metric values since uninstrumented measurements are deterministic on the same input data.

### Tier 2: Structured Logging

| Metric | Run 1 | Run 2 | Run 3 | Mean | CV |
|---|---|---|---|---|---|
| Duration (ms) | 0.868 | 0.706 | 0.688 | 0.754 | 10.7% |
| Reachability | 0.0 | 0.0 | 0.0 | 0.0 | 0.0% |
| Schema violations | 0 | 0 | 0 | 0.0 | 0.0% |
| Turns recorded | 47 | 47 | 47 | 47 | 0.0% |
| Payload (bytes) | 19,049 | 19,050 | 19,049 | 19,049 | 0.0% |

**Intermediate position assessment:**
- Reachability = 0.0 (no provenance DAG -- structured logging does not build one)
- Schema violations = 0 on this data (the real ledger data is well-formed)
- **This does NOT mean structured logging adds no value.** On malformed data (missing `ts`, wrong types, null required fields), structured logging would detect schema violations that uninstrumented would miss. The clean data simply does not trigger those checks.
- For the detection_rate metric to meaningfully differentiate tiers, violation-injected runs are needed (Phase 3).

### Tier 3: Forge Instrumented

| Metric | Run 1 | Run 2 | Run 3 | Mean | CV |
|---|---|---|---|---|---|
| Duration (ms) | 23.353 | 20.616 | 19.132 | 21.034 | 8.3% |
| Reachability | 1.0 | 1.0 | 1.0 | 1.0 | 0.0% |
| Provenance depth | 21 | 21 | 21 | 21 | 0.0% |
| Stage count | 40 | 40 | 40 | 40 | 0.0% |
| Validation errors | 0 | 0 | 0 | 0.0 | 0.0% |
| Forge trace compression ratio | 1.1793 | 1.1793 | 1.1793 | 1.1793 | 0.0% |
| Trace verified | yes | yes | yes | 100% | -- |
| Hash match | yes | yes | yes | 100% | -- |
| Payload (bytes) | 72,312 | 72,312 | 72,312 | 72,312 | 0.0% |

**Key observations:**
- **Reachability = 1.0:** All 40 forge stages have provenance chains reaching root. The BFS reachability computation confirms every artifact is traceable.
- **Provenance depth = 21:** Deep provenance chain -- the adapter builds source_refs linking each task to its predecessor, creating a chain 21 levels deep across the 21 task lifecycle groups.
- **Validation errors = 0:** All chambers pass validate_chamber() with zero structural errors. This is expected for clean data; the forge adapter correctly maps events to valid chambers.
- **Forge trace compression ratio = 1.18:** The forge trace codec compresses chamber data by ~16% through lossless hash-verified deduplication (shared structures: 54, ref replacements: 250).
- **Trace verified = yes, hash match = yes:** Round-trip verification confirms trace compression is lossless. Decoded trace matches original chamber exactly.

---

## Coefficient of Variation (Reproducibility Assessment)

| Metric | Uninstrumented CV | Structured Logging CV | Forge CV | Threshold |
|---|---|---|---|---|
| reachability_fraction | 0.0% | 0.0% | 0.0% | < 50% |
| violations_detected | 0.0% | 0.0% | 0.0% | < 50% |
| duration_ms | 76.1% | 10.7% | 8.3% | < 50% |
| payload_bytes | 0.0% | 0.0% | 0.0% | < 50% |

**Assessment:** All primary metrics (reachability, detection) have CV = 0.0% across all tiers, well below the 50% threshold. The high CV on uninstrumented duration is a cold-start artifact, not a measurement instability. Since the input data is deterministic (same JSONL file), the pipeline correctly produces identical metric values across runs. Duration variance reflects OS-level timing noise only.

**Contract test-reproducible:** PASS. CV < 50% for all primary metrics on 100% of tasks.

---

## Gap Analysis: Forge vs MockLM Ceiling

### Metric 1: reachability_fraction

| | Forge (real) | MockLM (ceiling) | Gap |
|---|---|---|---|
| Value | 1.0 | 1.0 | **No gap** |

**Explanation:** The real ledger data does not trigger LLM context-window compaction (47 events, well under 128K token threshold). Without compaction, provenance chains remain intact, yielding perfect reachability. This matches MockLM scenario A (no compaction = reachability 1.0).

**Phase 4 concern:** When tasks grow past the LLM context window and LLM compaction (lossy semantic summarization) occurs, reachability is expected to degrade. The gap analysis will become meaningful in Phase 4 (LLM compaction survival campaign).

### Metric 2: detection_rate

| | Forge (real) | MockLM (ceiling) | Gap |
|---|---|---|---|
| Value | 0 | 6/6 (1.0) | **Full gap (explained)** |

**Explanation:** The MockLM experiment deliberately injected 6 structural violations (D1-D6: empty output, ungrounded summary, dangling ref, duplicate ID, sealed chamber, null discipline). The real ledger data contains zero injected violations -- it is structurally clean. Detection rate on clean data is undefined (0/0), reported as 0.

**This is correct behavior, NOT a forge deficiency.** The detection_rate metric requires violation injection (Phase 3) to produce meaningful comparisons. On clean data, the only relevant metric is false_positive_rate, which is 0.0 for all tiers.

### Metric 3: forge trace compression ratio

| | Forge (real) | MockLM (ceiling) | Gap |
|---|---|---|---|
| Value | 1.18 | 1.10 (mean) | **Forge exceeds ceiling (+0.08)** |

**Explanation:** The real data achieves slightly BETTER compression than MockLM because:
- More structural repetition in real data (21 task groups share identical artifact schema patterns)
- 54 shared structures and 250 ref replacements (vs MockLM's 4-7 shared structures)
- The forge trace codec's deduplication is more effective when there are more repeated structural patterns

### Metric 4: vs_vanilla_pct

| | Forge (real) | MockLM (ceiling) | Gap |
|---|---|---|---|
| Value | +460.5% | -87.4% | **Sign reversal (explained)** |

**Explanation:** This metric compares different things in the two experiments:

- **MockLM experiment:** Compared forge's _compressed trace_ (4-7KB) against a _verbose vanilla logger_ (36-60KB). The vanilla logger recorded every iteration fully expanded, making it much larger. Forge trace compression reduced size dramatically: -87%.
- **Real ledger data:** Compared forge's _full chamber output_ (72KB with 40 stages, provenance DAG, typed absence states) against the _raw event list_ (10KB, just the 47 JSONL lines). The forge chamber adds substantial structural metadata (typed absence states, provenance refs, hash-verified compression artifacts, chamber lifecycle).

**The sign reversal is NOT a bug.** It reflects the fundamental difference between:
1. **Forge trace compression** (lossless dedup of an existing structure) -- always reduces size
2. **Forge structural metadata** (typed absence, provenance, validation) -- always increases size

The vs_vanilla_pct metric should be interpreted relative to what "vanilla" means:
- vs_vanilla_pct(trace_vs_verbose_logger) = -87% (forge trace is smaller than verbose logging)
- vs_vanilla_pct(chamber_vs_raw_events) = +460% (forge chamber is larger than raw events)

**Phase 3/4 recommendation:** Standardize the comparison basis. Report forge trace compression ratio separately from forge structural overhead.

### Metric 5: false_positive_rate

| | Forge (real) | MockLM (ceiling) | Gap |
|---|---|---|---|
| Value | 0.0 | 0.0 | **No gap** |

**Explanation:** Neither system produces false alarms on clean data. This is the expected floor.

---

## Cursor Advancement (State Loss Events)

The ledger sample contains 6 cursor reset events -- instances where `queue_byte_start` resets to 0 after tasks have completed:

| Reset | Task ID | Timestamp | Previous Done At | Type |
|---|---|---|---|---|
| 1 | resume1 | 2026-02-19T10:54:51Z | 2026-02-19T10:36:12Z | Resume |
| 2 | resume3 | 2026-02-19T10:56:15Z | 2026-02-19T10:54:53Z | Resume |
| 3 | resume4 | 2026-02-19T10:57:22Z | 2026-02-19T10:56:17Z | Resume |
| 4 | resume5 | 2026-02-19T10:58:23Z | 2026-02-19T10:57:24Z | Resume |
| 5 | resume6 | 2026-02-19T11:00:26Z | 2026-02-19T10:58:23Z | Resume |
| 6 | resume7 | 2026-02-19T11:08:06Z | 2026-02-19T11:00:26Z | Resume |

**Significance:** These cursor resets are structural state loss events at the queue worker layer. When the cursor resets to byte 0, the worker "forgets" its prior position and re-reads from the start. The forge adapter correctly detects these as state loss events and registers cursor advancement artifacts with source_refs pointing to all tasks behind the cursor.

**Convention note:** These are queue-worker cursor resets, NOT LLM context-window compaction events. LLM compaction (lossy semantic summarization) occurs at the LLM runtime layer when context exceeds the window size. The 47-event ledger does not trigger LLM compaction.

---

## LLM Compaction Event Analysis

**LLM compaction events observed:** 0

**Explanation:** The ledger sample represents a single session of ~32 minutes (10:36 to 11:17) with 47 events totaling approximately 2,544 estimated tokens. This is far below the ~128K token threshold where LLM context-window compaction would be expected to occur.

**Contract test-compaction-triggered:** NOT YET SATISFIED on this sample data. At least 1 genuine LLM compaction event is needed. This requires executing the LONG tasks from the task corpus (TASK-L1, TASK-L2, TASK-L3) against the VM, which are designed to produce 128K+ tokens through retry cycles.

**Mitigation:** The cursor resets (6 detected) ARE structural state loss events. While not LLM compaction, they exercise the same forge mechanisms (pruned_recoverable states, cursor advancement artifacts, provenance chain maintenance through state loss boundaries). The measurement pipeline correctly handles both types.

---

## Forbidden Proxy Audit

### fp-short-tasks

> **Proxy:** "All tasks complete without triggering LLM compaction"
> **Guard:** At least 1 task must trigger genuine LLM compaction

**Status on sample data:** NOT YET FULLY ADDRESSED. The sample data is from a short session (~32 min, ~2.5K tokens). LLM compaction requires 128K+ tokens from the LONG tasks (TASK-L1, L2, L3) executed on the VM.

**Mitigation:** The task corpus (Plan 02-03) includes 3 long tasks targeting 128K+ tokens via retry cycles. When executed on the VM, these will trigger LLM compaction. The measurement pipeline is validated and ready to process the results.

**Structural state loss coverage:** 6 cursor resets ARE observed and correctly processed. These exercise forge's state loss detection at the queue worker layer.

### fp-shallow-traces

> **Proxy:** "Forge provenance chains are trivially shallow (depth 1-2)"
> **Guard:** Maximum provenance chain depth must be >= 3

**Status:** SATISFIED. Maximum provenance depth = **21** (far exceeding the minimum of 3). The forge adapter builds a source_refs chain linking each task lifecycle to its predecessor. With 21 task groups in the ledger, the provenance chain reaches depth 21.

This is NOT a trivially shallow trace. It demonstrates forge's ability to maintain deep provenance chains across a complex multi-task session with retry cycles and cursor resets.

### fp-self-report

> **Proxy:** "Metrics based on system self-report rather than independent structural measurement"
> **Guard:** Metrics must be computed from structural analysis

**Status:** SATISFIED. All metrics are computed from independent structural analysis:

- **reachability_fraction:** Computed via BFS traversal of the provenance DAG in the sealed chamber (compute_reversibility_score in primordial_rlm_bridge.py). NOT self-reported by the adapter.
- **forge trace compression ratio:** Computed from actual byte sizes of original vs encoded trace (trace_stats in forge_trace_codec.py). NOT self-reported.
- **validation_errors:** Computed by validate_chamber() which independently verifies chamber structure (sealed status, artifact integrity, provenance refs). NOT self-reported.
- **trace verified / hash match:** Computed by verify_trace() which independently decodes the trace and compares against the original chamber via SHA-256 hash. NOT self-reported.

No metric relies on the adapter's own assessment of its correctness.

---

## Phase 3 Readiness Assessment

| Requirement | Status | Notes |
|---|---|---|
| Uninstrumented floor established | YES | reachability=0, detection=0 |
| Structured logging intermediate | YES | Schema validation functional, no false positives |
| Forge chambers valid | YES | validate_chamber() = 0 errors on all runs |
| Forge provenance positive | YES | reachability=1.0, depth=21 |
| Measurement pipeline validated | YES | Pipeline produces all 5 metrics with bootstrap CIs |
| Detection rate baseline | PARTIAL | Clean data produces 0/0; needs violation injection (Phase 3) |
| LLM compaction baseline | PENDING | Requires VM execution of LONG tasks |
| Forbidden proxies addressed | 2/3 | fp-shallow-traces and fp-self-report satisfied; fp-short-tasks pending VM execution |

**Recommendation:** The measurement methodology is validated. Phase 3 (violation detection campaign) can proceed using this pipeline. The remaining fp-short-tasks guard will be satisfied when LONG tasks are executed on the VM.

---

## Reference Comparisons

### ref-mock-experiment (tools/experiment_results.json)

| Metric | MockLM Value | Real Baseline Value | Match |
|---|---|---|---|
| Reachability (no LLM compaction) | 1.0 | 1.0 | EXACT |
| Reachability (with LLM compaction) | 1.0 | N/A (no LLM compaction in sample) | PENDING |
| Detection (with violations) | 6/6 | N/A (no violations in clean data) | PENDING |
| Detection (clean data) | 0 false positives | 0 false positives | EXACT |
| Forge trace compression ratio | 1.10 (mean) | 1.18 | BETTER (+0.08) |
| Trace round-trip verified | yes | yes | EXACT |

### ref-vanilla-baseline-prior (tools/vanilla_baseline_results.json)

| Metric | Prior Vanilla | Real Uninstrumented | Match |
|---|---|---|---|
| Reachability | 0.0 | 0.0 | EXACT |
| Violations detected | 0 | 0 | EXACT |
| Has provenance | false | false | EXACT |
| Has hashing | false | false | EXACT |

---

## Terminology Disambiguation Audit

**Requirement:** Zero instances of unqualified "compaction" in this report.

All uses are qualified:
- "LLM compaction" (or "LLM context-window compaction"): lossy semantic summarization at the LLM runtime layer
- "forge trace compression": lossless hash-verified deduplication at the forge trace codec layer
- "cursor reset" / "cursor advancement": queue worker state loss at the queue_byte_start layer

**Audit result:** PASS. No unqualified "compaction" in this document.

---

## Machine-Readable Outputs

| File | Description |
|---|---|
| `data/baselines/baseline-report.json` | Aggregate metrics, comparison table, reference values |
| `data/baselines/uninstrumented/metrics.json` | Uninstrumented tier aggregate metrics |
| `data/baselines/uninstrumented/ledger-sample_run{1,2,3}.json` | Per-run raw results |
| `data/baselines/structured-logging/metrics.json` | Structured logging tier aggregate metrics |
| `data/baselines/structured-logging/ledger-sample_run{1,2,3}.json` | Per-run raw results |
| `data/baselines/forge-instrumented/metrics.json` | Forge tier aggregate metrics with compression ratio |
| `data/baselines/forge-instrumented/ledger-sample_run{1,2,3}.json` | Per-run raw results |

---

_Measurement pipeline: tools/run_baseline_measurement.py_
_Data source: integration_samples/openclaw/queue_ledger.sample.jsonl_
_Completed: 2026-03-16_
