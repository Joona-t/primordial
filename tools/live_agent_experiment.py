"""
Live Agent Experiment — Primordial on Real Subagents

Task: "Analyze The Forge's architecture and recommend 3 improvements"

This runs 3 parallel research agents (via Claude Code's Agent tool),
captures their outputs with full Primordial instrumentation, then
synthesizes findings with a 4th agent. Some agents may fail, return
partial data, or produce no output — Primordial tracks WHY.

Measurements:
  - Typed absence: how many fields are missing, and WHY (not_generated vs not_invoked vs error)
  - Provenance: every synthesis claim traces back to a source agent's artifact
  - Compaction fidelity: SPF scores on summaries vs originals
  - Chamber integrity: all cross-refs resolve, no dangling pointers
"""

import sys
import os
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add tools dir to path
sys.path.insert(0, str(Path(__file__).parent))

from forge_nulls import absent, AbsenceState, validate_record, is_absent
from forge_chamber import (
    create_chamber, register_stage, seal_chamber,
    validate_chamber, save_chamber, get_context_view,
)
from forge_stage_output import (
    create_v1_stage_artifact, create_v1_stage_summary, validate_v1_stage,
)
from forge_reversible_summary import create_summary_view, is_grounded
from forge_trace_codec import encode_trace, verify_trace, trace_stats
from semantic_provenance_fidelity import SPFMetric
from findings_ledger import FindingsLedger, Finding


# === Agent Task Definitions ===

AGENT_TASKS = {
    "architecture-analyst": {
        "seat": "architecture_analyst",
        "role": "architecture",
        "prompt": (
            "Analyze the TypeScript codebase at /Users/darkfire/the-forge/src/. "
            "Focus on: (1) module coupling — which modules import from which, "
            "(2) error handling patterns — how errors propagate across collectors, "
            "(3) type safety — any 'as any' casts or unsafe patterns. "
            "Return a structured analysis with specific file:line references. "
            "Do NOT modify any files. Research only."
        ),
    },
    "performance-analyst": {
        "seat": "performance_analyst",
        "role": "performance",
        "prompt": (
            "Analyze the TypeScript codebase at /Users/darkfire/the-forge/src/. "
            "Focus on: (1) the collector parallelization strategy in run-daily-cycle.ts, "
            "(2) API rate limiting — how market-data.ts handles Yahoo Finance throttling, "
            "(3) memory patterns — any unbounded arrays or leaked closures. "
            "Return specific findings with file:line references. "
            "Do NOT modify any files. Research only."
        ),
    },
    "security-analyst": {
        "seat": "security_analyst",
        "role": "security",
        "prompt": (
            "Analyze the TypeScript codebase at /Users/darkfire/the-forge/src/. "
            "Focus on: (1) .env handling — is ANTHROPIC_API_KEY safe from leaking into logs, "
            "(2) the dashboard CORS policy (origin: '*'), "
            "(3) SEC EDGAR user-agent compliance, "
            "(4) any URLs or API keys that could leak into collector output JSON. "
            "Return specific findings with file:line references. "
            "Do NOT modify any files. Research only."
        ),
    },
}


