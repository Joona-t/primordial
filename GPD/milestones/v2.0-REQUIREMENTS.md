# v2.0 Requirements: The Forgetting Agent — Close Validation Gaps

## Milestone Goal

Demonstrate that Primordial catches real problems on real workloads at real scale. Close the three validation gaps from v1.0: (1) no genuine LLM compaction tested, (2) zero natural violations detected, (3) single runtime/workload only.

## Research Questions (Active)

- **RQ2b:** Do natural violations occur at detectable rates on longer/harder/more diverse agent tasks?
- **RQ3b:** Does structural reachability hold under genuine LLM context-window compaction (not simulated)?
- **RQ4:** Do typed absence and provenance gains transfer beyond a single recursive runtime into other agent architectures?

## Acceptance Criteria

### COMP-04: Genuine LLM Compaction
- [ ] Run Primordial-instrumented agent on tasks that trigger real context-window compaction
- [ ] Measure structural reachability before/after genuine compaction events (not simulated deletion)
- [ ] Measure semantic provenance fidelity (embedding similarity of recovered vs. original artifacts)
- [ ] Sample size: >= 50 genuine compaction events across >= 20 distinct tasks
- **Acceptance:** Structural reachability measured and compared to v1.0 simulated results; semantic fidelity baseline established

### VIOL-04: Natural Violation Detection on Diverse Workloads
- [ ] Design adversarial task corpus targeting D1-D9 violation categories
- [ ] Run >= 200 instrumented agent runs across >= 3 task categories (coding, web, reasoning)
- [ ] Compare violation rates against v1.0 baseline (0/30, CP upper bound 11.6%)
- **Acceptance:** Either (a) natural violations detected and characterized, OR (b) upper bound on violation rate tightened to <= 2% with honest negative finding

### XARCH-01: Cross-Architecture Adapters
- [ ] Build forge adapter for >= 2 additional agent frameworks (from: LangGraph, CrewAI, OpenHands, AutoGen)
- [ ] Run same task corpus on each framework with forge instrumentation
- [ ] Measure same metrics (detection rate, reachability, compression) across architectures
- [ ] Compare cross-framework results in side-by-side table
- **Acceptance:** Adapters functional on >= 2 frameworks; metrics comparable; architectural differences documented

### PAPER-01: Workshop Paper Submission
- [ ] Write workshop paper on v1.0 methodology + honest negative findings
- [ ] Target: AGENT 2026 workshop at ICSE, MemAgents at ICLR, or equivalent
- [ ] Submit to arXiv for priority establishment
- **Acceptance:** Paper submitted to at least one venue + arXiv

## Carry-Forward from v1.0

- 492 passing tests (updated from 453)
- forge tools: forge_nulls.py, forge_chamber.py, forge_trace_codec.py, forge_reversible_summary.py, forge_orchestrator.py
- OpenClaw adapter with 4 interception points
- Three-tier baseline framework (uninstrumented, structured logging, forge-instrumented)
- MockLM anchor results (100% provenance, 6/6 violations, 87% compression)
- v1.0 synthesis: RQ1 PASS, RQ2 PARTIAL, RQ3 PARTIAL

## Stop/Rethink Conditions

- Genuine compaction destroys ALL provenance chains systematically (forge refs cannot survive real compaction)
- 0 natural violations on 200+ runs across diverse tasks (must reframe from detection to prevention)
- Adapters require invasive framework modifications that make the approach impractical
- Overhead exceeds 20% of baseline task completion time

## Key References

- ref-mock-experiment: MockLM benchmark anchor
- ref-v1.0-synthesis: Cross-reference and synthesis report
- Knowledge Objects (Zahn & Chana, March 2026): 60% fact loss per compression pass
- PROV-AGENT (Souza et al., 2025): Agent provenance capture
- AgentSpec (Wang & Poskitt, ICSE 2026): Formal agent action guards
- FAME Framework: 93.5% silent failure detection baseline
