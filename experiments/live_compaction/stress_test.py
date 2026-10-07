"""
Primordial Forge — A/B Compaction Stress Test

Multi-phase stress test that scales from small to massive contexts,
comparing raw (control) vs Primordial-instrumented (treatment) compaction.

Phase 1: 50 canaries in 10K chars (warm-up)
Phase 2: 150 canaries in 50K chars (medium pressure)
Phase 3: 500 canaries in 200K chars (heavy pressure)
Phase 4: 500 canaries through 3-hop chain compaction (cascade)
Phase 5: 500 canaries in 500K+ chars with distractor noise (adversarial)

Each phase runs both A (raw) and B (instrumented) conditions.
"""

import sys
import json
import hashlib
import random
import string
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from forge_nulls import AbsenceState, absent
from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
from forge_chamber import create_chamber, register_stage, seal_chamber, validate_chamber
from forge_trace_codec import encode_trace, verify_trace, trace_stats

# ── Canary Generation ────────────────────────────────────────────────

DOMAINS = [
    "auth", "billing", "ingestion", "analytics", "notification",
    "search", "storage", "gateway", "scheduler", "monitoring",
    "compliance", "reporting", "migration", "cache", "messaging",
]

CANARY_TEMPLATES = {
    "exact_number": [
        "The {domain} service processes exactly {n1:,} events per second with a buffer of {n2} entries",
        "Peak memory for {domain} is {n1}.{n2}MB measured on {date}",
        "The {domain} queue depth averages {n1:,} with max observed {n2:,} on {date}",
        "Connection pool for {domain} has {n1} active and {n2} idle connections at steady state",
        "The {domain} batch processor handles {n1:,} records in {n2}ms per cycle",
    ],
    "identifier": [
        "The {domain} primary instance is '{domain}-prod-{region}-{n1}'",
        "Entry point function is {func_name} in {domain}/core/{file_name}.py line {n1}",
        "The {domain} config is stored at /etc/{domain}/v{n1}.{n2}.conf on host {host}",
        "Certificate CN for {domain} TLS is '{domain}.internal.{org}.{tld}'",
        "The {domain} deployment uses image registry.{org}.io/{domain}:{tag}",
    ],
    "causal": [
        "The {domain} timeout was increased from {n1}ms to {n2}ms because latency spikes correlated with GC pauses in the upstream {domain2} service",
        "{domain} switched from {tech1} to {tech2} because {reason}",
        "The {domain} retry limit was reduced from {n1} to {n2} after incident INC-{inc_id} showed cascading failures",
        "Rate limiting on {domain} was tightened from {n1}/min to {n2}/min because abuse detection found {n3} bot accounts",
        "{domain} schema version was frozen at v{n1} because {domain2} cannot parse v{n2} until their Q3 migration completes",
    ],
    "negation": [
        "The {domain} service does NOT use {tech1} — it relies on {tech2} with {detail}",
        "{domain} authentication does NOT validate {field} — this is handled by the {domain2} gateway instead",
        "The {domain} cache does NOT expire on TTL — eviction is {policy}-based with a {n1}GB cap",
        "{domain} does NOT write directly to {store1} — all writes go through the {store2} event bus first",
        "The {domain} API does NOT support pagination via offset — it uses cursor-based iteration with token '{token_prefix}_next'",
    ],
    "provenance": [
        "Based on the {domain} architect's finding that {prior_claim}, the builder implemented {impl_detail}",
        "The {domain} critic flagged {issue} which traces back to the architect's decision to {decision}",
        "After {domain} stage {n1} found {finding}, stage {n2} was re-run with {adjustment}",
        "The {domain} integrator confirmed that {upstream_fact} from stage {n1} is still valid after {domain2} changes in stage {n2}",
        "The {domain} security review in stage {n1} depends on the {domain2} architecture from stage {n2}: if {condition} changes, re-audit required",
    ],
}