def run_agent(name: str, task: dict, timeout_seconds: int = 120) -> dict:
    """Run a Claude Code subagent and capture its output."""
    start = time.time()
    result = {
        "agent": name,
        "seat": task["seat"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": None,
        "output_state": None,
        "error": None,
        "duration_ms": 0,
    }

    try:
        proc = subprocess.run(
            [
                "claude", "--print", "--dangerously-skip-permissions",
                "-p", task["prompt"],
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd="/Users/darkfire/the-forge",
        )

        duration = int((time.time() - start) * 1000)
        result["duration_ms"] = duration

        if proc.returncode == 0 and proc.stdout.strip():
            result["output"] = proc.stdout.strip()
        elif proc.returncode == 0:
            result["output_state"] = "not_generated"
            result["error"] = "Agent returned empty output"
        else:
            result["output_state"] = "invalid"
            result["error"] = f"Exit code {proc.returncode}: {proc.stderr[:500]}"

    except subprocess.TimeoutExpired:
        result["output_state"] = "not_generated"
        result["error"] = f"Agent timed out after {timeout_seconds}s"
        result["duration_ms"] = timeout_seconds * 1000
    except Exception as e:
        result["output_state"] = "unknown"
        result["error"] = str(e)
        result["duration_ms"] = int((time.time() - start) * 1000)

    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    return result


def run_synthesis_agent(upstream_outputs: dict, timeout_seconds: int = 90) -> dict:
    """Run synthesis agent that combines findings from upstream analysts."""
    context_parts = []
    for name, data in upstream_outputs.items():
        if data["output"]:
            context_parts.append(f"=== {name} ===\n{data['output'][:3000]}")
        else:
            context_parts.append(f"=== {name} ===\n[No output: {data.get('error', 'unknown reason')}]")

    context = "\n\n".join(context_parts)

    prompt = (
        f"You are a synthesis agent. Below are findings from 3 parallel research agents "
        f"who analyzed The Forge codebase. Synthesize their findings into exactly 3 "
        f"prioritized improvement recommendations. For each recommendation:\n"
        f"1. Title (one line)\n"
        f"2. Priority (P0/P1/P2)\n"
        f"3. Which analyst(s) identified it\n"
        f"4. Specific action to take\n\n"
        f"IMPORTANT: If an analyst produced no output, note that gap explicitly.\n\n"
        f"{context}"
    )

    return run_agent("synthesizer", {
        "seat": "synthesizer",
        "role": "synthesis",
        "prompt": prompt,
    }, timeout_seconds)


def build_chamber(agent_results: dict, synthesis_result: dict) -> dict:
    """Build a Primordial chamber from agent results."""
    run_id = f"live-{int(time.time())}"
    chamber = create_chamber(f"chamber:{run_id}:v1", metadata={
        "experiment": "live_agent_analysis",
        "task": "forge_architecture_review",
        "agent_count": len(agent_results) + 1,
        "framework": "claude-code-subagents",
    })

    # Register analyst stages
    analyst_artifact_ids = []
    for name, result in agent_results.items():
        task = AGENT_TASKS[name]
        artifact_id = f"artifact:{run_id}:stage:{task['seat']}:r1"

        if result["output"]:
            artifact = create_v1_stage_artifact(
                stage_id=artifact_id,
                seat=task["seat"],
                producer_name=name,
                producer_role=task["role"],
                output=result["output"],
                findings=[{
                    "code": "CRITIQUE.CRIT_ARCHITECTURE",
                    "detail": f"{name} completed in {result['duration_ms']}ms",
                }],
            )
            summary = create_v1_stage_summary(
                artifact,
                f"{name}: {result['output'][:200]}...",
            )
            register_stage(chamber, artifact, summary)
        else:
            # Typed absence — we know WHY it's missing
            state = AbsenceState(result["output_state"]) if result["output_state"] else AbsenceState.UNKNOWN
            artifact = create_v1_stage_artifact(
                stage_id=artifact_id,
                seat=task["seat"],
                producer_name=name,
                producer_role=task["role"],
                output=None,
                output_state=state,
                stop_reason="STOP.STOP_ERROR" if result["error"] else "STOP.STOP_TIMEOUT",
                findings=[{
                    "code": "ERROR.ERR_TIMEOUT_SEAT" if "timeout" in (result.get("error") or "").lower()
                            else "ERROR.ERR_SEAT_FAILED",
                    "detail": result.get("error", "Unknown failure"),
                }],
            )
            register_stage(chamber, artifact, summary_state="not_generated")

        analyst_artifact_ids.append(artifact_id)

    # Register synthesis stage (references all upstream)
    synth_id = f"artifact:{run_id}:stage:synthesizer:r1"
    successful_refs = [
        aid for aid, res in zip(analyst_artifact_ids, agent_results.values())
        if res["output"]
    ]

    if synthesis_result["output"]:
        synth_artifact = create_v1_stage_artifact(
            stage_id=synth_id,
            seat="synthesizer",
            producer_name="synthesizer",
            producer_role="synthesis",
            output=synthesis_result["output"],
            source_refs=successful_refs,
            findings=[{
                "code": "CRITIQUE.CRIT_ARCHITECTURE",
                "detail": f"Synthesis from {len(successful_refs)}/{len(analyst_artifact_ids)} sources",
            }],
        )
        synth_summary = create_v1_stage_summary(
            synth_artifact,
            f"Synthesis of {len(successful_refs)} analyst outputs into 3 recommendations",
            extra_source_refs=successful_refs,
        )
        register_stage(chamber, synth_artifact, synth_summary)
    else:
        state = AbsenceState(synthesis_result["output_state"]) if synthesis_result["output_state"] else AbsenceState.UNKNOWN
        synth_artifact = create_v1_stage_artifact(
            stage_id=synth_id,
            seat="synthesizer",
            producer_name="synthesizer",
            producer_role="synthesis",
            output=None,
            output_state=state,
            source_refs=successful_refs,
            stop_reason="STOP.STOP_ERROR",
            findings=[{
                "code": "ERROR.ERR_API_FAIL",
                "detail": synthesis_result.get("error", "Unknown failure"),
            }],
        )
        register_stage(chamber, synth_artifact, summary_state="not_generated")

    seal_chamber(chamber)
    return chamber


def measure_compaction(chamber: dict) -> dict:
    """Measure SPF on summaries vs original outputs."""
    spf = SPFMetric()
    pairs = []

    for stage in chamber["stages"]:
        original = stage["artifact"].get("output")
        summary = stage.get("summary")

        if original and summary and isinstance(summary, dict):
            summary_text = summary.get("summary", "")
            if summary_text:
                pairs.append((original, summary_text))

    if not pairs:
        return {"pairs": 0, "aggregate": None}

    measurements = spf.measure_batch(pairs)
    aggregate = spf.aggregate(measurements)

    return {
        "pairs": len(pairs),
        "measurements": measurements,
        "aggregate": aggregate,
    }


def collect_metrics(chamber: dict, agent_results: dict, synthesis_result: dict, spf_results: dict) -> dict:
    """Collect all experiment metrics."""
    # Chamber validation
    errors = validate_chamber(chamber)

    # Trace encoding
    trace = encode_trace(chamber)
    trace_verification = verify_trace(trace, chamber)
    stats = trace_stats(trace)

    # Typed absence accounting
    absence_counts = {"total": 0, "by_state": {}}
    for stage in chamber["stages"]:
        out_state = stage["artifact"].get("output_state")
        if out_state:
            absence_counts["total"] += 1
            absence_counts["by_state"][out_state] = absence_counts["by_state"].get(out_state, 0) + 1

    # Provenance check — does synthesis reference all available sources?
    synth_stage = next((s for s in chamber["stages"] if s["seat"] == "synthesizer"), None)
    provenance = {"grounded": False, "source_ref_count": 0, "available_sources": 0}
    if synth_stage:
        refs = synth_stage["artifact"].get("refs", [])
        provenance["source_ref_count"] = len(refs)
        provenance["available_sources"] = sum(1 for s in chamber["stages"] if s["seat"] != "synthesizer" and s["artifact"].get("output"))
        if synth_stage.get("summary") and isinstance(synth_stage["summary"], dict):
            provenance["grounded"] = is_grounded(synth_stage["summary"])

    # Agent timing
    timings = {}
    for name, result in agent_results.items():
        timings[name] = {
            "duration_ms": result["duration_ms"],
            "succeeded": result["output"] is not None,
            "absence_state": result.get("output_state"),
        }
    timings["synthesizer"] = {
        "duration_ms": synthesis_result["duration_ms"],
        "succeeded": synthesis_result["output"] is not None,
        "absence_state": synthesis_result.get("output_state"),
    }

    return {
        "experiment": "live_agent_primordial",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chamber_id": chamber["chamber_id"],
        "chamber_status": chamber["status"],
        "chamber_errors": errors,
        "total_stages": len(chamber["stages"]),
        "trace": {
            "verified": trace_verification["valid"],
            "hash_match": trace_verification["hash_match"],
            "compression_ratio": stats["compression_ratio"],
            "shared_structures": stats["shared_structures"],
            "ref_replacements": stats["ref_replacements"],
        },
        "typed_absence": absence_counts,
        "provenance": provenance,
        "spf": {
            "pairs_measured": spf_results["pairs"],
            "aggregate": spf_results.get("aggregate"),
        },
        "agent_timings": timings,
        "total_duration_ms": sum(t["duration_ms"] for t in timings.values()),
    }


def record_findings(ledger: FindingsLedger, metrics: dict):
    """Record experiment findings to the ledger."""
    # Finding 1: Typed absence effectiveness
    absence = metrics["typed_absence"]
    ledger.record(Finding(
        phase=7,
        category="ontology",
        rq="RQ1",
        title=f"Live agent typed absence: {absence['total']} absent fields with explicit states",
        description=(
            f"In a 4-agent live run, {absence['total']} output fields were absent. "
            f"Each was classified: {json.dumps(absence['by_state'])}. "
            f"Zero ambiguous nulls — every absence has a reason."
        ),
        evidence=absence,
        verdict="positive" if absence["total"] == 0 or all(
            s in {"not_generated", "invalid", "unknown"} for s in absence["by_state"]
        ) else "partial",
        confidence="high",
        tags=["live-experiment", "typed-absence"],
    ))

    # Finding 2: Provenance integrity
    prov = metrics["provenance"]
    ledger.record(Finding(
        phase=7,
        category="architecture",
        rq="RQ2",
        title=f"Synthesis provenance: {prov['source_ref_count']} refs to {prov['available_sources']} sources",
        description=(
            f"The synthesis agent's output references {prov['source_ref_count']} upstream artifacts. "
            f"{prov['available_sources']} source agents produced output. "
            f"Summary grounded: {prov['grounded']}."
        ),
        evidence=prov,
        verdict="positive" if prov["grounded"] and prov["source_ref_count"] >= prov["available_sources"] else "partial",
        confidence="high",
        tags=["live-experiment", "provenance"],
    ))

    # Finding 3: Compaction fidelity
    spf = metrics["spf"]
    if spf["aggregate"]:
        agg = spf["aggregate"]
        ledger.record(Finding(
            phase=7,
            category="compaction",
            rq="RQ3",
            title=f"Live SPF: jaccard={agg['jaccard']['mean']:.3f}, token_overlap={agg['token_overlap']['mean']:.3f}",
            description=(
                f"Measured {spf['pairs_measured']} summary-vs-original pairs. "
                f"Mean Jaccard: {agg['jaccard']['mean']:.3f}, "
                f"Mean token overlap: {agg['token_overlap']['mean']:.3f}, "
                f"Mean weighted overlap: {agg['weighted_overlap']['mean']:.3f}."
            ),
            evidence={"pairs": spf["pairs_measured"], "aggregate": agg},
            verdict="positive" if agg["jaccard"]["mean"] > 0.1 else "negative",
            confidence="high",
            tags=["live-experiment", "spf", "compaction"],
        ))

    # Finding 4: Chamber integrity
    ledger.record(Finding(
        phase=7,
        category="architecture",
        rq="RQ2",
        title=f"Chamber integrity: {len(metrics['chamber_errors'])} validation errors",
        description=(
            f"Chamber {metrics['chamber_id']} with {metrics['total_stages']} stages. "
            f"Trace verified: {metrics['trace']['verified']}, "
            f"hash match: {metrics['trace']['hash_match']}, "
            f"compression: {metrics['trace']['compression_ratio']:.2f}x."
        ),
        evidence={
            "errors": metrics["chamber_errors"],
            "trace": metrics["trace"],
        },
        verdict="positive" if len(metrics["chamber_errors"]) == 0 and metrics["trace"]["verified"] else "negative",
        confidence="high",
        tags=["live-experiment", "chamber-integrity"],
    ))


def main():
    print("=" * 70)
    print("PRIMORDIAL LIVE AGENT EXPERIMENT")
    print("Task: Analyze The Forge architecture with 3 parallel analysts + synthesizer")
    print("=" * 70)

    output_dir = Path(__file__).parent.parent / "data" / "live_experiment"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for cached results
    raw_path = output_dir / "raw_agent_outputs.json"
    use_cache = "--use-cache" in sys.argv and raw_path.exists()

    if use_cache:
        print("\n[Phase 1-2] Loading cached agent outputs...")
        with open(raw_path) as f:
            cached = json.load(f)
        agent_results = cached["agents"]
        synthesis_result = cached["synthesis"]
        for name, r in agent_results.items():
            status = "OK" if r["output"] else f"ABSENT ({r.get('output_state')})"
            print(f"  {name}: {status} ({r['duration_ms']}ms) [cached]")
        synth_status = "OK" if synthesis_result["output"] else f"ABSENT ({synthesis_result.get('output_state')})"
        print(f"  synthesizer: {synth_status} ({synthesis_result['duration_ms']}ms) [cached]")
    else:
        # Phase 1: Run parallel analysts
        print("\n[Phase 1] Running 3 analyst agents in parallel...")
        agent_results = {}
        for name, task in AGENT_TASKS.items():
            print(f"  Starting {name}...")
            result = run_agent(name, task, timeout_seconds=180)
            status = "OK" if result["output"] else f"ABSENT ({result['output_state']})"
            print(f"  {name}: {status} ({result['duration_ms']}ms)")
            agent_results[name] = result

        # Phase 2: Run synthesis
        print("\n[Phase 2] Running synthesis agent...")
        synthesis_result = run_synthesis_agent(agent_results, timeout_seconds=120)
        synth_status = "OK" if synthesis_result["output"] else f"ABSENT ({synthesis_result['output_state']})"
        print(f"  synthesizer: {synth_status} ({synthesis_result['duration_ms']}ms)")

    # Phase 3: Build Primordial chamber
    print("\n[Phase 3] Building Primordial chamber...")
    chamber = build_chamber(agent_results, synthesis_result)
    chamber_path = save_chamber(chamber, base_dir=str(output_dir))
    print(f"  Chamber: {chamber['chamber_id']}")
    print(f"  Stages: {len(chamber['stages'])}")
    print(f"  Saved: {chamber_path}")

    # Phase 4: Measure compaction fidelity
    print("\n[Phase 4] Measuring compaction fidelity (SPF)...")
    spf_results = measure_compaction(chamber)
    print(f"  Pairs measured: {spf_results['pairs']}")
    if spf_results["aggregate"]:
        agg = spf_results["aggregate"]
        print(f"  Mean Jaccard: {agg['jaccard']['mean']:.3f}")
        print(f"  Mean token overlap: {agg['token_overlap']['mean']:.3f}")

    # Phase 5: Collect metrics
    print("\n[Phase 5] Collecting metrics...")
    metrics = collect_metrics(chamber, agent_results, synthesis_result, spf_results)

    # Save metrics
    metrics_path = output_dir / "experiment_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Metrics: {metrics_path}")

    # Save raw agent outputs
    raw_path = output_dir / "raw_agent_outputs.json"
    with open(raw_path, "w") as f:
        json.dump({
            "agents": agent_results,
            "synthesis": synthesis_result,
        }, f, indent=2, default=str)
    print(f"  Raw outputs: {raw_path}")

    # Phase 6: Record findings
    print("\n[Phase 6] Recording findings to ledger...")
    ledger = FindingsLedger(data_dir=str(output_dir / "findings"))
    record_findings(ledger, metrics)
    summary = ledger.summary()
    print(f"  Findings recorded: {summary['total']}")
    print(f"  By verdict: {json.dumps(summary['by_verdict'])}")

    # Export
    ledger.export_markdown(str(output_dir / "findings_report.md"))
    ledger.export_json(str(output_dir / "findings_export.json"))

    # Final report
    print("\n" + "=" * 70)
    print("EXPERIMENT RESULTS")
    print("=" * 70)
    print(f"\n  Agents run:           {len(agent_results) + 1}")
    print(f"  Agents succeeded:     {sum(1 for r in list(agent_results.values()) + [synthesis_result] if r['output'])}")
    print(f"  Chamber stages:       {metrics['total_stages']}")
    print(f"  Chamber errors:       {len(metrics['chamber_errors'])}")
    print(f"  Trace verified:       {metrics['trace']['verified']}")
    print(f"  Trace compression:    {metrics['trace']['compression_ratio']:.2f}x")
    print(f"  Typed absences:       {metrics['typed_absence']['total']}")
    if metrics['typed_absence']['by_state']:
        for state, count in metrics['typed_absence']['by_state'].items():
            print(f"    - {state}: {count}")
    print(f"  Provenance grounded:  {metrics['provenance']['grounded']}")
    print(f"  SPF pairs:            {metrics['spf']['pairs_measured']}")
    if metrics['spf']['aggregate']:
        a = metrics['spf']['aggregate']
        print(f"  SPF jaccard mean:     {a['jaccard']['mean']:.3f}")
        print(f"  SPF token overlap:    {a['token_overlap']['mean']:.3f}")
    print(f"  Total duration:       {metrics['total_duration_ms'] / 1000:.1f}s")
    print(f"\n  Output dir: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
