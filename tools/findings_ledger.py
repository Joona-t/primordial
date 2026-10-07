"""Findings Ledger — structured research log for Primordial Computing v2.0.

Every experiment result, decision, observation, and negative finding gets
recorded here with full evidence chains. This is the single source of truth
for all research outcomes.

Storage: JSONL at data/findings/findings.jsonl
Each line is one finding with: id, timestamp, phase, category, title,
description, evidence, verdict, confidence, refs, tags.

Usage:
    ledger = FindingsLedger()
    ledger.record(Finding(
        phase=6,
        category="compaction",
        title="Artifact ID survival at 80K threshold",
        description="3/5 forge artifact IDs survived genuine compaction...",
        evidence={"artifact_ids_before": 5, "artifact_ids_after": 3, ...},
        verdict="partial",
        confidence="high",
        tags=["COMP-04", "SPF-01"],
    ))

    # Query
    findings = ledger.query(phase=6, category="compaction")
    negative = ledger.query(verdict="negative")

    # Export
    ledger.export_markdown("findings-report.md")
    ledger.summary()
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# --- Finding Data Model ---

CATEGORIES = [
    "compaction",       # RQ3b — genuine compaction results
    "violation",        # RQ2b — natural/injected violation detection
    "architecture",     # RQ4 — cross-architecture adapter results
    "ontology",         # RQ1 — absence ontology findings
    "methodology",      # Research methodology observations
    "spf",              # Semantic Provenance Fidelity measurements
    "publication",      # Publication-related decisions/outcomes
    "negative",         # Explicitly negative findings (important!)
    "decision",         # Research decisions with rationale
    "baseline",         # Baseline measurements
]

VERDICTS = [
    "positive",         # Finding supports the hypothesis
    "negative",         # Finding contradicts or fails to support
    "partial",          # Mixed or incomplete evidence
    "neutral",          # Informational, no directional implication
    "pending",          # Awaiting further analysis
]

CONFIDENCE = ["high", "medium", "low"]


@dataclass
class Finding:
    """A single research finding."""
    phase: int
    category: str
    title: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    verdict: str = "pending"
    confidence: str = "medium"
    refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    rq: str | None = None  # Which research question this addresses

    def validate(self):
        """Validate finding fields."""
        if self.category not in CATEGORIES:
            raise ValueError(f"Unknown category '{self.category}'. Valid: {CATEGORIES}")
        if self.verdict not in VERDICTS:
            raise ValueError(f"Unknown verdict '{self.verdict}'. Valid: {VERDICTS}")
        if self.confidence not in CONFIDENCE:
            raise ValueError(f"Unknown confidence '{self.confidence}'. Valid: {CONFIDENCE}")
        if not self.title:
            raise ValueError("Finding must have a title")
        if not self.description:
            raise ValueError("Finding must have a description")


@dataclass
class FindingRecord:
    """A finding with metadata (as stored in the ledger)."""
    id: str
    timestamp: str
    finding: dict
    content_hash: str

    @staticmethod
    def from_finding(finding: Finding, seq: int) -> "FindingRecord":
        finding.validate()
        finding_dict = asdict(finding)
        ts = datetime.now(timezone.utc).isoformat()
        fid = f"F-{seq:04d}"
        content = json.dumps(finding_dict, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return FindingRecord(
            id=fid,
            timestamp=ts,
            finding=finding_dict,
            content_hash=content_hash,
        )


# --- Ledger ---

class FindingsLedger:
    """JSONL-backed research findings ledger."""

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            # Default: relative to this file's project root
            tools_dir = Path(__file__).parent
            data_dir = tools_dir.parent / "data" / "findings"
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._data_dir / "findings.jsonl"
        self._next_seq = self._compute_next_seq()

    def _compute_next_seq(self) -> int:
        """Find the next sequence number from existing records."""
        if not self._ledger_path.exists():
            return 1
        max_seq = 0
        for line in self._ledger_path.read_text().strip().split("\n"):
            if not line:
                continue
            record = json.loads(line)
            fid = record.get("id", "F-0000")
            try:
                seq = int(fid.split("-")[1])
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                pass
        return max_seq + 1

    def record(self, finding: Finding) -> FindingRecord:
        """Record a finding to the ledger. Returns the stored record."""
        record = FindingRecord.from_finding(finding, self._next_seq)
        self._next_seq += 1

        with open(self._ledger_path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

        return record

    def record_many(self, findings: list[Finding]) -> list[FindingRecord]:
        """Record multiple findings atomically."""
        return [self.record(f) for f in findings]

    def all_records(self) -> list[dict]:
        """Load all records from the ledger."""
        if not self._ledger_path.exists():
            return []
        records = []
        for line in self._ledger_path.read_text().strip().split("\n"):
            if line:
                records.append(json.loads(line))
        return records

    def query(self, **kwargs) -> list[dict]:
        """Query findings by field values.

        Supports:
            phase=6, category="compaction", verdict="negative",
            tag="COMP-04", rq="RQ3b", confidence="high"
        """
        records = self.all_records()
        results = []
        for rec in records:
            finding = rec["finding"]
            match = True
            for key, value in kwargs.items():
                if key == "tag":
                    if value not in finding.get("tags", []):
                        match = False
                elif key == "min_phase":
                    if finding.get("phase", 0) < value:
                        match = False
                elif key == "max_phase":
                    if finding.get("phase", 0) > value:
                        match = False
                else:
                    if finding.get(key) != value:
                        match = False
            if match:
                results.append(rec)
        return results

    def count(self, **kwargs) -> int:
        """Count findings matching query."""
        return len(self.query(**kwargs))

    def summary(self) -> dict:
        """Generate summary statistics."""
        records = self.all_records()
        if not records:
            return {"total": 0}

        by_category = {}
        by_verdict = {}
        by_phase = {}
        by_rq = {}
        by_confidence = {}

        for rec in records:
            f = rec["finding"]
            cat = f.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            verd = f.get("verdict", "unknown")
            by_verdict[verd] = by_verdict.get(verd, 0) + 1
            phase = f.get("phase", 0)
            by_phase[phase] = by_phase.get(phase, 0) + 1
            rq = f.get("rq")
            if rq:
                by_rq[rq] = by_rq.get(rq, 0) + 1
            conf = f.get("confidence", "unknown")
            by_confidence[conf] = by_confidence.get(conf, 0) + 1

        return {
            "total": len(records),
            "by_category": by_category,
            "by_verdict": by_verdict,
            "by_phase": by_phase,
            "by_rq": by_rq,
            "by_confidence": by_confidence,
            "negative_findings": self.count(verdict="negative"),
            "positive_findings": self.count(verdict="positive"),
        }

    def export_markdown(self, output_path: str | None = None) -> str:
        """Export all findings as a markdown report."""
        records = self.all_records()
        lines = [
            "# Research Findings Ledger",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Total findings:** {len(records)}",
            "",
        ]

        # Summary table
        summary = self.summary()
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total findings | {summary['total']} |")
        lines.append(f"| Positive | {summary['positive_findings']} |")
        lines.append(f"| Negative | {summary['negative_findings']} |")
        for cat, count in sorted(summary.get("by_category", {}).items()):
            lines.append(f"| Category: {cat} | {count} |")
        lines.append("")

        # Findings by phase
        phases = sorted(set(r["finding"].get("phase", 0) for r in records))
        for phase in phases:
            phase_records = [r for r in records if r["finding"].get("phase") == phase]
            lines.append(f"## Phase {phase} ({len(phase_records)} findings)")
            lines.append("")
            lines.append("| ID | Category | Title | Verdict | Confidence |")
            lines.append("|----|----------|-------|---------|------------|")
            for rec in phase_records:
                f = rec["finding"]
                lines.append(
                    f"| {rec['id']} | {f['category']} | {f['title']} "
                    f"| {f['verdict']} | {f['confidence']} |"
                )
            lines.append("")

            # Detail for each finding
            for rec in phase_records:
                f = rec["finding"]
                lines.append(f"### {rec['id']}: {f['title']}")
                lines.append("")
                lines.append(f"**Category:** {f['category']} | "
                             f"**Verdict:** {f['verdict']} | "
                             f"**Confidence:** {f['confidence']}")
                if f.get("rq"):
                    lines.append(f"**Research Question:** {f['rq']}")
                lines.append(f"**Timestamp:** {rec['timestamp']}")
                lines.append("")
                lines.append(f"{f['description']}")
                lines.append("")
                if f.get("evidence"):
                    lines.append("**Evidence:**")
                    lines.append(f"```json\n{json.dumps(f['evidence'], indent=2)}\n```")
                    lines.append("")
                if f.get("tags"):
                    lines.append(f"**Tags:** {', '.join(f['tags'])}")
                if f.get("refs"):
                    lines.append(f"**References:** {', '.join(f['refs'])}")
                lines.append("")
                lines.append("---")
                lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w") as out:
                out.write(report)

        return report

    def export_json(self, output_path: str | None = None) -> dict:
        """Export as structured JSON with summary + all records."""
        result = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "summary": self.summary(),
            "findings": self.all_records(),
        }
        if output_path:
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
        return result


# --- Convenience: record v1.0 baseline findings ---

def seed_v1_findings(ledger: FindingsLedger) -> list[FindingRecord]:
    """Seed the ledger with v1.0 baseline findings for continuity."""
    findings = [
        Finding(
            phase=1, category="ontology", rq="RQ1",
            title="8-state absence ontology formalized and verified",
            description="64-entry transition table (45 legal, 19 illegal). "
                        "300K+ adversarial Hypothesis transitions with 0 violations. "
                        "99% mutation score (103/104 non-equivalent killed).",
            evidence={
                "states": 8, "transitions": 64, "legal": 45, "illegal": 19,
                "adversarial_transitions": 300000, "violations": 0,
                "mutation_score": 0.99, "mutants_killed": 103, "mutants_total": 104,
            },
            verdict="positive", confidence="high",
            tags=["RQ1", "FORM-01", "FORM-02"], refs=["Phase 1 Plans 01-02"],
        ),
        Finding(
            phase=3, category="violation", rq="RQ2",
            title="Violation detection: 44.4% on injected faults, 0% FPR",
            description="4/9 fault types detected at 100% (D1, D2, D5, D9). "
                        "Aggregate: 40/90 = 44.4% [CI: 0.344-0.544]. "
                        "Differential: +0.444 vs uninstrumented. FPR = 0.0%.",
            evidence={
                "types_detected": ["D1", "D2", "D5", "D9"],
                "types_missed": ["D3", "D4", "D6", "D7", "D8"],
                "aggregate_rate": 0.444, "ci_lower": 0.344, "ci_upper": 0.544,
                "fpr": 0.0, "injections": 90, "detections": 40,
            },
            verdict="partial", confidence="high",
            tags=["RQ2", "VIOL-01", "VIOL-02"], refs=["Phase 3 Plan 02"],
        ),
        Finding(
            phase=3, category="negative", rq="RQ2",
            title="NEGATIVE: Zero natural violations in 30 runs",
            description="0/30 clean runs detected natural structural violations. "
                        "Clopper-Pearson 95% upper bound: 11.6%. "
                        "Mechanism validated on injected faults but practical value "
                        "on naturally-occurring failures is undemonstrated.",
            evidence={
                "runs": 30, "natural_violations": 0,
                "cp_upper_95": 0.116, "cp_lower_95": 0.0,
                "workload": "coding/patching tasks",
                "power_at_5pct": 0.785, "power_at_2pct": 0.455,
            },
            verdict="negative", confidence="high",
            tags=["RQ2", "VIOL-03", "negative-finding"],
            refs=["Phase 3 Plan 02", "Cross-reference report Section 3"],
        ),
        Finding(
            phase=4, category="compaction", rq="RQ3",
            title="Simulated compaction: reachability 0.93→0.25 over 10-90% deletion",
            description="Structural reachability degrades monotonically. "
                        "Backtracking threshold at 80% deletion. "
                        "Pre-compaction reachability 1.0 matches MockLM ceiling. "
                        "SIMULATED ONLY — genuine LLM compaction untested.",
            evidence={
                "type": "simulated_deletion",
                "reachability_10pct": 0.932, "reachability_50pct": 0.821,
                "reachability_80pct": 0.438, "reachability_90pct": 0.250,
                "backtracking_threshold": 0.80,
                "pre_compaction": 1.0, "mockml_ceiling": 1.0,
                "violation_regression": "D1/D2/D5/D9 at 100% post-compaction",
            },
            verdict="partial", confidence="medium",
            tags=["RQ3", "COMP-02", "simulated-only"],
            refs=["Phase 4 Plan 02"],
        ),
        Finding(
            phase=5, category="methodology",
            title="v1.0 synthesis: RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL",
            description="All 4 automated consistency checks pass. "
                        "62 programmatic cross-reference checks green. "
                        "No stop/rethink conditions triggered. "
                        "Compaction inconclusive (simulated only).",
            evidence={
                "rq1": "PASS", "rq2": "PARTIAL", "rq3": "PARTIAL",
                "consistency_checks": 4, "consistency_pass": 4,
                "xref_checks": 62, "xref_pass": 62,
                "total_tests": 492,
            },
            verdict="partial", confidence="high",
            tags=["synthesis", "v1.0-complete"],
            refs=["docs/cross-reference-report.md"],
        ),
    ]
    return ledger.record_many(findings)


if __name__ == "__main__":
    import tempfile

    # Demo with temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = FindingsLedger(data_dir=tmpdir)

        # Seed v1.0 findings
        records = seed_v1_findings(ledger)
        print(f"Seeded {len(records)} v1.0 findings")

        # Record a new v2.0 finding
        new = ledger.record(Finding(
            phase=6, category="compaction", rq="RQ3b",
            title="compact_20260112 API provides full boundary observability",
            description="Anthropic's compaction API with pause_after_compaction=true "
                        "returns stop_reason='compaction' with exact boundary capture. "
                        "Min trigger: 50K tokens. This enables controlled genuine "
                        "compaction experiments.",
            evidence={"api": "compact_20260112", "min_tokens": 50000, "default": 150000},
            verdict="positive", confidence="high",
            tags=["COMP-04", "breakthrough"], refs=["Phase 6 Research"],
        ))
        print(f"Recorded: {new.id}")

        # Summary
        summary = ledger.summary()
        print(f"\nTotal findings: {summary['total']}")
        print(f"Positive: {summary['positive_findings']}")
        print(f"Negative: {summary['negative_findings']}")
        print(f"By category: {summary['by_category']}")
        print(f"By verdict: {summary['by_verdict']}")

        # Query
        negatives = ledger.query(verdict="negative")
        print(f"\nNegative findings: {len(negatives)}")
        for n in negatives:
            print(f"  {n['id']}: {n['finding']['title']}")

        # Export markdown
        report = ledger.export_markdown()
        print(f"\nMarkdown report: {len(report)} chars")
        print(report[:500])