# Realistic noise generators
NOISE_PARAGRAPHS = [
    "During the review, the team discussed various approaches to improving system reliability. Several options were considered including active-passive failover, consensus-based replication, and event sourcing patterns. The tradeoffs between consistency and availability were weighed against the current SLA requirements.",
    "The deployment pipeline consists of multiple stages including unit tests, integration tests, contract tests, and canary deployments. Each stage has configurable gates that can be adjusted based on the risk profile of the change. The rollback mechanism uses blue-green deployment with automatic health checks.",
    "Infrastructure costs were analyzed across multiple dimensions including compute, storage, network egress, and managed service fees. The team identified several optimization opportunities in right-sizing instances and leveraging reserved capacity. A cost allocation model was proposed to improve visibility into per-service spending.",
    "The observability stack includes metrics collection via Prometheus, distributed tracing via Jaeger, and centralized logging via Elasticsearch. Alert routing is handled by PagerDuty with escalation policies defined per service tier. Dashboard templates are maintained as code in a shared repository.",
    "The data governance framework requires all PII to be classified, encrypted at rest, and access-logged. Retention policies vary by data category from 30 days for debug logs to 7 years for financial records. Cross-border data transfer restrictions apply to EU user data under GDPR compliance requirements.",
    "Performance testing is conducted weekly using a combination of load tests, stress tests, and soak tests. The baseline metrics are tracked over time to detect gradual degradation. Capacity planning models are updated quarterly based on growth projections and feature roadmap impact assessments.",
    "The API versioning strategy uses URL-based versioning for major changes and header-based feature flags for minor additions. Deprecation notices are communicated via response headers and developer portal announcements. Backward compatibility is maintained for a minimum of 6 months after deprecation.",
    "Service mesh configuration manages inter-service communication including mTLS, circuit breaking, retry policies, and load balancing. Traffic splitting for canary releases is controlled via weighted routing rules. Observability data from the mesh is correlated with application-level metrics for end-to-end visibility.",
]


def generate_random_values():
    """Generate random but realistic-looking values for canary templates."""
    regions = ["us-east-1", "eu-west-2", "ap-south-1", "us-west-2"]
    orgs = ["acme", "globex", "initech", "umbrella", "weyland"]
    techs = ["Redis", "Memcached", "PostgreSQL", "MongoDB", "DynamoDB", "Cassandra",
             "Kafka", "RabbitMQ", "NATS", "gRPC", "REST", "GraphQL", "etcd", "Consul"]
    policies = ["LRU", "LFU", "FIFO", "ARC", "LIRS"]
    stores = ["PostgreSQL", "S3", "DynamoDB", "Redis", "Elasticsearch"]
    reasons = [
        "message ordering was required for audit compliance",
        "the legacy protocol had a known memory leak under sustained load",
        "horizontal scaling required stateless request handling",
        "the security team mandated encryption at the transport layer",
        "latency requirements dropped below the old system's floor",
    ]
    func_names = [
        "process_incoming_batch", "validate_and_route", "handle_event_stream",
        "execute_reconciliation", "run_compliance_check", "sync_upstream_state",
        "dispatch_notification", "aggregate_metrics", "transform_payload",
    ]
    file_names = ["handler", "processor", "router", "validator", "dispatcher", "engine"]
    hosts = ["ip-10-0-1-42", "ip-172-16-3-17", "ip-10-0-8-91", "ip-192-168-1-23"]
    tlds = ["net", "io", "com", "dev"]
    tags = [f"v{random.randint(1,5)}.{random.randint(0,30)}.{random.randint(0,99)}-{random.choice(['stable','rc1','beta'])}" for _ in range(5)]
    fields = ["X-Request-ID", "Authorization bearer scope", "Content-Type charset", "X-Forwarded-Proto"]
    token_prefixes = ["pgn", "cur", "iter", "seq", "tok"]

    return {
        "n1": random.randint(10, 99999),
        "n2": random.randint(10, 99999),
        "n3": random.randint(100, 9999),
        "region": random.choice(regions),
        "org": random.choice(orgs),
        "tech1": random.choice(techs),
        "tech2": random.choice(techs),
        "policy": random.choice(policies),
        "store1": random.choice(stores),
        "store2": random.choice(stores),
        "reason": random.choice(reasons),
        "func_name": random.choice(func_names),
        "file_name": random.choice(file_names),
        "host": random.choice(hosts),
        "tld": random.choice(tlds),
        "tag": random.choice(tags),
        "field": random.choice(fields),
        "token_prefix": random.choice(token_prefixes),
        "date": f"2026-0{random.randint(1,3)}-{random.randint(10,28)}",
        "inc_id": random.randint(10000, 99999),
    }


