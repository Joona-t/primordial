"""
Primordial Forge — Stress Test Analyzer

Reads saved summaries from each phase and produces A/B comparison reports.

Usage: python3 stress_analyze.py [phase_number]
       python3 stress_analyze.py           # analyze all phases
       python3 stress_analyze.py 1         # analyze phase 1 only
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from stress_test import analyze_results, print_comparison, PHASES


def analyze_phase(phase_idx: int, phase_dir: Path) -> dict | None:
    """Analyze a single phase if summaries exist."""
    canary_path = phase_dir / "canaries.json"
    raw_summary_path = phase_dir / "summary_raw.txt"
    inst_summary_path = phase_dir / "summary_instrumented.txt"

    if not canary_path.exists():
        print(f"  Phase {phase_idx + 1}: No canary data found, skipping")
        return None

    canaries = json.loads(canary_path.read_text())

    results = {"phase": phase_idx + 1, "name": PHASES[phase_idx]["name"]}

    if raw_summary_path.exists():
        raw_summary = raw_summary_path.read_text()
        results["raw"] = analyze_results(canaries, raw_summary, "raw")
    else:
        print(f"  Phase {phase_idx + 1}: No raw summary yet (save as {raw_summary_path.name})")
        results["raw"] = None

    if inst_summary_path.exists():
        inst_summary = inst_summary_path.read_text()
        results["instrumented"] = analyze_results(canaries, inst_summary, "instrumented")
    else:
        print(f"  Phase {phase_idx + 1}: No instrumented summary yet (save as {inst_summary_path.name})")
        results["instrumented"] = None

    # For multi-hop phases, check for intermediate summaries
    hop_results = []
    for hop in range(1, 10):
        raw_hop = phase_dir / f"summary_raw_hop{hop}.txt"
        inst_hop = phase_dir / f"summary_instrumented_hop{hop}.txt"
        if raw_hop.exists() or inst_hop.exists():
            hop_data = {"hop": hop}
            if raw_hop.exists():
                hop_data["raw"] = analyze_results(canaries, raw_hop.read_text(), f"raw_hop{hop}")
            if inst_hop.exists():
                hop_data["instrumented"] = analyze_results(canaries, inst_hop.read_text(), f"inst_hop{hop}")
            hop_results.append(hop_data)

    if hop_results:
        results["hops"] = hop_results

    return results


def print_phase_report(results: dict):
    """Print report for a single phase."""
    if results["raw"] and results["instrumented"]:
        print_comparison(results["raw"], results["instrumented"], results["name"])
    elif results["raw"]:
        r = results["raw"]
        print(f"\n  Phase {results['phase']}: RAW only (no instrumented summary yet)")
        print(f"    Survived: {r['survived']}/{r['total_canaries']} ({r['survival_rate']:.0%})")
        print(f"    Lost: {r['lost']}")
    elif results["instrumented"]:
        r = results["instrumented"]
        print(f"\n  Phase {results['phase']}: INSTRUMENTED only (no raw summary yet)")
        print(f"    Survived: {r['survived']}/{r['total_canaries']} ({r['survival_rate']:.0%})")
        print(f"    Lost: {r['lost']}")

    # Print hop cascade if available
    if "hops" in results and results["hops"]:
        print(f"\n  ── Cascade Compaction (multi-hop) ──")
        for hop_data in results["hops"]:
            hop = hop_data["hop"]
            for cond in ["raw", "instrumented"]:
                if cond in hop_data:
                    r = hop_data[cond]
                    label = "A" if cond == "raw" else "B"
                    print(f"    Hop {hop} ({label}): {r['survived']}/{r['total_canaries']} survived ({r['survival_rate']:.0%})")


def print_summary_table(all_results: list[dict]):
    """Print overall summary across all phases."""
    print(f"\n{'=' * 80}")
    print(f"  OVERALL A/B SUMMARY")
    print(f"{'=' * 80}")
    print(f"\n  {'Phase':<45} {'A (Raw)':<15} {'B (Inst)':<15} {'Delta'}")
    print(f"  {'─' * 80}")

    for r in all_results:
        if not r:
            continue
        name = r["name"][:44]
        a_rate = f"{r['raw']['survival_rate']:.0%}" if r.get("raw") else "—"
        b_rate = f"{r['instrumented']['survival_rate']:.0%}" if r.get("instrumented") else "—"
        if r.get("raw") and r.get("instrumented"):
            delta = r["instrumented"]["survival_rate"] - r["raw"]["survival_rate"]
            delta_str = f"{delta:+.0%}"
        else:
            delta_str = "—"
        print(f"  {name:<45} {a_rate:<15} {b_rate:<15} {delta_str}")

    # Type breakdown across all phases
    if any(r and r.get("raw") and r.get("instrumented") for r in all_results):
        print(f"\n  ── Type Survival Across All Phases (averaged) ──")
        type_totals_a = {}
        type_totals_b = {}

        for r in all_results:
            if not r or not r.get("raw") or not r.get("instrumented"):
                continue
            for t, data in r["raw"]["by_type"].items():
                type_totals_a.setdefault(t, []).append(data["rate"])
            for t, data in r["instrumented"]["by_type"].items():
                type_totals_b.setdefault(t, []).append(data["rate"])

        all_types = sorted(set(list(type_totals_a.keys()) + list(type_totals_b.keys())))
        for t in all_types:
            a_avg = sum(type_totals_a.get(t, [0])) / max(len(type_totals_a.get(t, [1])), 1)
            b_avg = sum(type_totals_b.get(t, [0])) / max(len(type_totals_b.get(t, [1])), 1)
            delta = b_avg - a_avg
            print(f"    {t:<16} A: {a_avg:.0%}   B: {b_avg:.0%}   {delta:+.0%}")

    print(f"\n{'=' * 80}")


def main():
    data_dir = Path(__file__).parent / "stress_data"

    if not data_dir.exists():
        print("ERROR: Run stress_test.py first to generate phase data")
        sys.exit(1)

    # Parse args
    target_phase = None
    if len(sys.argv) > 1:
        target_phase = int(sys.argv[1]) - 1

    all_results = []
    for i in range(len(PHASES)):
        if target_phase is not None and i != target_phase:
            continue

        phase_dir = data_dir / f"phase_{i + 1}"
        if not phase_dir.exists():
            continue

        result = analyze_phase(i, phase_dir)
        if result:
            print_phase_report(result)
            all_results.append(result)

            # Save phase report
            report_path = phase_dir / "report.json"
            # Strip details for summary (too large)
            save_result = {k: v for k, v in result.items() if k != "details"}
            if result.get("raw"):
                save_result["raw"] = {k: v for k, v in result["raw"].items() if k != "details"}
            if result.get("instrumented"):
                save_result["instrumented"] = {k: v for k, v in result["instrumented"].items() if k != "details"}
            report_path.write_text(json.dumps(save_result, indent=2, default=str))

    if len(all_results) > 1:
        print_summary_table(all_results)

    # Save overall report
    if all_results:
        overall_path = data_dir / "overall_report.json"
        overall = []
        for r in all_results:
            entry = {"phase": r["phase"], "name": r["name"]}
            for cond in ["raw", "instrumented"]:
                if r.get(cond):
                    entry[cond] = {k: v for k, v in r[cond].items() if k != "details"}
            overall.append(entry)
        overall_path.write_text(json.dumps(overall, indent=2, default=str))
        print(f"\n  Reports saved to: {data_dir}")


if __name__ == "__main__":
    main()
