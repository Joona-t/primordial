# Null Ontology — Draft v0

## Purpose

This document defines the initial ontology of absence states for Primordial Computing.

The goal is to replace generic null-collapse with explicit state categories that support validation, transition rules, and provenance-aware reasoning.

## State set

### `resolved`
A valid artifact or value exists and is available.

### `not_invoked`
The computation or action was never started.

### `unknown`
The system cannot determine whether a value exists or what it is.

### `unresolved`
The computation has been initiated or is expected, but has not yet reached a valid terminal result.

### `withheld`
A value exists or may exist, but is intentionally not exposed at the current layer.

### `invalid`
A produced value or artifact exists, but failed protocol or semantic validation.

### `deleted`
A previously available value/artifact has been intentionally removed and is not recoverable through ordinary dereference.

### `pruned_recoverable`
A value/artifact has been removed from the active working set, but remains recoverable through a grounded source path.

## State semantics

These states are not interchangeable. In particular:
- `unknown` is not `deleted`
- `not_invoked` is not `unresolved`
- `pruned_recoverable` is not `deleted`
- `invalid` is not merely absent

## Initial transition sketch

### Legal candidates
- `not_invoked -> unresolved`
- `not_invoked -> resolved`
- `unknown -> resolved`
- `unknown -> unresolved`
- `unresolved -> resolved`
- `unresolved -> invalid`
- `resolved -> pruned_recoverable`
- `resolved -> deleted`
- `resolved -> withheld`
- `pruned_recoverable -> resolved`
- `withheld -> resolved`

### Likely illegal candidates
- `deleted -> resolved` (unless explicitly restored from a separate source lineage)
- `not_invoked -> invalid`
- `deleted -> pruned_recoverable`

## Required metadata ideas

Certain states should require companion fields.

### `pruned_recoverable`
Should require:
- source refs
- recovery path or provenance anchor
- compaction reason

### `invalid`
Should require:
- validator or failing check
- failure reason/category

### `withheld`
Should require:
- withholding reason/class
- visibility context

### `resolved`
Should require:
- artifact identity or value body
- provenance metadata when applicable

## Open questions

1. Should `timed_out` exist as its own state?
2. Should `interrupted` be distinct from `unresolved`?
3. Should recoverability be binary or graded?
4. Should state transitions themselves be recorded as first-class artifacts?

## Next action

Convert this draft into:
- a full transition table
- validator rules
- example traces for each legal/illegal path
