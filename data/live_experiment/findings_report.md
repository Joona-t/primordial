# Research Findings Ledger

**Generated:** 2026-03-28T02:34:18.407616+00:00
**Total findings:** 24

## Summary

| Metric | Value |
|--------|-------|
| Total findings | 24 |
| Positive | 18 |
| Negative | 6 |
| Category: architecture | 12 |
| Category: compaction | 6 |
| Category: ontology | 6 |

## Phase 7 (24 findings)

| ID | Category | Title | Verdict | Confidence |
|----|----------|-------|---------|------------|
| F-0001 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0002 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0003 | compaction | Live SPF: jaccard=0.062, token_overlap=0.062 | negative | high |
| F-0004 | architecture | Chamber integrity: 0 validation errors | positive | high |
| F-0005 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0006 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0007 | compaction | Live SPF: jaccard=0.062, token_overlap=0.062 | negative | high |
| F-0008 | architecture | Chamber integrity: 0 validation errors | positive | high |
| F-0009 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0010 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0011 | compaction | Live SPF: jaccard=0.055, token_overlap=0.055 | negative | high |
| F-0012 | architecture | Chamber integrity: 0 validation errors | positive | high |
| F-0013 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0014 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0015 | compaction | Live SPF: jaccard=0.053, token_overlap=0.054 | negative | high |
| F-0016 | architecture | Chamber integrity: 0 validation errors | positive | high |
| F-0017 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0018 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0019 | compaction | Live SPF: jaccard=0.055, token_overlap=0.055 | negative | high |
| F-0020 | architecture | Chamber integrity: 0 validation errors | positive | high |
| F-0021 | ontology | Live agent typed absence: 0 absent fields with explicit states | positive | high |
| F-0022 | architecture | Synthesis provenance: 3 refs to 3 sources | positive | high |
| F-0023 | compaction | Live SPF: jaccard=0.047, token_overlap=0.047 | negative | high |
| F-0024 | architecture | Chamber integrity: 0 validation errors | positive | high |

### F-0001: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:29:14.624151+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0002: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:29:14.624302+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0003: Live SPF: jaccard=0.062, token_overlap=0.062

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:29:14.624397+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.062, Mean token overlap: 0.062, Mean weighted overlap: 0.124.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0621,
      "min": 0.0204,
      "max": 0.0991,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.0623,
      "min": 0.0206,
      "max": 0.0995,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.1245,
      "min": 0.0474,
      "max": 0.1714,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0004: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:29:14.624492+00:00

Chamber chamber:live-1774664954:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.03x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0256,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---

### F-0005: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:30:22.318128+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0006: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:30:22.318821+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0007: Live SPF: jaccard=0.062, token_overlap=0.062

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:30:22.319085+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.062, Mean token overlap: 0.062, Mean weighted overlap: 0.124.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0621,
      "min": 0.0204,
      "max": 0.0991,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.0623,
      "min": 0.0206,
      "max": 0.0995,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.1245,
      "min": 0.0474,
      "max": 0.1714,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0008: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:30:22.319255+00:00

Chamber chamber:live-1774665022:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.03x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0256,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---

### F-0009: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:30:56.308191+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0010: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:30:56.308478+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0011: Live SPF: jaccard=0.055, token_overlap=0.055

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:30:56.308630+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.055, Mean token overlap: 0.055, Mean weighted overlap: 0.104.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0548,
      "min": 0.0216,
      "max": 0.0824,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.055,
      "min": 0.0218,
      "max": 0.0827,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.104,
      "min": 0.0351,
      "max": 0.1538,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0012: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:30:56.308777+00:00

Chamber chamber:live-1774665056:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.02x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0228,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---

### F-0013: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:31:45.386007+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0014: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:31:45.386257+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0015: Live SPF: jaccard=0.053, token_overlap=0.054

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:31:45.386419+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.053, Mean token overlap: 0.054, Mean weighted overlap: 0.115.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0534,
      "min": 0.0151,
      "max": 0.0862,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.0536,
      "min": 0.0153,
      "max": 0.0866,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.1145,
      "min": 0.0202,
      "max": 0.1766,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0016: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:31:45.386527+00:00

Chamber chamber:live-1774665105:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.02x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0224,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---

### F-0017: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:33:21.864889+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0018: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:33:21.865134+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0019: Live SPF: jaccard=0.055, token_overlap=0.055

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:33:21.865251+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.055, Mean token overlap: 0.055, Mean weighted overlap: 0.139.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0546,
      "min": 0.0171,
      "max": 0.0827,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.0547,
      "min": 0.0173,
      "max": 0.0827,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.1391,
      "min": 0.0398,
      "max": 0.1965,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0020: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:33:21.865438+00:00

Chamber chamber:live-1774665201:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.02x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0222,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---

### F-0021: Live agent typed absence: 0 absent fields with explicit states

**Category:** ontology | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ1
**Timestamp:** 2026-03-28T02:34:18.406693+00:00

In a 4-agent live run, 0 output fields were absent. Each was classified: {}. Zero ambiguous nulls — every absence has a reason.

**Evidence:**
```json
{
  "total": 0,
  "by_state": {}
}
```

**Tags:** live-experiment, typed-absence

---

### F-0022: Synthesis provenance: 3 refs to 3 sources

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:34:18.406813+00:00

The synthesis agent's output references 3 upstream artifacts. 3 source agents produced output. Summary grounded: True.

**Evidence:**
```json
{
  "grounded": true,
  "source_ref_count": 3,
  "available_sources": 3
}
```

**Tags:** live-experiment, provenance

---

### F-0023: Live SPF: jaccard=0.047, token_overlap=0.047

**Category:** compaction | **Verdict:** negative | **Confidence:** high
**Research Question:** RQ3
**Timestamp:** 2026-03-28T02:34:18.406912+00:00

Measured 4 summary-vs-original pairs. Mean Jaccard: 0.047, Mean token overlap: 0.047, Mean weighted overlap: 0.120.

**Evidence:**
```json
{
  "pairs": 4,
  "aggregate": {
    "count": 4,
    "jaccard": {
      "mean": 0.0471,
      "min": 0.0136,
      "max": 0.0657,
      "n": 4
    },
    "token_overlap": {
      "mean": 0.0474,
      "min": 0.0138,
      "max": 0.066,
      "n": 4
    },
    "weighted_overlap": {
      "mean": 0.1201,
      "min": 0.0113,
      "max": 0.1837,
      "n": 4
    },
    "exact_match_rate": 0.0
  }
}
```

**Tags:** live-experiment, spf, compaction

---

### F-0024: Chamber integrity: 0 validation errors

**Category:** architecture | **Verdict:** positive | **Confidence:** high
**Research Question:** RQ2
**Timestamp:** 2026-03-28T02:34:18.407008+00:00

Chamber chamber:live-1774665258:v1 with 4 stages. Trace verified: True, hash match: True, compression: 1.02x.

**Evidence:**
```json
{
  "errors": [],
  "trace": {
    "verified": true,
    "hash_match": true,
    "compression_ratio": 1.0175,
    "shared_structures": 4,
    "ref_replacements": 14
  }
}
```

**Tags:** live-experiment, chamber-integrity

---