def generate_canaries(count: int, seed: int = 42) -> list[dict]:
    """Generate N unique canary facts with verifiable signal tokens."""
    random.seed(seed)
    canaries = []
    types = list(CANARY_TEMPLATES.keys())

    for i in range(count):
        ctype = types[i % len(types)]
        templates = CANARY_TEMPLATES[ctype]
        template = templates[i % len(templates)]

        domain = DOMAINS[i % len(DOMAINS)]
        domain2 = DOMAINS[(i + 7) % len(DOMAINS)]
        vals = generate_random_values()
        vals["domain"] = domain
        vals["domain2"] = domain2

        # For provenance types, add cross-references
        if ctype == "provenance":
            prior_idx = max(0, i - random.randint(1, 5))
            vals["prior_claim"] = f"finding F-{prior_idx:04d}"
            vals["impl_detail"] = f"mitigation M-{i:04d}"
            vals["issue"] = f"issue ISS-{i:04d}"
            vals["decision"] = f"decision D-{prior_idx:04d}"
            vals["finding"] = f"finding F-{i:04d}"
            vals["adjustment"] = f"adjustment ADJ-{i:04d}"
            vals["upstream_fact"] = f"fact UF-{prior_idx:04d}"
            vals["condition"] = f"condition COND-{prior_idx:04d}"

        # Try to format, skip missing keys gracefully
        try:
            claim = template.format(**vals)
        except KeyError:
            claim = f"The {domain} system has a critical configuration with value {vals['n1']} affecting {vals['n2']} components"

        # Extract signal tokens — the specific values that must survive
        signals = []
        # Always include the exact numbers
        signals.append(f"{vals['n1']:,}" if vals['n1'] > 999 else str(vals['n1']))
        if ctype == "identifier":
            # Include the generated identifier
            if "prod-" in claim:
                signals.append(f"{domain}-prod-")
            if vals.get("func_name") and vals["func_name"] in claim:
                signals.append(vals["func_name"])
        if ctype == "negation" and "NOT" in claim:
            signals.append(vals.get("tech2", vals.get("policy", str(vals["n1"]))))
        if ctype == "provenance":
            signals.append(f"F-{i:04d}" if f"F-{i:04d}" in claim else f"M-{i:04d}")

        canary_id = f"C{i:04d}"
        canaries.append({
            "id": canary_id,
            "type": ctype,
            "claim": claim,
            "stage": domain,
            "signals": signals,
            "domain": domain,
        })

    return canaries


def build_raw_context(canaries: list[dict], add_noise: bool = False, noise_ratio: float = 3.0) -> str:
    """Build raw (control) context — just the facts, no Primordial metadata."""
    lines = ["# System Architecture Review — Multi-Domain Analysis\n"]

    # Group by domain/stage
    by_domain = {}
    for c in canaries:
        by_domain.setdefault(c["domain"], []).append(c)

    for domain, domain_canaries in by_domain.items():
        lines.append(f"\n## {domain.title()} Service Review\n")

        if add_noise:
            # Add distractor paragraphs before the facts
            noise_count = max(1, int(len(domain_canaries) * noise_ratio / len(NOISE_PARAGRAPHS)))
            for _ in range(noise_count):
                lines.append(random.choice(NOISE_PARAGRAPHS))
                lines.append("")

        for c in domain_canaries:
            lines.append(f"- {c['claim']}")
            if add_noise:
                # Interleave noise between facts
                if random.random() < 0.4:
                    lines.append(f"  (Further analysis pending review cycle {random.randint(1,5)})")
                    lines.append("")

        lines.append("")

    return "\n".join(lines)


