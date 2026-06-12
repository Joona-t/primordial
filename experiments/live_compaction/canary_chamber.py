"""
Live Compaction Test — Ground Truth Chamber

Creates a Forge chamber with 20 specific, verifiable "canary facts"
embedded across 5 agent stages. Each canary is a precise claim that
can be checked for presence in any summary.

The canaries span different information types:
- Exact numbers (most likely to be lost or rounded)
- Specific names/identifiers
- Causal relationships (A because B)
- Negations (X does NOT Y)
- Provenance chains (fact depends on earlier fact)
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from forge_nulls import AbsenceState
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_trace_codec import encode_trace, verify_trace, trace_stats

# ── 20 Canary Facts ──────────────────────────────────────────────────
# Each has: id, type, claim, embedded_in (stage), verification_query
CANARY_FACTS = [
    # Stage 1: Architecture discovery (architect seat)
    {"id": "C01", "type": "exact_number", "claim": "The system processes exactly 3,847 requests per second at peak load", "stage": "architect"},
    {"id": "C02", "type": "identifier", "claim": "The primary database is named 'helios-prod-west-7'", "stage": "architect"},
    {"id": "C03", "type": "causal", "claim": "Connection pooling was disabled because CVE-2024-31891 affects libpq versions below 15.3", "stage": "architect"},
    {"id": "C04", "type": "negation", "claim": "The auth service does NOT use JWT tokens — it uses opaque session references stored in Redis", "stage": "architect"},

    # Stage 2: Code analysis (builder seat)
    {"id": "C05", "type": "exact_number", "claim": "The retry logic uses exponential backoff with base delay 237ms and max 4 retries", "stage": "builder"},
    {"id": "C06", "type": "identifier", "claim": "The function handle_batch_ingestion in worker/pipeline.py is the entry point", "stage": "builder"},
    {"id": "C07", "type": "causal", "claim": "The batch size was reduced from 500 to 128 because memory profiling showed 2.3GB spikes at 500", "stage": "builder"},
    {"id": "C08", "type": "negation", "claim": "The pipeline does NOT validate schema on ingestion — validation happens only at the transform stage", "stage": "builder"},

    # Stage 3: Security review (critic seat)
    {"id": "C09", "type": "exact_number", "claim": "The security scan found exactly 14 high-severity and 37 medium-severity findings", "stage": "critic"},
    {"id": "C10", "type": "identifier", "claim": "The most critical finding is FORGE-SEC-2024-0042: unauthenticated access to /internal/metrics endpoint", "stage": "critic"},
    {"id": "C11", "type": "causal", "claim": "Rate limiting was bypassed because the X-Forwarded-For header is trusted without validation from the load balancer", "stage": "critic"},
    {"id": "C12", "type": "negation", "claim": "The TLS configuration does NOT support TLS 1.3 — it is pinned to TLS 1.2 due to a legacy HSM constraint", "stage": "critic"},

    # Stage 4: Performance analysis (analyst seat)
    {"id": "C13", "type": "exact_number", "claim": "P99 latency is 847ms, P95 is 312ms, and P50 is 23ms", "stage": "analyst"},
    {"id": "C14", "type": "identifier", "claim": "The slowest endpoint is POST /api/v2/reconciliation/batch which averages 2.1 seconds", "stage": "analyst"},
    {"id": "C15", "type": "causal", "claim": "GC pauses increased from 12ms to 89ms after upgrading to Java 21 because ZGC was replaced with G1GC in the deployment config", "stage": "analyst"},
    {"id": "C16", "type": "negation", "claim": "The cache layer does NOT evict on TTL — it uses LFU with a 16GB hard cap", "stage": "analyst"},

    # Stage 5: Integration findings (integrator seat)
    {"id": "C17", "type": "exact_number", "claim": "Cross-service calls have a 0.3% failure rate, with 67% of failures being timeouts to the payment-gateway service", "stage": "integrator"},
    {"id": "C18", "type": "identifier", "claim": "The circuit breaker library is resilience4j v2.1.0 with half-open state threshold of 5 requests", "stage": "integrator"},
    {"id": "C19", "type": "causal", "claim": "The event bus was migrated from RabbitMQ to Kafka because message ordering guarantees were needed for the audit trail", "stage": "integrator"},
    {"id": "C20", "type": "negation", "claim": "Service discovery does NOT use DNS-based resolution — it uses a custom etcd registry with 3-second lease TTL", "stage": "integrator"},
]


def build_stage_output(stage_name: str, canaries: list[dict]) -> str:
    """Build a realistic-looking stage output embedding the canary facts."""
    lines = [f"## {stage_name.title()} Analysis Report\n"]
    for c in canaries:
        lines.append(f"**[{c['id']}]** {c['claim']}\n")
    return "\n".join(lines)


def create_ground_truth_chamber():
    """Create a sealed Forge chamber with all 20 canary facts."""
    chamber = create_chamber("chamber:compaction-test:live-v1", metadata={
        "experiment": "live_compaction_test",
        "canary_count": len(CANARY_FACTS),
        "purpose": "Measure information loss through LLM agent compaction boundary",
    })

    stages = ["architect", "builder", "critic", "analyst", "integrator"]
    prev_artifact_id = None

    for stage_name in stages:
        stage_canaries = [c for c in CANARY_FACTS if c["stage"] == stage_name]
        output_text = build_stage_output(stage_name, stage_canaries)

        artifact_id = f"artifact:compaction-test:stage:{stage_name}:r1"
        source_refs = [prev_artifact_id] if prev_artifact_id else None

        artifact = create_v1_stage_artifact(
            stage_id=artifact_id,
            seat=stage_name,
            producer_name=f"{stage_name}-agent",
            producer_role=stage_name,
            output=output_text,
            source_refs=source_refs,
        )

        summary_text = f"{stage_name.title()} stage completed with {len(stage_canaries)} key findings."
        summary = create_v1_stage_summary(artifact, summary_text)

        register_stage(chamber, artifact, summary)
        prev_artifact_id = artifact_id

    seal_chamber(chamber)
    errors = validate_chamber(chamber)
    assert not errors, f"Chamber validation failed: {errors}"

    trace = encode_trace(chamber)
    verification = verify_trace(trace, chamber)
    assert verification["valid"], f"Trace verification failed: {verification}"

    return chamber, trace, CANARY_FACTS


def export_full_context(chamber: dict, canary_facts: list[dict]) -> str:
    """Export the full chamber content as text — this is what gets sent to the agent."""
    lines = [
        "# System Architecture Review — Full Session Transcript",
        f"# Chamber: {chamber['chamber_id']}",
        f"# Stages: {len(chamber['stages'])}",
        "",
    ]

    for stage_entry in chamber["stages"]:
        artifact = stage_entry["artifact"]
        seat = artifact["seat"]
        output = artifact["output"]
        refs = artifact.get("refs", [])

        lines.append(f"---")
        lines.append(f"## Stage {stage_entry['stage_index'] + 1}: {seat.title()}")
        if refs:
            ref_ids = [r["ref"] if isinstance(r, dict) else r for r in refs]
            lines.append(f"Depends on: {', '.join(ref_ids)}")
        lines.append("")
        lines.append(output)
        lines.append("")

    return "\n".join(lines)


def save_ground_truth(output_dir: Path):
    """Create chamber, export context, save everything."""
    output_dir.mkdir(parents=True, exist_ok=True)

    chamber, trace, canaries = create_ground_truth_chamber()

    # Save the full context (what gets sent to the compacting agent)
    full_context = export_full_context(chamber, canaries)
    (output_dir / "full_context.txt").write_text(full_context)

    # Save canary facts for the analyzer
    (output_dir / "canary_facts.json").write_text(
        json.dumps(canaries, indent=2)
    )

    # Save chamber and trace
    (output_dir / "chamber.json").write_text(
        json.dumps(chamber, indent=2, default=str)
    )
    (output_dir / "trace.json").write_text(
        json.dumps(trace, indent=2, default=str)
    )

    stats = trace_stats(trace)
    print(f"Chamber created: {chamber['chamber_id']}")
    print(f"  Stages: {len(chamber['stages'])}")
    print(f"  Canary facts: {len(canaries)}")
    print(f"  Trace compression: {stats['compression_ratio']:.2f}x")
    print(f"  Ground truth saved to: {output_dir}")
    print(f"\nFull context length: {len(full_context)} chars")

    return full_context


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "run_data"
    ctx = save_ground_truth(output_dir)
    print("\n" + "=" * 60)
    print("NEXT: Send full_context.txt through a compaction boundary")
    print("      (subagent, API call, or manual summary)")
    print("      Then run: python3 loss_analyzer.py <summary_file>")
