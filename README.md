# Primordial

Primordial is a research project exploring whether **typed absence**, **explicit provenance**, and **recoverable compaction** can improve the reliability of long-horizon agentic systems.

This project begins from a philosophical claim and attempts to turn it into a formal, falsifiable systems program.

## Core thesis

> Zero is not mere emptiness. It is structured capacity.

In practical systems terms, this means agent runtimes should distinguish different kinds of absence—unknown, not invoked, unresolved, deleted, withheld, pruned but recoverable—instead of collapsing them into generic null-like states.

## Initial research stack

- `docs/PROJECT_CHARTER.md`
- `docs/FOUNDATIONS.md`
- `docs/NULL_ONTOLOGY.md`
- `docs/METHODOLOGY.md`

## Status

Two milestones complete: **v1.0** (2026-03-16, 5 phases) and **v2.0 "The
Forgetting Agent"** (2026-03-28, 3 phases) — see `.gpd/milestones/v1.0/` and
`.gpd/milestones/v2.0/RESEARCH-DIGEST.md` for full results, and
`docs/cross-architecture-report.md` / `docs/genuine-compaction-report.md` for
the headline findings. 1000+ tests in `tools/`.

Genuine (non-synthetic) LLM-compaction measurement remains **out of scope**:
it would require Anthropic's raw Messages API beta feature
(`compact_20260112` + `pause_after_compaction`), and this codebase never
calls a paid LLM API (fleet CLAUDE.md Rule #10 — see BUG-020 in
`BUGS_AND_ITERATIONS.md`). All compaction results in this repo are from the
deterministic synthetic (dry-run) pipeline, which is explicitly disclosed
wherever a report references it.

Still an experimental research program, not a validated theory — the v1.0/v2.0
digests state their own confidence levels per claim.
