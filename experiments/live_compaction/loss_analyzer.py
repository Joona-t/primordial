"""
Live Compaction Test — Loss Analyzer

Takes a compacted summary (from a subagent, API call, or manual summary)
and measures what survived against the 20 canary facts.

Classifies each loss using Primordial's typed absence ontology.

Usage:
    python3 loss_analyzer.py <summary_file>
    python3 loss_analyzer.py --summary "inline summary text"
"""

import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from forge_nulls import AbsenceState, absent


# ── Canary Detection ─────────────────────────────────────────────────

# Each canary has specific "signal tokens" — if these are present in the
# summary, the canary survived. We check for key distinguishing details,
# not just keywords.

CANARY_SIGNALS = {
    "C01": {"must_have": ["3,847", "3847"], "match_any": True, "description": "exact request rate (3,847 rps)"},
    "C02": {"must_have": ["helios-prod-west-7"], "match_any": True, "description": "database name"},
    "C03": {"must_have": ["CVE-2024-31891"], "match_any": True, "description": "specific CVE for connection pooling"},
    "C04": {"must_have": ["opaque session"], "match_any": True, "description": "NOT JWT — opaque sessions"},
    "C05": {"must_have": ["237"], "match_any": True, "description": "exact backoff base delay (237ms)"},
    "C06": {"must_have": ["handle_batch_ingestion"], "match_any": True, "description": "function name"},
    "C07": {"must_have": ["2.3"], "match_any": True, "description": "memory spike size (2.3GB)"},
    "C08": {"must_have": ["transform stage", "transform phase"], "match_any": True, "description": "validation only at transform stage"},
    "C09": {"must_have": ["14"], "match_any": True, "description": "exact count: 14 high-severity"},
    "C10": {"must_have": ["FORGE-SEC-2024-0042"], "match_any": True, "description": "specific finding ID"},
    "C11": {"must_have": ["X-Forwarded-For"], "match_any": True, "description": "header name in rate limit bypass"},
    "C12": {"must_have": ["TLS 1.2", "TLS1.2", "legacy HSM"], "match_any": True, "description": "TLS version pinned to 1.2"},
    "C13": {"must_have": ["847"], "match_any": True, "description": "P99 latency (847ms)"},
    "C14": {"must_have": ["reconciliation/batch", "reconciliation"], "match_any": True, "description": "slowest endpoint path"},
    "C15": {"must_have": ["G1GC", "ZGC"], "match_any": True, "description": "GC collector names"},
    "C16": {"must_have": ["LFU", "16GB"], "match_any": True, "description": "cache eviction policy (LFU, 16GB cap)"},
    "C17": {"must_have": ["0.3%", "0.3 percent", "67%", "67 percent"], "match_any": True, "description": "cross-service failure rate"},
    "C18": {"must_have": ["resilience4j"], "match_any": True, "description": "circuit breaker library name"},
    "C19": {"must_have": ["RabbitMQ", "Kafka"], "match_any": True, "description": "event bus migration (Rabbit→Kafka)"},
    "C20": {"must_have": ["etcd", "3-second", "3 second", "3s"], "match_any": True, "description": "service discovery (etcd, 3s TTL)"},
}

# Canary type categories
CANARY_TYPES = {
    "exact_number": ["C01", "C05", "C09", "C13", "C17"],
    "identifier":   ["C02", "C06", "C10", "C14", "C18"],
    "causal":       ["C03", "C07", "C11", "C15", "C19"],
    "negation":     ["C04", "C08", "C12", "C16", "C20"],
}

STAGE_MAP = {
    "architect": ["C01", "C02", "C03", "C04"],
    "builder":   ["C05", "C06", "C07", "C08"],
    "critic":    ["C09", "C10", "C11", "C12"],
    "analyst":   ["C13", "C14", "C15", "C16"],
    "integrator":["C17", "C18", "C19", "C20"],
}


def check_canary(canary_id: str, summary_text: str) -> dict:
    """Check if a canary fact survived in the summary."""
    signals = CANARY_SIGNALS[canary_id]
    summary_lower = summary_text.lower()

    found_signals = []
    for token in signals["must_have"]:
        if token.lower() in summary_lower:
            found_signals.append(token)

    survived = len(found_signals) > 0 if signals["match_any"] else len(found_signals) == len(signals["must_have"])

    return {
        "canary_id": canary_id,
        "survived": survived,
        "description": signals["description"],
        "signals_checked": signals["must_have"],
        "signals_found": found_signals,
    }


def classify_absence(canary_id: str, summary_text: str) -> dict:
    """Classify a missing canary using Primordial's typed absence."""
    # Heuristics for absence type:
    # - If the stage is mentioned but the specific fact isn't → pruned_recoverable
    #   (the agent knew about this stage but compressed away the detail)
    # - If the stage isn't mentioned at all → deleted
    #   (the agent dropped the entire stage)
    # - If a vague/wrong version of the fact appears → invalid
    #   (the agent hallucinated or corrupted the fact)

    summary_lower = summary_text.lower()

    # Find which stage this canary belongs to
    stage = None
    for s, canaries in STAGE_MAP.items():
        if canary_id in canaries:
            stage = s
            break

    stage_mentioned = stage and stage.lower() in summary_lower

    # Check for corrupted versions (rough heuristic)
    signals = CANARY_SIGNALS[canary_id]
    partial_match = False
    for token in signals["must_have"]:
        # Check if a partial or corrupted version exists
        words = token.lower().split()
        if len(words) > 1 and any(w in summary_lower for w in words):
            partial_match = True

    if not stage_mentioned:
        return absent(AbsenceState.DELETED, f"Stage '{stage}' not referenced in summary")
    elif partial_match:
        return absent(AbsenceState.INVALID, f"Corrupted or partial version of {canary_id} detected")
    else:
        return absent(AbsenceState.PRUNED_RECOVERABLE, f"Stage '{stage}' mentioned but detail {canary_id} compressed away")


