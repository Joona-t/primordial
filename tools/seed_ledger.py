"""Seed the production findings ledger with v1.0 results + v2.0 research findings.

Run once: python3 tools/seed_ledger.py
"""

from findings_ledger import FindingsLedger, Finding, seed_v1_findings


def seed_v2_research_findings(ledger: FindingsLedger):
    """Record findings from v2.0 research phase (2026-03-27)."""
    findings = [
        Finding(
            phase=6, category="compaction", rq="RQ3b",
            title="BREAKTHROUGH: compact_20260112 API enables full compaction observability",
            description="Anthropic's compaction API with pause_after_compaction=true "
                        "returns stop_reason='compaction' with exact boundary capture. "
                        "Min trigger: 50K tokens, default 150K. This enables controlled "
                        "genuine compaction experiments — the key missing piece from v1.0.",
            evidence={
                "api": "compact_20260112",
                "param": "pause_after_compaction",
                "stop_reason": "compaction",
                "min_trigger_tokens": 50000,
                "default_trigger_tokens": 150000,
                "compaction_block_type": "compaction",
            },
            verdict="positive", confidence="high",
            tags=["COMP-04", "breakthrough", "api-discovery"],
            refs=["Phase 6 Research", "docs/phase-2.1-genuine-compaction-protocol.md"],
        ),
        Finding(
            phase=6, category="baseline", rq="RQ3b",
            title="Knowledge Objects: 60% fact loss per LLM compression pass",
            description="Zahn & Chana (arXiv:2603.17781, March 2026) measured 60% fact loss "
                        "per compression pass and 54% project constraint erosion through "
                        "cascading compaction. This validates our thesis — summaries are lossy "
                        "and without grounded provenance refs, lost facts are unrecoverable.",
            evidence={
                "paper": "Zahn & Chana, arXiv:2603.17781",
                "date": "2026-03",
                "fact_loss_per_pass": 0.60,
                "constraint_erosion": 0.54,
                "method": "Facts as First Class Objects",
            },
            verdict="positive", confidence="high",
            tags=["COMP-04", "external-validation", "literature"],
            refs=["ref-knowledge-objects"],
        ),
        Finding(
            phase=7, category="methodology", rq="RQ2b",
            title="Power analysis: 200 runs gives 98.2% power at 2% violation rate",
            description="Statistical power analysis computed. v1.0 had only 26% power "
                        "to detect a 1% rate and 45.5% for 2%. 200 runs → CP upper bound "
                        "1.8% if still 0 violations, 98.2% power at 2%. For <1% claim "
                        "need 368 runs.",
            evidence={
                "v1_runs": 30, "v1_cp_upper": 0.116, "v1_power_at_2pct": 0.455,
                "v2_target_runs": 200, "v2_cp_upper_if_zero": 0.018,
                "v2_power_at_2pct": 0.982, "v2_power_at_5pct": 1.0,
                "runs_for_1pct_bound": 368,
            },
            verdict="neutral", confidence="high",
            tags=["VIOL-04", "power-analysis", "sample-size"],
            refs=["tools/power_analysis.py", "power_analysis_results.json"],
        ),
        Finding(
            phase=7, category="baseline", rq="RQ2b",
            title="MAS-FIRE: failures manifest as 'soft semantic deviations' in multi-agent systems",
            description="MAS-FIRE taxonomy identifies 15 fault types with the key insight "
                        "that failures manifest as soft semantic deviations — exactly what "
                        "typed absence should catch. Factory.ai found artifact tracking "
                        "scores only 2.19-2.45/5.0 across all compression strategies.",
            evidence={
                "taxonomy": "MAS-FIRE",
                "fault_types": 15,
                "injection_mechanisms": 3,
                "key_insight": "soft semantic deviations",
                "factory_artifact_tracking": {"low": 2.19, "high": 2.45, "max": 5.0},
            },
            verdict="positive", confidence="medium",
            tags=["VIOL-04", "external-validation", "literature"],
            refs=["MAS-FIRE taxonomy", "Factory.ai evaluation"],
        ),
        Finding(
            phase=8, category="architecture", rq="RQ4",
            title="All 4 target frameworks have sufficient extensibility without core patches",
            description="AG2 (9 hooks), LangGraph (callbacks + checkpointer), CrewAI "
                        "(task hooks), OpenHands (event stream) all provide sufficient "
                        "instrumentation points. AG2 is P0 (closest match to forge model), "
                        "LangGraph P1 (biggest impact). Universal ForgeAdapter ABC designed.",
            evidence={
                "ag2_hooks": 9,
                "ag2_priority": "P0",
                "langgraph_priority": "P1",
                "crewai_priority": "P2",
                "openhands_priority": "P3",
                "core_patches_needed": 0,
                "adapter_pattern": "ForgeAdapter ABC",
            },
            verdict="positive", confidence="medium",
            tags=["XARCH-01", "adapter-feasibility"],
            refs=["GPD/phases/08-cross-architecture/08-RESEARCH.md"],
        ),
        Finding(
            phase=0, category="methodology",
            title="Novelty confirmed: no prior work combines typed absence + provenance + compaction",
            description="Three independent literature surveys across 60+ papers confirm: "
                        "no prior work integrates typed absence ontology, structural provenance "
                        "enforcement, and recoverable compaction in a single framework for "
                        "agent runtimes. Components have precedent individually; integration "
                        "is the novel contribution.",
            evidence={
                "papers_surveyed": 60,
                "closest_competitors": [
                    "PROV-AGENT (captures, doesn't enforce)",
                    "AgentSpec (guards actions, not data)",
                    "Knowledge Objects (measures loss, doesn't prevent)",
                    "Kumiho (formal memory, not structural integrity)",
                    "FAME (statistical, not structural protocol)",
                ],
                "novelty_type": "integration",
            },
            verdict="positive", confidence="high",
            tags=["novelty", "literature-survey", "phd-assessment"],
            refs=["Planning phase research agents (3 parallel)"],
        ),
        Finding(
            phase=0, category="methodology",
            title="Current state: ~1/3 of PhD thesis, researcher capable of PhD-level work",
            description="Assessment by PhD committee simulation: exceptional methodology, "
                        "honest negative findings, 537+ tests. Gaps: zero natural violations, "
                        "simulated-only compaction, single runtime, missing theoretical depth "
                        "(no completeness argument, no formal proofs, no database null theory "
                        "engagement). Path requires: Finnish university enrollment, or academic "
                        "collaborator, or workshop paper → industry venue route.",
            evidence={
                "thesis_completion": "33%",
                "strengths": ["methodology", "implementation", "honest negatives"],
                "gaps": ["natural violations", "genuine compaction", "theory", "multi-arch"],
                "test_count": 537,
                "open_theoretical_gaps": [
                    "no composition algebra",
                    "no evaluation logic for absent fields",
                    "no possible-worlds semantics (Libkin)",
                    "runtime-only enforcement",
                ],
                "must_cite_count": 18,
            },
            verdict="partial", confidence="high",
            tags=["phd-assessment", "meta"],
            refs=["PhD study design plan"],
        ),
        Finding(
            phase=0, category="publication",
            title="Publication windows: NeurIPS (5wk), ICSE 2027 (3mo), AAAI 2027 (4mo)",
            description="AGENT 2026, MemAgents, FormaliSE — all closed. "
                        "Actionable: arXiv (immediate), NeurIPS 2026 (May 4-6), "
                        "ICSE 2027 (Jun 23-30), AAAI 2027 (Jul 25 - Aug 1), "
                        "OOPSLA 2027 R1 (~Oct 2026).",
            evidence={
                "closed": ["AGENT 2026", "MemAgents", "FormaliSE 2026", "AAMAS 2026", "OOPSLA 2026 R2"],
                "open": {
                    "arXiv": "always",
                    "NeurIPS 2026": "2026-05-04",
                    "ICSE 2027": "2026-06-23",
                    "AAAI 2027": "2026-07-25",
                    "OOPSLA 2027 R1": "~2026-10",
                },
            },
            verdict="neutral", confidence="high",
            tags=["PAPER-01", "deadlines"],
            refs=["Publication deadline research agent"],
        ),
    ]
    return ledger.record_many(findings)


if __name__ == "__main__":
    ledger = FindingsLedger()
    print("Seeding production findings ledger...")

    v1_records = seed_v1_findings(ledger)
    print(f"  v1.0 baseline: {len(v1_records)} findings")

    v2_records = seed_v2_research_findings(ledger)
    print(f"  v2.0 research: {len(v2_records)} findings")

    summary = ledger.summary()
    print(f"\n  Total: {summary['total']} findings")
    print(f"  Positive: {summary['positive_findings']}")
    print(f"  Negative: {summary['negative_findings']}")
    print(f"  Partial: {summary['by_verdict'].get('partial', 0)}")

    # Export reports
    md_path = str(ledger._data_dir / "findings-report.md")
    ledger.export_markdown(md_path)
    print(f"\n  Markdown report: {md_path}")

    json_path = str(ledger._data_dir / "findings-export.json")
    ledger.export_json(json_path)
    print(f"  JSON export: {json_path}")

    # Show negative findings
    negatives = ledger.query(verdict="negative")
    if negatives:
        print(f"\n  Negative findings ({len(negatives)}):")
        for n in negatives:
            print(f"    {n['id']}: {n['finding']['title']}")