def build_instrumented_context(canaries: list[dict], add_noise: bool = False, noise_ratio: float = 3.0) -> str:
    """Build Primordial-instrumented (treatment) context with typed metadata."""
    lines = [
        "# System Architecture Review — Multi-Domain Analysis",
        "# PRIMORDIAL FORGE INSTRUMENTED — Typed Absence Protocol Active",
        "",
        "## Compaction Instructions",
        "This document contains typed artifacts with provenance metadata.",
        "When summarizing, you MUST:",
        "1. Preserve all artifact IDs (format: [CXXXX])",
        "2. For any fact you cannot include, mark it with its absence state:",
        "   - PRUNED_RECOVERABLE: fact compressed but source ref preserved",
        "   - DELETED: fact intentionally removed (unrecoverable)",
        "   - UNKNOWN: unable to determine if fact is still valid",
        "3. Preserve provenance chains: if fact B depends on fact A, note the dependency",
        "4. Negations (NOT/DOES NOT) are high-priority — never silently drop a negation",
        "5. Exact numbers are high-priority — never round or approximate without marking",
        "",
        "## Absence State Legend",
        "| State | Meaning | Recovery |",
        "|-------|---------|----------|",
        "| PRUNED_RECOVERABLE | Detail compressed, source available | Re-read source stage |",
        "| DELETED | Removed, no recovery path | Re-run analysis |",
        "| UNKNOWN | Cannot determine status | Investigate |",
        "| NOT_GENERATED | Never produced | Run missing stage |",
        "",
    ]

    by_domain = {}
    for c in canaries:
        by_domain.setdefault(c["domain"], []).append(c)

    stage_idx = 0
    prev_artifact_id = None
    for domain, domain_canaries in by_domain.items():
        stage_idx += 1
        artifact_id = f"artifact:stress:{domain}:r1"

        lines.append(f"\n## Stage {stage_idx}: {domain.title()} Service")
        lines.append(f"Artifact: {artifact_id}")
        if prev_artifact_id:
            lines.append(f"Depends-on: {prev_artifact_id}")
        lines.append(f"Priority: ALL facts below are CRITICAL — preserve or mark absent")
        lines.append("")

        if add_noise:
            noise_count = max(1, int(len(domain_canaries) * noise_ratio / len(NOISE_PARAGRAPHS)))
            for _ in range(noise_count):
                lines.append(random.choice(NOISE_PARAGRAPHS))
                lines.append("")

        for c in domain_canaries:
            priority = "HIGH" if c["type"] in ("negation", "exact_number") else "MEDIUM"
            lines.append(f"- [{c['id']}] [priority:{priority}] [type:{c['type']}] {c['claim']}")
            if c["type"] == "provenance" and prev_artifact_id:
                lines.append(f"  └─ provenance: depends on {prev_artifact_id}")
            if add_noise and random.random() < 0.4:
                lines.append(f"  (Further analysis pending review cycle {random.randint(1,5)})")
                lines.append("")

        lines.append("")
        prev_artifact_id = artifact_id

    lines.append("\n## End of Instrumented Session")
    lines.append("If compacting: list ALL artifact IDs that were PRUNED or DELETED with their absence state.")

    return "\n".join(lines)


def check_canary_survival(canary: dict, summary: str) -> dict:
    """Check if a canary's signals survived in the summary."""
    summary_lower = summary.lower()

    found = []
    for signal in canary["signals"]:
        if signal.lower() in summary_lower:
            found.append(signal)

    survived = len(found) > 0

    # Check if the canary ID itself survived (instrumented condition)
    id_preserved = canary["id"].lower() in summary_lower

    # Check for absence marking (instrumented condition)
    absence_marked = False
    for marker in ["pruned_recoverable", "pruned", "deleted", "unknown", "not_generated"]:
        if f"{canary['id'].lower()}" in summary_lower and marker in summary_lower:
            absence_marked = True
            break

    return {
        "id": canary["id"],
        "type": canary["type"],
        "domain": canary["domain"],
        "survived": survived,
        "id_preserved": id_preserved,
        "absence_marked": absence_marked,
        "signals_checked": canary["signals"],
        "signals_found": found,
    }


