#!/usr/bin/env python3
"""
run_campaign.py -- Execute the Phase 3 violation detection campaign.

Runs:
1. D1-D9 fault injection campaign (90 injections, 10 per type)
2. Clean campaign (30 runs for FPR measurement and natural violation detection)
3. Computes detection rates with proper CIs
4. Generates machine-readable campaign report

Convention compliance:
  - All metrics dimensionless ratios in [0,1] or counts >= 0
  - CI method: bootstrap 95% (B=10000, seed=42) for N >= 5,
    Clopper-Pearson exact binomial for proportions at 0/n or n/n
  - "Compaction" always qualified per Convention #6
  - Injected and natural detections STRICTLY SEPARATED (fp-synthetic-only)

Seed: 42 (reproducible)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure tools/ is importable
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from detection_campaign import DetectionCampaign
from fault_injector import FAULT_TYPES, FAULT_DESCRIPTIONS, MOCKLM_DETECTION


def main():
    project_root = Path(__file__).parent.parent
    ledger_path = str(project_root / "integration_samples" / "openclaw" / "queue_ledger.sample.jsonl")
    campaign_dir = project_root / "data" / "campaign"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("Phase 3 Violation Detection Campaign")
    print("=" * 72)

    # --- 1. Initialize campaign ---
    print("\n[1/6] Initializing campaign (seed=42, n_injections_per_type=10)...")
    campaign = DetectionCampaign(
        ledger_path=ledger_path,
        seed=42,
        n_injections_per_type=10,
    )

    # --- 2. Schedule injections ---
    print("[2/6] Scheduling D1-D9 injections...")
    schedule = campaign.schedule_injections()
    print(f"  Scheduled {len(schedule)} injections across {len(FAULT_TYPES)} fault types")

    # Verify injection count
    type_counts = {}
    for spec in schedule:
        type_counts[spec.fault_type] = type_counts.get(spec.fault_type, 0) + 1
    print("  Per-type counts:")
    for ft in FAULT_TYPES:
        count = type_counts.get(ft, 0)
        print(f"    {ft}: {count} injections")
    assert len(schedule) == 90, f"Expected 90 injections, got {len(schedule)}"
    for ft in FAULT_TYPES:
        assert type_counts.get(ft, 0) == 10, f"Expected 10 injections for {ft}, got {type_counts.get(ft, 0)}"

    # --- 3. Run full campaign (injection + clean) ---
    print("\n[3/6] Running full campaign (injection + clean runs)...")
    t0 = time.time()
    report = campaign.run_full_campaign(dry_run=False, n_clean_runs=30)
    elapsed = time.time() - t0
    print(f"  Campaign completed in {elapsed:.1f}s")

    # --- 4. Extract injection results ---
    print("\n[4/6] Analyzing injection results...")
    injection_summary = report["injection_summary"]
    detection_rates = injection_summary["detection_rates"]
    total_injections = injection_summary["total_injections"]
    print(f"  Total injections executed: {total_injections}")

    # Per-type results table
    print("\n  D1-D9 Detection Rates (Forge Tier):")
    print(f"  {'Type':<6} {'Rate':<10} {'CI 95%':<20} {'Method':<16} {'Description'}")
    print(f"  {'-'*5:<6} {'-'*9:<10} {'-'*19:<20} {'-'*15:<16} {'-'*30}")
    for ft in FAULT_TYPES:
        per_type = detection_rates["per_type"].get(ft, {})
        forge = per_type.get("forge", {})
        rate = forge.get("rate", 0.0)
        ci = forge.get("ci_95", [0.0, 0.0])
        method = forge.get("ci_method", "N/A")
        desc = FAULT_DESCRIPTIONS.get(ft, "")[:40]
        print(f"  {ft:<6} {rate:.2f}      [{ci[0]:.3f}, {ci[1]:.3f}]     {method:<16} {desc}")

    # Aggregate rates per tier
    aggregate = detection_rates.get("aggregate", {})
    print("\n  Aggregate Detection Rates:")
    for tier in ["uninstrumented", "structured", "forge"]:
        tier_data = aggregate.get(tier, {})
        rate = tier_data.get("rate", 0.0)
        ci = tier_data.get("ci_95", [0.0, 0.0])
        method = tier_data.get("ci_method", "N/A")
        print(f"    {tier:<20} rate={rate:.4f}  CI=[{ci[0]:.4f}, {ci[1]:.4f}]  method={method}")

    # Three-tier ordering verification
    print("\n  Three-tier ordering verification (per fault type):")
    ordering_holds = True
    for ft in FAULT_TYPES:
        per_type = detection_rates["per_type"].get(ft, {})
        u_rate = per_type.get("uninstrumented", {}).get("rate", 0.0)
        s_rate = per_type.get("structured", {}).get("rate", 0.0)
        f_rate = per_type.get("forge", {}).get("rate", 0.0)
        ok = f_rate >= s_rate >= u_rate
        status = "OK" if ok else "VIOLATION"
        if not ok:
            ordering_holds = False
        print(f"    {ft}: forge={f_rate:.2f} >= structured={s_rate:.2f} >= uninstrumented={u_rate:.2f}  [{status}]")
    print(f"  Overall ordering: {'HOLDS' if ordering_holds else 'VIOLATED'}")

    # Differentials
    diffs = detection_rates.get("differentials", {})
    print(f"\n  Differentials:")
    print(f"    delta(forge - uninstrumented) = {diffs.get('delta_forge_uninstrumented', 0.0):.4f}")
    print(f"    delta(forge - structured)     = {diffs.get('delta_forge_structured', 0.0):.4f}")

    # --- 5. Clean campaign results ---
    print("\n[5/6] Clean campaign results...")
    clean_summary = report.get("clean_summary", {})
    n_clean = clean_summary.get("n_runs", 0)
    fpr = clean_summary.get("false_positive_rate", 0.0)
    fpr_ci = clean_summary.get("fpr_ci_95", [0.0, 0.0])
    fpr_method = clean_summary.get("fpr_ci_method", "N/A")
    fpr_warn = clean_summary.get("fpr_warning")
    natural_candidates = clean_summary.get("natural_violation_candidates", [])

    print(f"  Clean runs: {n_clean}")
    print(f"  Total errors on clean data: {clean_summary.get('total_errors', 0)}")
    print(f"  False positive rate: {fpr:.4f}  CI=[{fpr_ci[0]:.4f}, {fpr_ci[1]:.4f}]  method={fpr_method}")
    if fpr_warn:
        print(f"  WARNING: {fpr_warn}")

    # Natural violation assessment
    print(f"\n  Natural violation candidates: {len(natural_candidates)}")
    if natural_candidates:
        for i, candidate in enumerate(natural_candidates):
            print(f"    Candidate {i+1}: code={candidate.get('code','?')} message={candidate.get('message','?')[:60]}")
    else:
        # Clopper-Pearson upper bound for 0/N
        from fault_injector import clopper_pearson_ci
        _, cp_upper = clopper_pearson_ci(0, n_clean)
        print(f"  Zero natural violations detected after {n_clean} clean runs.")
        print(f"  Clopper-Pearson 95% upper bound on natural violation rate: {cp_upper:.4f} ({cp_upper*100:.1f}%)")

    # Separated counts
    separated = report.get("separated", {})
    print(f"\n  Separation (fp-synthetic-only enforcement):")
    print(f"    Injected detections: {separated.get('injected_detections_count', 0)}")
    print(f"    Natural detections:  {separated.get('natural_detections_count', 0)}")

    # --- 6. Anchor comparison ---
    print("\n[6/6] Anchor comparison (MockLM ceiling)...")
    anchor = report.get("anchor_comparison", {})
    print(f"  MockLM ceiling: {anchor.get('mocklm_ceiling', 'N/A')}")
    print(f"  D1-D6 aggregate rate (forge): {anchor.get('d1_d6_aggregate_rate', 0.0):.4f} ({anchor.get('d1_d6_aggregate', 'N/A')})")
    print(f"  D1-D6 match: {anchor.get('d1_d6_aggregate_rate', 0.0) == 1.0}")

    gap = anchor.get("gap_analysis")
    if gap:
        print(f"  Gap identified: missed types = {gap.get('missed_types', [])}")
        print(f"  Explanation: {gap.get('explanation', '')[:100]}...")

    d1_d6_per_type = anchor.get("d1_d6_per_type", {})
    print("\n  D1-D6 per-type comparison:")
    print(f"  {'Type':<6} {'Forge Rate':<12} {'Detected/Total':<16} {'MockLM Expected'}")
    for ft in ["D1", "D2", "D3", "D4", "D5", "D6"]:
        d = d1_d6_per_type.get(ft, {})
        print(f"  {ft:<6} {d.get('rate', 0.0):<12.2f} {d.get('detected',0)}/{d.get('total',0):<12} {d.get('mocklm_expected','N/A')}")

    # D7-D9 new findings
    d7_d9 = report.get("d7_d9_new_findings", {})
    print("\n  D7-D9 new findings:")
    for ft in ["D7", "D8", "D9"]:
        d = d7_d9.get(ft, {})
        forge = d.get("forge", {})
        rate = forge.get("rate", 0.0)
        detected = forge.get("detected", 0)
        total = forge.get("total", 0)
        status = "DETECTED" if rate > 0 else "GAP"
        print(f"  {ft}: rate={rate:.2f} ({detected}/{total})  [{status}]")

    # --- Save results ---
    print("\n" + "=" * 72)
    print("Saving results...")

    # Save injection results (individual injection records)
    injection_results_data = []
    for r in campaign._injection_results:
        injection_results_data.append(r.to_dict())
    injection_path = campaign_dir / "injection-results.json"
    with open(injection_path, "w") as f:
        json.dump({
            "metadata": {
                "seed": 42,
                "n_injections_per_type": 10,
                "total_injections": len(injection_results_data),
                "fault_types": FAULT_TYPES,
                "data_source": ledger_path,
            },
            "results": injection_results_data,
        }, f, indent=2, default=str)
    print(f"  Injection results: {injection_path}")

    # Save clean results
    clean_path = campaign_dir / "clean-results.json"
    with open(clean_path, "w") as f:
        json.dump({
            "metadata": {
                "seed": 42,
                "n_clean_runs": n_clean,
                "data_source": ledger_path,
            },
            "results": clean_summary,
        }, f, indent=2, default=str)
    print(f"  Clean results: {clean_path}")

    # Save full campaign report
    report_path = campaign_dir / "campaign-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Campaign report: {report_path}")

    print("\n" + "=" * 72)
    print("Campaign complete.")
    print("=" * 72)

    # Return report for programmatic use
    return report


if __name__ == "__main__":
    main()