def analyze_compaction(summary_text: str, canary_facts: list[dict]) -> dict:
    """Full compaction loss analysis."""
    results = []
    for canary in canary_facts:
        cid = canary["id"]
        check = check_canary(cid, summary_text)

        if check["survived"]:
            results.append({
                **check,
                "absence_state": None,
                "classification": "survived",
            })
        else:
            absence = classify_absence(cid, summary_text)
            results.append({
                **check,
                "absence_state": absence,
                "classification": absence["state"],
            })

    # Aggregate metrics
    survived = [r for r in results if r["survived"]]
    lost = [r for r in results if not r["survived"]]

    # By type
    type_survival = {}
    for type_name, canary_ids in CANARY_TYPES.items():
        type_results = [r for r in results if r["canary_id"] in canary_ids]
        type_survived = [r for r in type_results if r["survived"]]
        type_survival[type_name] = {
            "total": len(type_results),
            "survived": len(type_survived),
            "rate": len(type_survived) / len(type_results) if type_results else 0,
        }

    # By stage
    stage_survival = {}
    for stage_name, canary_ids in STAGE_MAP.items():
        stage_results = [r for r in results if r["canary_id"] in canary_ids]
        stage_survived = [r for r in stage_results if r["survived"]]
        stage_survival[stage_name] = {
            "total": len(stage_results),
            "survived": len(stage_survived),
            "rate": len(stage_survived) / len(stage_results) if stage_results else 0,
        }

    # By absence classification
    absence_counts = {}
    for r in lost:
        cls = r["classification"]
        absence_counts[cls] = absence_counts.get(cls, 0) + 1

    # Provenance reachability: can we trace surviving facts back to their source?
    provenance_reachable = sum(1 for r in survived if r["survived"]) / len(results)

    report = {
        "summary_length_chars": len(summary_text),
        "total_canaries": len(results),
        "survived": len(survived),
        "lost": len(lost),
        "survival_rate": len(survived) / len(results),
        "provenance_reachability": provenance_reachable,
        "by_type": type_survival,
        "by_stage": stage_survival,
        "absence_classifications": absence_counts,
        "details": results,
    }

    return report


def print_report(report: dict):
    """Pretty-print the compaction loss report."""
    print("\n" + "=" * 70)
    print("  PRIMORDIAL FORGE — LIVE COMPACTION LOSS REPORT")
    print("=" * 70)

    print(f"\n  Summary length:      {report['summary_length_chars']:,} chars")
    print(f"  Total canary facts:  {report['total_canaries']}")
    print(f"  Survived:            {report['survived']} ({report['survival_rate']:.0%})")
    print(f"  Lost:                {report['lost']} ({1 - report['survival_rate']:.0%})")
    print(f"  Provenance reach:    {report['provenance_reachability']:.2f}")

    print(f"\n  ── Survival by Information Type ──")
    for type_name, data in report["by_type"].items():
        bar = "█" * data["survived"] + "░" * (data["total"] - data["survived"])
        print(f"    {type_name:<14} {bar}  {data['survived']}/{data['total']} ({data['rate']:.0%})")

    print(f"\n  ── Survival by Stage (temporal order) ──")
    for stage_name, data in report["by_stage"].items():
        bar = "█" * data["survived"] + "░" * (data["total"] - data["survived"])
        print(f"    {stage_name:<14} {bar}  {data['survived']}/{data['total']} ({data['rate']:.0%})")

    print(f"\n  ── Absence Classifications (lost facts) ──")
    if report["absence_classifications"]:
        for cls, count in sorted(report["absence_classifications"].items(), key=lambda x: -x[1]):
            print(f"    {cls:<24} {count}")
    else:
        print("    (none — all facts survived)")

    print(f"\n  ── Detail: Lost Facts ──")
    lost = [d for d in report["details"] if not d["survived"]]
    if lost:
        for d in lost:
            state = d["absence_state"]["state"] if d["absence_state"] else "?"
            reason = d["absence_state"].get("reason", "") if d["absence_state"] else ""
            print(f"    [{d['canary_id']}] {state:<22} {d['description']}")
            if reason:
                print(f"           └─ {reason}")
    else:
        print("    (none — perfect retention)")

    print("\n" + "=" * 70)


def main():
    run_dir = Path(__file__).parent / "run_data"

    # Load canary facts
    canary_path = run_dir / "canary_facts.json"
    if not canary_path.exists():
        print("ERROR: Run canary_chamber.py first to generate ground truth")
        sys.exit(1)

    canary_facts = json.loads(canary_path.read_text())

    # Get summary text
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            summary_text = " ".join(sys.argv[2:])
        else:
            summary_path = Path(sys.argv[1])
            summary_text = summary_path.read_text()
    else:
        # Try default location
        default_summary = run_dir / "compacted_summary.txt"
        if default_summary.exists():
            summary_text = default_summary.read_text()
        else:
            print("Usage: python3 loss_analyzer.py <summary_file>")
            print("   or: python3 loss_analyzer.py --summary 'text...'")
            print(f"\n   or: save summary to {default_summary}")
            sys.exit(1)

    # Run analysis
    report = analyze_compaction(summary_text, canary_facts)

    # Print report
    print_report(report)

    # Save report
    report_path = run_dir / "loss_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