def analyze_results(canaries: list[dict], summary: str, condition: str) -> dict:
    """Full analysis of compaction results."""
    results = [check_canary_survival(c, summary) for c in canaries]

    survived = [r for r in results if r["survived"]]
    lost = [r for r in results if not r["survived"]]
    id_preserved = [r for r in results if r["id_preserved"]]
    absence_marked = [r for r in lost if r["absence_marked"]]

    # By type
    types = set(c["type"] for c in canaries)
    by_type = {}
    for t in sorted(types):
        t_results = [r for r in results if r["type"] == t]
        t_survived = [r for r in t_results if r["survived"]]
        by_type[t] = {"total": len(t_results), "survived": len(t_survived),
                      "rate": len(t_survived) / len(t_results) if t_results else 0}

    # By domain
    domains = set(c["domain"] for c in canaries)
    by_domain = {}
    for d in sorted(domains):
        d_results = [r for r in results if r["domain"] == d]
        d_survived = [r for r in d_results if r["survived"]]
        by_domain[d] = {"total": len(d_results), "survived": len(d_survived),
                        "rate": len(d_survived) / len(d_results) if d_results else 0}

    return {
        "condition": condition,
        "summary_length": len(summary),
        "total_canaries": len(results),
        "survived": len(survived),
        "lost": len(lost),
        "survival_rate": len(survived) / len(results) if results else 0,
        "ids_preserved": len(id_preserved),
        "ids_preserved_rate": len(id_preserved) / len(results) if results else 0,
        "absence_marked": len(absence_marked),
        "absence_marked_rate": len(absence_marked) / len(lost) if lost else 1.0,
        "by_type": by_type,
        "by_domain": by_domain,
        "details": results,
    }


def print_comparison(result_a: dict, result_b: dict, phase_name: str):
    """Pretty-print A/B comparison."""
    print(f"\n{'=' * 72}")
    print(f"  PHASE: {phase_name}")
    print(f"{'=' * 72}")

    print(f"\n  {'Metric':<30} {'A (Raw)':<18} {'B (Instrumented)':<18} {'Delta'}")
    print(f"  {'─' * 78}")
    print(f"  {'Context length':<30} {result_a['summary_length']:>12,} ch  {result_b['summary_length']:>12,} ch")
    print(f"  {'Canaries survived':<30} {result_a['survived']:>6}/{result_a['total_canaries']:<6} ({result_a['survival_rate']:.0%})  {result_b['survived']:>6}/{result_b['total_canaries']:<6} ({result_b['survival_rate']:.0%})  {result_b['survival_rate'] - result_a['survival_rate']:+.0%}")
    print(f"  {'Canaries lost':<30} {result_a['lost']:>6}           {result_b['lost']:>6}")
    print(f"  {'IDs preserved':<30} {result_a['ids_preserved']:>6} ({result_a['ids_preserved_rate']:.0%})       {result_b['ids_preserved']:>6} ({result_b['ids_preserved_rate']:.0%})")
    print(f"  {'Absent facts marked':<30} {result_a['absence_marked']:>6}           {result_b['absence_marked']:>6} ({result_b['absence_marked_rate']:.0%} of lost)")

    print(f"\n  ── Survival by Type ──")
    types = sorted(set(list(result_a["by_type"].keys()) + list(result_b["by_type"].keys())))
    for t in types:
        a = result_a["by_type"].get(t, {"rate": 0, "survived": 0, "total": 0})
        b = result_b["by_type"].get(t, {"rate": 0, "survived": 0, "total": 0})
        delta = b["rate"] - a["rate"]
        print(f"    {t:<16} A: {a['survived']:>3}/{a['total']:<3} ({a['rate']:.0%})   B: {b['survived']:>3}/{b['total']:<3} ({b['rate']:.0%})   {delta:+.0%}")

    print(f"\n  ── Survival by Domain (bottom 5) ──")
    # Show worst-performing domains
    a_domains = sorted(result_a["by_domain"].items(), key=lambda x: x[1]["rate"])[:5]
    for domain, data in a_domains:
        b_data = result_b["by_domain"].get(domain, {"rate": 0, "survived": 0, "total": 0})
        delta = b_data["rate"] - data["rate"]
        print(f"    {domain:<16} A: {data['survived']:>3}/{data['total']:<3} ({data['rate']:.0%})   B: {b_data['survived']:>3}/{b_data['total']:<3} ({b_data['rate']:.0%})   {delta:+.0%}")

    print(f"{'=' * 72}")


