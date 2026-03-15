# Conventions Ledger

**Project:** Primordial Computing: Typed Absence and Provenance in Agentic Systems
**Created:** 2026-03-15
**Last updated:** 2026-03-15 (Phase 1)

> This file is append-only for convention entries. When a convention changes, add a new
> entry with the updated value and mark the old entry as superseded. Never delete entries.

> This is a formal systems / computer science research project. All 18 canonical physics
> convention slots (metric signature, Fourier convention, gauge choice, etc.) are N/A.
> All conventions below are project-specific.

---

## Absence Ontology

### 1. Absence State Ontology

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | 8 canonical absence states: `not_generated`, `not_invoked`, `unknown`, `unresolved`, `withheld`, `invalid`, `deleted`, `pruned_recoverable`. Defined in `V1_ABSENCE_STATES` frozenset in `forge_nulls.py`. |
| **Introduced**   | Phase 1 (provisional -- locks implementation as ground truth pending FORM-01 formal resolution) |
| **Rationale**    | Implementation in forge_nulls.py is the executable specification; PROJECT.md listed `resolved` instead of `not_generated` which is a documentation error flagged for Phase 1 reconciliation |
| **Dependencies** | State Transition Legality (convention #3), Violation Classification (convention #8), all forge validation functions |
| **Test value**   | `normalize_absence_state("pruned_recoverable")` returns `"pruned_recoverable"`; `normalize_absence_state("resolved")` raises `ValueError` |

**Deprecated alias:** `pruned` maps to `pruned_recoverable` via `_LEGACY_ALIASES`.

**Known discrepancy (flagged for Phase 1 FORM-01):**
- PROJECT.md lists: `not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable, resolved`
- Implementation has: `not_generated, not_invoked, unknown, unresolved, withheld, invalid, deleted, pruned_recoverable`
- Differences: `resolved` in docs but not code; `not_generated` in code but not docs
- Resolution: Phase 1 FORM-01 will produce the authoritative ontology. Until then, implementation wins.

**Open questions (Phase 1 FORM-03):**
- Should `timed_out` and `interrupted` be added as distinct states (expanding to 10)?
- Should recoverability be binary or graded?

### 2. Absence Object Canonical Form

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Canonical v1 shape: `{"value": None, "state": "<AbsenceState>"}`. Optional `"reason"` field for human-readable explanation. |
| **Introduced**   | Phase 1 |
| **Rationale**    | v1 convergence in forge_nulls.py uses `state` as the canonical key; `absence_state` is legacy ingress only |
| **Dependencies** | Absence State Ontology (convention #1), all forge validation and normalization functions |
| **Test value**   | `normalize_absent_object({"value": None, "state": "unknown"})` returns unchanged; `normalize_absent_object({"value": None, "absence_state": "pruned"})` normalizes to `{"value": None, "state": "pruned_recoverable"}` |

**Legacy ingress form:** `{"value": None, "absence_state": "<AbsenceState>"}` -- accepted by `normalize_absent_object()` with deprecation warning, rewritten to canonical form.

**Sibling-field pattern:** For flat records, absence can be expressed as `{"output": None, "output_state": "not_generated"}` where the `_state` suffix field carries the typed absence state. Both patterns are valid; standalone absent objects are preferred for nested structures.

### 3. State Transition Legality

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Every `(source_state, target_state)` pair in the 8-state ontology is classified as legal, illegal, or conditional. The complete 8x8 transition matrix (64 entries) is the primary deliverable of Phase 1 FORM-01. |
| **Introduced**   | Phase 1 (skeleton -- full matrix pending FORM-01) |
| **Rationale**    | Transition legality is the core formal property; Hoare-style precondition/postcondition contracts on state changes |
| **Dependencies** | Absence State Ontology (convention #1), Violation Classification (convention #8), Hypothesis stateful testing (Phase 1 FORM-02) |
| **Test value**   | Phase 1 will deliver: `validate_transition(from_state, to_state)` returns True/False for every pair in the 8x8 matrix. Hypothesis `RuleBasedStateMachine` will generate 10K+ random transition sequences without invariant violations. |

**Explicitly illegal transitions (known prior to full formalization):**
- Any state -> `not_invoked` (cannot un-invoke)
- Any state -> `not_generated` (cannot un-generate)
- `deleted` -> any state except `deleted` (deletion is terminal, or requires explicit recovery protocol)

These will be verified and extended by Phase 1.

---

## Provenance

### 4. Provenance Reference Format

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Lightweight `parent_id` + `source_refs` model. `source_refs` is a list of structured refs `[{"ref": "artifact:...", ...}]` or string artifact IDs. Single-runtime lineage only. Not full W3C PROV. |
| **Introduced**   | Phase 1 |
| **Rationale**    | W3C PROV Entity-Activity-Agent triad is too heavy for single-runtime traces that must survive compaction; `parent_id` + `source_refs` captures the derivation and generation relations needed for DAG reachability |
| **Dependencies** | Artifact ID Format (convention #5), Metrics Definitions (convention #7, reachability_fraction), chamber validation |
| **Test value**   | A valid `source_ref` resolves to an artifact in the chamber's `artifact_index` set; an unresolvable ref produces error code `REF.REF_UNRESOLVED` |

**Empty refs are valid:** `refs: []` and `source_refs: []` are semantically valid (no upstream references). These are exempt from null discipline via `V1_REF_CONTAINER_KEYS`.

### 5. Artifact ID Format

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Colon-separated hierarchical IDs. Artifacts: `artifact:<run>:stage:<seat>:<revision>`. Chambers: `chamber:<seg1>:<seg2>[:<segN>]`. Validated by regex `^chamber:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$` for chambers; artifacts follow analogous pattern with `artifact:` prefix. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Colon-separated segments enable hierarchical namespace, sorting, and grep-ability without filesystem path ambiguity |
| **Dependencies** | Provenance Reference Format (convention #4), chamber `artifact_index` membership checks |
| **Test value**   | `"artifact:run100:stage:builder:r1"` is valid; `"artifact run100"` is invalid (space instead of colon); `"chamber:run100:v1"` is valid |

---

## Compaction and Integrity

### 6. Compaction Disambiguation

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | "Compaction" has two distinct meanings that must ALWAYS be qualified. Unqualified "compaction" is **forbidden** in all derivation and measurement files. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Conflating forge trace compression (lossless, hash-verified) with LLM context-window compaction (lossy, semantic) is the single most likely source of measurement errors in this project |
| **Dependencies** | Metrics Definitions (convention #7), Hash Integrity (convention #10) |
| **Test value**   | `encode_trace()` + `decode_trace()` round-trip produces bitwise-identical output (SHA-256 match) -- this is **forge compaction**. LLM compaction does NOT have this property. |

**Forge compaction** (a.k.a. trace compression):
- Lossless structural deduplication via `encode_trace()` / `decode_trace()`
- Hash-verified round-trip integrity (SHA-256)
- Controlled entirely by forge tools
- Measured by `compression_ratio`

**LLM compaction** (a.k.a. context-window compaction):
- Lossy semantic summarization replacing message history
- NOT controlled by forge
- Forge records `pruned_recoverable` state for items lost to LLM compaction
- Measured by `reachability_fraction` degradation

### 10. Hash Integrity Convention

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | SHA-256 on canonical (deterministic) JSON serialization: `json.dumps(obj, sort_keys=True, ensure_ascii=True)`. Used for round-trip verification of forge trace compression. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Deterministic serialization ensures hash stability across Python versions and platforms; SHA-256 collision probability is 2^-128, sufficient for integrity verification |
| **Dependencies** | Compaction Disambiguation (convention #6), forge_trace_codec.py |
| **Test value**   | `verify_trace(trace, chamber)` returns `{"valid": True, "hash_match": True, "content_match": True}` for an untampered trace |

---

## Metrics

### 7. Metrics Definitions

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | All project metrics are dimensionless ratios or counts. Definitions below are canonical and must not be used with alternative formulas. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Precise metric definitions prevent silent measurement errors; each metric has a single formula |
| **Dependencies** | Compaction Disambiguation (convention #6), Violation Classification (convention #8) |
| **Test value**   | MockLM anchor: reachability_fraction = 1.0, compression vs vanilla = 87% reduction, violation detection = 6/6 |

| Metric | Formula | Range | Notes |
| ------ | ------- | ----- | ----- |
| `reachability_fraction` | (reachable artifacts via BFS/DFS on provenance DAG) / (total artifacts) | [0, 1] | 1.0 = complete structural provenance; computed exactly via NetworkX |
| `compression_ratio` | `original_size / encoded_size` | (1, inf) | Forge internal dedup only; ratio > 1.0 means compression achieved; distinct from LLM compaction |
| `vs_vanilla_pct` | `(forge_size - vanilla_size) / vanilla_size * 100` | (-100, inf) | Overhead comparison; negative = forge is smaller; positive = forge is larger |
| Detection rate | violations_detected / total_violations | [0, 1] | Reported with bootstrap 95% CI for N < 30 |
| False positive rate | false_alarms / clean_runs | [0, 1] | Measured on uninstrumented clean runs |

**MockLM anchor values (controlled-condition ceiling):**
- reachability_fraction = 1.0 (100%)
- Violation detection = 6/6 (100%)
- Trace compression vs vanilla = 87% reduction (compression_ratio >= 1.87)

### 8. Violation Classification

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Violations are **structural only**: illegal state transitions or missing metadata. Distinguished from hallucination (content error), fault (infrastructure failure), and semantic error (wrong value). Only structural violations are in scope for forge detection. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Typed absence addresses structural correctness, not semantic correctness; honest scoping prevents overclaiming |
| **Dependencies** | Absence State Ontology (convention #1), State Transition Legality (convention #3) |
| **Test value**   | `{"output": None}` with no `output_state` field is a structural violation (ABSENCE.MISSING_STATE_LABEL). `{"output": "wrong answer", "state": "unknown"}` is NOT a structural violation. |

**Fault injection taxonomy (D1-D9):**
- D1: Null collapse (typed absence degrades to bare None)
- D2: Broken provenance (source_refs point to nonexistent artifacts)
- D3: Corrupted hashes (SHA-256 mismatch on round-trip)
- D4: Fake source refs (refs that resolve but to wrong artifacts)
- D5: Missing state label (ambiguous empty without typed absence)
- D6: Illegal state transition (violates transition matrix)
- D7: Compaction data loss (forge compaction loses information)
- D8: Context pressure corruption (data corruption under memory pressure)
- D9: Timeout/interruption handling (ungraceful termination)

---

## System

### 9. Unit System

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | Not applicable. All metrics are dimensionless ratios or counts. No physical units in this project. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Formal systems research; all quantities are pure numbers |
| **Dependencies** | None |
| **Test value**   | Every metric in the project (reachability_fraction, compression_ratio, vs_vanilla_pct, detection rate, false positive rate) is expressible as a pure dimensionless number |

### 11. Protocol Versioning

| Field            | Value |
| ---------------- | ----- |
| **Convention**   | `schema_version = "forge.internal.v1"` for chamber and artifact schemas. `encoding = "forge.trace.v1"` for trace codec payloads. Legacy pre-v1 ingress is accepted but normalized to v1 canonical form. |
| **Introduced**   | Phase 1 |
| **Rationale**    | Explicit versioning enables backward-compatible evolution; normalization at ingress ensures downstream code only handles one schema version |
| **Dependencies** | Absence Object Canonical Form (convention #2), all forge modules |
| **Test value**   | `decode_trace()` raises `ForgeTraceError` if `trace.encoding != "forge.trace.v1"` |

---

## Convention Changes

> When a convention must change, record the change here. The old entry above stays;
> a new entry is added with a reference back.

| Change ID | Convention | Old Value | New Value | Changed In | Reason | Conversion |
| --------- | ---------- | --------- | --------- | ---------- | ------ | ---------- |
| (none yet) | | | | | | |

---

## Cross-Convention Compatibility Notes

> Record any known interactions between conventions that produce subtle errors.
> These are the "gotchas" that cause cross-phase errors.

| Convention A | Convention B | Interaction | Risk | Example |
| ------------ | ------------ | ----------- | ---- | ------- |
| #1 Absence State Ontology (8 states) | #3 State Transition Legality | Transition table dimensions are 8x8 (64 entries); adding/removing states changes the matrix | Adding `timed_out` and `interrupted` (Phase 1 FORM-03) would expand to 10x10 = 100 entries | If `timed_out` is added, every existing transition rule must be re-evaluated for the new state |
| #6 Compaction Disambiguation | #7 Metrics Definitions | `compression_ratio` measures forge compaction ONLY; `reachability_fraction` degrades under LLM compaction | Reporting `compression_ratio` as evidence of compaction survival would be a category error | MockLM anchor 87% compression is forge-only; LLM compaction degrades reachability_fraction from 1.0 |
| #4 Provenance Reference Format | #5 Artifact ID Format | `source_refs` must contain valid artifact IDs from the chamber's `artifact_index` | A source_ref with a syntactically valid but unregistered ID passes format validation but fails chamber validation | `"artifact:run100:stage:ghost:r1"` passes regex but fails `REF.REF_UNRESOLVED` if not in index |
| #10 Hash Integrity | #6 Compaction Disambiguation | Hash verification applies to forge compaction (lossless) only; meaningless for LLM compaction (lossy) | Claiming "hash-verified compaction" without qualifying which layer is misleading | `verify_trace()` passes on forge-compressed data; it cannot verify LLM-compacted content |
| #8 Violation Classification | #1 Absence State Ontology | Violations are defined as illegal transitions in the ontology or missing state labels | A new absence state that lacks transition rules is an implicit violation source | If `timed_out` is added without defining legal transitions, any transition involving it is undefined |

---

## Machine-Readable Convention Tests

```yaml
# Parseable by consistency checker for automated validation
# All physics convention tests are N/A for this project
convention_tests:
  absence_state_ontology:
    canonical_states: ["not_generated", "not_invoked", "unknown", "unresolved", "withheld", "invalid", "deleted", "pruned_recoverable"]
    state_count: 8
    deprecated_aliases: {"pruned": "pruned_recoverable"}
    test: "normalize_absence_state('pruned_recoverable') == 'pruned_recoverable'; normalize_absence_state('resolved') raises ValueError"
  absence_object_form:
    canonical_key: "state"
    legacy_key: "absence_state"
    required_fields: ["value", "state"]
    value_must_be: null
    test: "normalize_absent_object({'value': None, 'state': 'unknown'}) returns unchanged"
  transition_legality:
    matrix_dimensions: "8x8"
    total_entries: 64
    known_illegal: [["any", "not_invoked"], ["any", "not_generated"], ["deleted", "any_except_deleted"]]
    test: "Phase 1 FORM-01 deliverable: validate_transition(from, to) for all 64 pairs"
    status: "skeleton -- pending FORM-01"
  provenance_refs:
    format: "parent_id + source_refs list"
    ref_pattern: "artifact:<run>:stage:<seat>:<revision>"
    empty_refs_valid: true
    test: "Unresolvable ref produces REF.REF_UNRESOLVED error"
  artifact_id_format:
    artifact_pattern: "artifact:<run>:stage:<seat>:<revision>"
    chamber_pattern: "chamber:<seg1>:<seg2>[:<segN>]"
    chamber_regex: "^chamber:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$"
    test: "'chamber:run100:v1' matches regex; 'artifact run100' does not"
  compaction_disambiguation:
    forge_compaction: "lossless, hash-verified, encode_trace/decode_trace"
    llm_compaction: "lossy, semantic, uncontrolled by forge"
    unqualified_forbidden: true
    test: "encode_trace + decode_trace round-trip is SHA-256 identical"
  metrics:
    reachability_fraction: "(reachable via BFS) / total"
    compression_ratio: "original_size / encoded_size"
    vs_vanilla_pct: "(forge_size - vanilla_size) / vanilla_size * 100"
    mockml_anchors:
      reachability: 1.0
      violation_detection: "6/6"
      compression_vs_vanilla: "87% reduction"
  violation_classification:
    scope: "structural only"
    out_of_scope: ["hallucination", "fault", "semantic_error"]
    fault_taxonomy: ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
    test: "{'output': None} without output_state is violation; {'output': 'wrong', 'state': 'unknown'} is not"
  unit_system:
    system: "N/A"
    all_metrics_dimensionless: true
  hash_integrity:
    algorithm: "SHA-256"
    serialization: "json.dumps(obj, sort_keys=True, ensure_ascii=True)"
    test: "verify_trace returns hash_match=True for untampered trace"
  protocol_versioning:
    chamber_schema: "forge.internal.v1"
    trace_encoding: "forge.trace.v1"
    legacy_accepted: true
    test: "decode_trace raises ForgeTraceError if encoding != forge.trace.v1"
```

---

_Conventions ledger created: 2026-03-15_
_Last updated: 2026-03-15 (Phase 1)_