# ── Phase Definitions ────────────────────────────────────────────────

PHASES = [
    {
        "name": "Phase 1: Warm-up (50 canaries, ~10K chars)",
        "canary_count": 50,
        "noise": False,
        "noise_ratio": 0,
        "hops": 1,
    },
    {
        "name": "Phase 2: Medium pressure (150 canaries, ~50K chars)",
        "canary_count": 150,
        "noise": True,
        "noise_ratio": 2.0,
        "hops": 1,
    },
    {
        "name": "Phase 3: Heavy pressure (500 canaries, ~200K chars)",
        "canary_count": 500,
        "noise": True,
        "noise_ratio": 3.0,
        "hops": 1,
    },
    {
        "name": "Phase 4: Cascade (500 canaries, 3-hop chain)",
        "canary_count": 500,
        "noise": True,
        "noise_ratio": 2.0,
        "hops": 3,
    },
    {
        "name": "Phase 5: Adversarial (500 canaries, 500K+ chars, high noise)",
        "canary_count": 500,
        "noise": True,
        "noise_ratio": 8.0,
        "hops": 1,
    },
]


def save_phase_data(phase_idx: int, phase: dict, canaries: list, raw_ctx: str, inst_ctx: str, output_dir: Path):
    """Save all phase data to disk."""
    phase_dir = output_dir / f"phase_{phase_idx + 1}"
    phase_dir.mkdir(parents=True, exist_ok=True)

    (phase_dir / "canaries.json").write_text(json.dumps(canaries, indent=2))
    (phase_dir / "context_raw.txt").write_text(raw_ctx)
    (phase_dir / "context_instrumented.txt").write_text(inst_ctx)
    (phase_dir / "phase_config.json").write_text(json.dumps(phase, indent=2))

    print(f"\n  Phase {phase_idx + 1} data saved:")
    print(f"    Canaries:     {len(canaries)}")
    print(f"    Raw context:  {len(raw_ctx):,} chars ({len(raw_ctx) / 4:.0f} est. tokens)")
    print(f"    Inst context: {len(inst_ctx):,} chars ({len(inst_ctx) / 4:.0f} est. tokens)")
    print(f"    Hops:         {phase['hops']}")
    print(f"    Dir:          {phase_dir}")

    return phase_dir


def main():
    output_dir = Path(__file__).parent / "stress_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("  PRIMORDIAL FORGE — A/B COMPACTION STRESS TEST GENERATOR")
    print("=" * 72)

    for i, phase in enumerate(PHASES):
        print(f"\n{'─' * 72}")
        print(f"  Generating: {phase['name']}")
        print(f"{'─' * 72}")

        canaries = generate_canaries(phase["canary_count"], seed=42 + i)
        raw_ctx = build_raw_context(canaries, add_noise=phase["noise"], noise_ratio=phase["noise_ratio"])
        inst_ctx = build_instrumented_context(canaries, add_noise=phase["noise"], noise_ratio=phase["noise_ratio"])

        save_phase_data(i, phase, canaries, raw_ctx, inst_ctx, output_dir)

    print(f"\n{'=' * 72}")
    print(f"  ALL PHASES GENERATED")
    print(f"  Output: {output_dir}")
    print(f"\n  Next: dispatch each context through subagent compaction,")
    print(f"  save summaries as summary_raw.txt / summary_instrumented.txt,")
    print(f"  then run: python3 stress_analyze.py")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
