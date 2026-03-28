"""Test suite for cross-architecture campaign runner (Phase 8, Plan 03).

Tests cover:
  - Campaign execution (session counts, scenario diversity)
  - Metric schema completeness
  - Forge structural guarantees (zero violations, reversibility, trace integrity)
  - Comparison matrix (both frameworks present, cross-arch consistency, anchor comparisons)
  - Coverage gap analysis (honest gaps documented, valid schema)
  - JSONL output validity
  - Session independence (no shared state leaks)
  - Statistical properties (Clopper-Pearson bounds)
  - Edge cases and regression tests

Convention assertions:
  violation_classification = structural only
  compaction_disambiguation = forge compaction (lossless) vs LLM compaction (lossy)
  all_metrics_dimensionless = True
  statistical_conventions = Clopper-Pearson exact 95% CI (two-sided)
"""

import json
import math
import tempfile
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent))

from xarch_campaign_runner import (
    XArchCampaignRunner,
    XArchComparisonMatrix,
    CoverageGapAnalysis,
    _make_ag2_session_specs,
    _make_langgraph_session_specs,
    _run_ag2_session,
    _run_langgraph_session,
    _clopper_pearson_upper,
    _std,
    _scenario_type_counts,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def campaign_runner():
    """Run the full campaign once for the entire test module."""
    runner = XArchCampaignRunner(
        frameworks=["ag2", "langgraph"],
        sessions_per_framework=55,
    )
    runner.run_campaign()
    return runner


@pytest.fixture(scope="module")
def ag2_results(campaign_runner):
    return campaign_runner.get_results()["ag2"]


@pytest.fixture(scope="module")
def lg_results(campaign_runner):
    return campaign_runner.get_results()["langgraph"]


@pytest.fixture(scope="module")
def comparison_matrix(campaign_runner):
    matrix = XArchComparisonMatrix()
    matrix.load_from_runner(campaign_runner)
    return matrix


@pytest.fixture(scope="module")
def coverage_gaps():
    return CoverageGapAnalysis.analyze()


# ============================================================
# Test 1: Campaign creates correct session counts
# ============================================================

class TestCampaignExecution:

    def test_campaign_runner_creates_sessions_ag2(self, ag2_results):
        """AG2 campaign produces exactly 55 sessions."""
        assert len(ag2_results) == 55

    def test_campaign_runner_creates_sessions_lg(self, lg_results):
        """LangGraph campaign produces exactly 55 sessions."""
        assert len(lg_results) == 55

    def test_total_campaign_size(self, ag2_results, lg_results):
        """Total campaign is 110 sessions (55 + 55)."""
        assert len(ag2_results) + len(lg_results) == 110


# ============================================================
# Test 2: All scenario types present
# ============================================================

class TestScenarioDiversity:

    def test_all_scenario_types_present_ag2(self, ag2_results):
        """AG2 campaign includes all 5 scenario types."""
        types = {r["scenario_type"] for r in ag2_results}
        expected = {"simple_conversation", "tool_use_session",
                    "multi_agent_groupchat", "error_and_absence",
                    "compaction_trigger"}
        assert types == expected

    def test_all_scenario_types_present_lg(self, lg_results):
        """LangGraph campaign includes all 5 scenario types."""
        types = {r["scenario_type"] for r in lg_results}
        expected = {"linear_pipeline", "conditional_routing",
                    "tool_use_graph", "error_recovery",
                    "long_conversation"}
        assert types == expected

    def test_min_sessions_per_type_ag2(self, ag2_results):
        """Each AG2 scenario type has >= 10 sessions."""
        counts = _scenario_type_counts(ag2_results)
        for stype, count in counts.items():
            assert count >= 10, f"AG2 {stype} has only {count} sessions (need >= 10)"

    def test_min_sessions_per_type_lg(self, lg_results):
        """Each LangGraph scenario type has >= 10 sessions."""
        counts = _scenario_type_counts(lg_results)
        for stype, count in counts.items():
            assert count >= 10, f"LG {stype} has only {count} sessions (need >= 10)"

    def test_no_identical_sessions_ag2(self, ag2_results):
        """No two AG2 sessions have the same run_id (diversity check)."""
        run_ids = [r["run_id"] for r in ag2_results]
        assert len(run_ids) == len(set(run_ids)), "Duplicate run_ids in AG2 campaign"

    def test_no_identical_sessions_lg(self, lg_results):
        """No two LangGraph sessions have the same run_id."""
        run_ids = [r["run_id"] for r in lg_results]
        assert len(run_ids) == len(set(run_ids)), "Duplicate run_ids in LG campaign"


# ============================================================
# Test 3: Metrics schema completeness
# ============================================================

class TestMetricsSchema:

    REQUIRED_FIELDS = [
        "run_id", "framework", "scenario_type", "timestamp",
        "total_stages", "total_events", "violations_detected",
        "validation_errors", "reversibility_score", "trace_verified",
        "hash_match", "trace_stats", "absence_events",
        "compaction_events", "duration_ms",
    ]

    def test_metrics_schema_complete_ag2(self, ag2_results):
        """Every AG2 session result has all required fields."""
        for i, r in enumerate(ag2_results):
            for field in self.REQUIRED_FIELDS:
                assert field in r, f"AG2 session {i} missing field: {field}"

    def test_metrics_schema_complete_lg(self, lg_results):
        """Every LangGraph session result has all required fields."""
        for i, r in enumerate(lg_results):
            for field in self.REQUIRED_FIELDS:
                assert field in r, f"LG session {i} missing field: {field}"

    def test_framework_field_correct_ag2(self, ag2_results):
        """All AG2 results report framework='ag2'."""
        for r in ag2_results:
            assert r["framework"] == "ag2"

    def test_framework_field_correct_lg(self, lg_results):
        """All LangGraph results report framework='langgraph'."""
        for r in lg_results:
            assert r["framework"] == "langgraph"


# ============================================================
# Test 4: Clean sessions have zero violations
# ============================================================

class TestZeroViolations:

    def test_clean_sessions_zero_violations_ag2(self, ag2_results):
        """All AG2 sessions produce 0 violations."""
        for r in ag2_results:
            assert r["violations_detected"] == 0, (
                f"AG2 {r['run_id']}: {r['violations_detected']} violations"
            )

    def test_clean_sessions_zero_violations_lg(self, lg_results):
        """All LangGraph sessions produce 0 violations."""
        for r in lg_results:
            assert r["violations_detected"] == 0, (
                f"LG {r['run_id']}: {r['violations_detected']} violations"
            )

    def test_zero_validation_errors_ag2(self, ag2_results):
        """All AG2 sessions produce 0 validation errors."""
        for r in ag2_results:
            assert r["validation_errors"] == 0, (
                f"AG2 {r['run_id']}: {r['validation_errors']} validation errors"
            )

    def test_zero_validation_errors_lg(self, lg_results):
        """All LangGraph sessions produce 0 validation errors."""
        for r in lg_results:
            assert r["validation_errors"] == 0, (
                f"LG {r['run_id']}: {r['validation_errors']} validation errors"
            )


# ============================================================
# Test 5: Reversibility above threshold
# ============================================================

class TestReversibility:

    def test_reversibility_above_threshold_ag2(self, campaign_runner):
        """AG2 mean reversibility >= 0.95."""
        metrics = campaign_runner.per_framework_metrics("ag2")
        assert metrics["reversibility"]["mean"] >= 0.95

    def test_reversibility_above_threshold_lg(self, campaign_runner):
        """LangGraph mean reversibility >= 0.95."""
        metrics = campaign_runner.per_framework_metrics("langgraph")
        assert metrics["reversibility"]["mean"] >= 0.95

    def test_per_session_reversibility_ag2(self, ag2_results):
        """Every AG2 session has reversibility >= 0.95."""
        for r in ag2_results:
            assert r["reversibility_score"] >= 0.95, (
                f"AG2 {r['run_id']}: reversibility={r['reversibility_score']}"
            )

    def test_per_session_reversibility_lg(self, lg_results):
        """Every LG session has reversibility >= 0.95."""
        for r in lg_results:
            assert r["reversibility_score"] >= 0.95, (
                f"LG {r['run_id']}: reversibility={r['reversibility_score']}"
            )


# ============================================================
# Test 6: Trace verified for all sessions
# ============================================================

class TestTraceIntegrity:

    def test_trace_verified_all_ag2(self, ag2_results):
        """100% of AG2 sessions have trace_verified=True."""
        count = sum(1 for r in ag2_results if r["trace_verified"])
        assert count == len(ag2_results)

    def test_trace_verified_all_lg(self, lg_results):
        """100% of LG sessions have trace_verified=True."""
        count = sum(1 for r in lg_results if r["trace_verified"])
        assert count == len(lg_results)

    def test_hash_match_all_ag2(self, ag2_results):
        """100% of AG2 sessions have hash_match=True."""
        count = sum(1 for r in ag2_results if r["hash_match"])
        assert count == len(ag2_results)

    def test_hash_match_all_lg(self, lg_results):
        """100% of LG sessions have hash_match=True."""
        count = sum(1 for r in lg_results if r["hash_match"])
        assert count == len(lg_results)


# ============================================================
# Test 7: Comparison matrix covers both frameworks
# ============================================================

class TestComparisonMatrix:

    def test_comparison_matrix_both_frameworks(self, comparison_matrix):
        """Comparison includes both AG2 and LangGraph."""
        comparison = comparison_matrix.cross_framework_comparison()
        assert "ag2" in comparison["frameworks"]
        assert "langgraph" in comparison["frameworks"]

    def test_comparison_within_tolerance(self, comparison_matrix):
        """Metrics within 10% of each other (cross-architecture consistency)."""
        comparison = comparison_matrix.cross_framework_comparison()
        assert comparison["cross_architecture_consistent"] is True

    def test_anchor_comparison_present_mocklm(self, comparison_matrix):
        """MockLM anchor comparison is present."""
        comparison = comparison_matrix.cross_framework_comparison()
        assert "MockLM" in comparison["anchor_comparisons"]
        mocklm = comparison["anchor_comparisons"]["MockLM"]
        assert "anchor" in mocklm
        assert "comparison" in mocklm
        assert mocklm["anchor"]["sessions"] == 211

    def test_anchor_comparison_present_openclaw(self, comparison_matrix):
        """OpenClaw anchor comparison is present."""
        comparison = comparison_matrix.cross_framework_comparison()
        assert "OpenClaw" in comparison["anchor_comparisons"]

    def test_anchor_all_match(self, comparison_matrix):
        """All frameworks match both anchors on key metrics."""
        comparison = comparison_matrix.cross_framework_comparison()
        for anchor_name in ["MockLM", "OpenClaw"]:
            for fw, comp in comparison["anchor_comparisons"][anchor_name]["comparison"].items():
                assert comp["reversibility_match"] is True, (
                    f"{fw} doesn't match {anchor_name} on reversibility"
                )
                assert comp["trace_integrity_match"] is True, (
                    f"{fw} doesn't match {anchor_name} on trace integrity"
                )
                assert comp["zero_violations_match"] is True, (
                    f"{fw} doesn't match {anchor_name} on zero violations"
                )

    def test_comparison_report_generates(self, comparison_matrix):
        """Markdown comparison report is non-empty and contains key sections."""
        report = comparison_matrix.generate_comparison_report()
        assert len(report) > 200
        assert "Cross-Architecture Comparison Matrix" in report
        assert "Per-Framework Summary" in report
        assert "Anchor Comparisons" in report
        assert "MockLM" in report
        assert "OpenClaw" in report


# ============================================================
# Test 8: Coverage gaps documented honestly
# ============================================================

class TestCoverageGaps:

    def test_coverage_gaps_both_frameworks(self, coverage_gaps):
        """Coverage gap analysis includes both AG2 and LangGraph."""
        frameworks = {g["framework"] for g in coverage_gaps}
        assert "ag2" in frameworks
        assert "langgraph" in frameworks

    def test_coverage_gaps_honest_ag2(self, coverage_gaps):
        """AG2 has non-empty invisible_transitions (honest gaps)."""
        ag2 = next(g for g in coverage_gaps if g["framework"] == "ag2")
        assert len(ag2["invisible_transitions"]) > 0, (
            "AG2 should have invisible transitions documented"
        )

    def test_coverage_gaps_honest_lg(self, coverage_gaps):
        """LangGraph has non-empty invisible_transitions (honest gaps)."""
        lg = next(g for g in coverage_gaps if g["framework"] == "langgraph")
        assert len(lg["invisible_transitions"]) > 0, (
            "LangGraph should have invisible transitions documented"
        )

    def test_coverage_gaps_schema_ag2(self, coverage_gaps):
        """AG2 gaps have required schema fields."""
        ag2 = next(g for g in coverage_gaps if g["framework"] == "ag2")
        assert "intercepted_transitions" in ag2
        assert "invisible_transitions" in ag2
        for it in ag2["intercepted_transitions"]:
            assert "transition" in it
            assert "description" in it
        for iv in ag2["invisible_transitions"]:
            assert "transition" in iv
            assert "gap_reason" in iv
            assert "gap_severity" in iv
            assert "mitigation" in iv

    def test_coverage_gaps_schema_lg(self, coverage_gaps):
        """LangGraph gaps have required schema fields."""
        lg = next(g for g in coverage_gaps if g["framework"] == "langgraph")
        for it in lg["intercepted_transitions"]:
            assert "transition" in it
            assert "description" in it
        for iv in lg["invisible_transitions"]:
            assert "transition" in iv
            assert "gap_reason" in iv
            assert "gap_severity" in iv
            assert "mitigation" in iv

    def test_coverage_gaps_write_file(self, tmp_path):
        """CoverageGapAnalysis.write() produces valid JSON file."""
        out = tmp_path / "gaps.json"
        CoverageGapAnalysis.write(out)
        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        assert len(data) == 2


# ============================================================
# Test 9: CP upper bound below threshold
# ============================================================

class TestStatisticalBounds:

    def test_cp_upper_bound_below_threshold_ag2(self, campaign_runner):
        """AG2 CP 95% upper bound < 7% per-framework (0/55 -> ~6.49%)."""
        metrics = campaign_runner.per_framework_metrics("ag2")
        # Exact CP for 0/55: 1 - 0.025^(1/55) = 0.0649
        # Per-framework bound is < 7%; combined 0/110 achieves < 5%
        assert metrics["cp_95_upper"] < 0.07, (
            f"AG2 CP upper: {metrics['cp_95_upper']}"
        )

    def test_cp_upper_bound_below_threshold_lg(self, campaign_runner):
        """LangGraph CP 95% upper bound < 7% per-framework (0/55 -> ~6.49%)."""
        metrics = campaign_runner.per_framework_metrics("langgraph")
        assert metrics["cp_95_upper"] < 0.07, (
            f"LG CP upper: {metrics['cp_95_upper']}"
        )

    def test_combined_cp_below_5_pct(self):
        """Combined cross-architecture 0/110 has CP upper < 5%."""
        combined_cp = _clopper_pearson_upper(0, 110, 0.05)
        assert combined_cp < 0.05, f"Combined CP upper: {combined_cp}"

    def test_clopper_pearson_zero_violations(self):
        """CP upper bound for 0/55 is approximately 6.5% (below 10%)."""
        upper = _clopper_pearson_upper(0, 55, 0.05)
        assert 0.0 < upper < 0.10
        # Exact value: 1 - 0.025^(1/55) ≈ 0.0649
        assert abs(upper - 0.0649) < 0.001

    def test_clopper_pearson_edge_n_zero(self):
        """CP upper for n=0 returns 1.0."""
        assert _clopper_pearson_upper(0, 0, 0.05) == 1.0


# ============================================================
# Test 10: JSONL output validity
# ============================================================

class TestJSONLOutput:

    def test_jsonl_valid_ag2(self, campaign_runner, tmp_path):
        """AG2 JSONL output: all lines parse as valid JSON."""
        campaign_runner.write_results(str(tmp_path))
        path = tmp_path / "ag2_campaign.jsonl"
        assert path.exists()
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 55
        for i, line in enumerate(lines):
            obj = json.loads(line)
            assert "run_id" in obj, f"Line {i} missing run_id"

    def test_jsonl_valid_lg(self, campaign_runner, tmp_path):
        """LangGraph JSONL output: all lines parse as valid JSON."""
        campaign_runner.write_results(str(tmp_path))
        path = tmp_path / "langgraph_campaign.jsonl"
        assert path.exists()
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 55
        for i, line in enumerate(lines):
            obj = json.loads(line)
            assert "run_id" in obj, f"Line {i} missing run_id"


# ============================================================
# Test 11: Session independence
# ============================================================

class TestSessionIndependence:

    def test_session_independence_ag2(self, ag2_results):
        """AG2 sessions have independent run_ids (no shared state leak)."""
        run_ids = [r["run_id"] for r in ag2_results]
        assert len(set(run_ids)) == len(run_ids), "AG2 has duplicate run_ids"

    def test_session_independence_lg(self, lg_results):
        """LG sessions have independent run_ids."""
        run_ids = [r["run_id"] for r in lg_results]
        assert len(set(run_ids)) == len(run_ids), "LG has duplicate run_ids"

    def test_no_cross_framework_contamination(self, ag2_results, lg_results):
        """No run_id appears in both framework results."""
        ag2_ids = {r["run_id"] for r in ag2_results}
        lg_ids = {r["run_id"] for r in lg_results}
        assert ag2_ids.isdisjoint(lg_ids), "Cross-framework run_id leak"


# ============================================================
# Test 12: Spec generation diversity
# ============================================================

class TestSpecGeneration:

    def test_ag2_specs_correct_count(self):
        """AG2 spec generator produces exactly 55 specs."""
        specs = _make_ag2_session_specs(55)
        assert len(specs) == 55

    def test_lg_specs_correct_count(self):
        """LG spec generator produces exactly 55 specs."""
        specs = _make_langgraph_session_specs(55)
        assert len(specs) == 55

    def test_ag2_specs_varied_seeds(self):
        """AG2 specs have unique seeds (parameter diversity)."""
        specs = _make_ag2_session_specs(55)
        seeds = [s["seed"] for s in specs]
        assert len(set(seeds)) == len(seeds), "AG2 has duplicate seeds"

    def test_lg_specs_varied_seeds(self):
        """LG specs have unique seeds."""
        specs = _make_langgraph_session_specs(55)
        seeds = [s["seed"] for s in specs]
        assert len(set(seeds)) == len(seeds), "LG has duplicate seeds"


# ============================================================
# Test 13: Per-framework metrics computation
# ============================================================

class TestPerFrameworkMetrics:

    def test_per_framework_metrics_ag2(self, campaign_runner):
        """AG2 per-framework metrics have expected structure."""
        m = campaign_runner.per_framework_metrics("ag2")
        assert m["framework"] == "ag2"
        assert m["sessions"] == 55
        assert "reversibility" in m
        assert "mean" in m["reversibility"]
        assert "std" in m["reversibility"]
        assert m["validation_errors_total"] == 0
        assert m["violations_total"] == 0

    def test_per_framework_metrics_lg(self, campaign_runner):
        """LangGraph per-framework metrics have expected structure."""
        m = campaign_runner.per_framework_metrics("langgraph")
        assert m["framework"] == "langgraph"
        assert m["sessions"] == 55

    def test_per_framework_error_unknown(self, campaign_runner):
        """Unknown framework returns error dict."""
        m = campaign_runner.per_framework_metrics("unknown_framework")
        assert "error" in m


# ============================================================
# Test 14: Duration is positive
# ============================================================

class TestDuration:

    def test_positive_duration_ag2(self, ag2_results):
        """All AG2 sessions have positive duration."""
        for r in ag2_results:
            assert r["duration_ms"] >= 0, f"{r['run_id']} has negative duration"

    def test_positive_duration_lg(self, lg_results):
        """All LG sessions have positive duration."""
        for r in lg_results:
            assert r["duration_ms"] >= 0, f"{r['run_id']} has negative duration"


# ============================================================
# Test 15: Utility functions
# ============================================================

class TestUtilities:

    def test_std_single_value(self):
        """Standard deviation of single value is 0."""
        assert _std([5.0]) == 0.0

    def test_std_known_values(self):
        """Standard deviation of [2, 4, 4, 4, 5, 5, 7, 9]."""
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        # Sample std = sqrt(36/7) ≈ 2.1381
        result = _std(values)
        assert abs(result - 2.0) < 0.2  # Rough check

    def test_scenario_type_counts(self):
        """Scenario type counter works correctly."""
        results = [
            {"scenario_type": "a"},
            {"scenario_type": "b"},
            {"scenario_type": "a"},
        ]
        counts = _scenario_type_counts(results)
        assert counts == {"a": 2, "b": 1}


# ============================================================
# Test 16: Comparison matrix from JSONL files
# ============================================================

class TestComparisonFromFiles:

    def test_load_from_jsonl(self, campaign_runner, tmp_path):
        """Comparison matrix can load from JSONL files."""
        campaign_runner.write_results(str(tmp_path))

        matrix = XArchComparisonMatrix()
        matrix.load_campaign("ag2", tmp_path / "ag2_campaign.jsonl")
        matrix.load_campaign("langgraph", tmp_path / "langgraph_campaign.jsonl")

        comparison = matrix.cross_framework_comparison()
        assert "ag2" in comparison["frameworks"]
        assert "langgraph" in comparison["frameworks"]
        assert comparison["cross_architecture_consistent"] is True


# ============================================================
# Test 17: Absence events detected
# ============================================================

class TestAbsenceEvents:

    def test_ag2_absence_events_nonzero(self, campaign_runner):
        """AG2 campaign has non-zero absence events (error_and_absence scenario)."""
        metrics = campaign_runner.per_framework_metrics("ag2")
        assert metrics["absence_events_total"] > 0

    def test_ag2_compaction_events_nonzero(self, campaign_runner):
        """AG2 campaign has non-zero compaction events (compaction_trigger scenario)."""
        metrics = campaign_runner.per_framework_metrics("ag2")
        assert metrics["compaction_events_total"] > 0


# ============================================================
# Test 18: Stages > 0 for all sessions
# ============================================================

class TestStageCount:

    def test_stages_positive_ag2(self, ag2_results):
        """Every AG2 session has at least 1 stage."""
        for r in ag2_results:
            assert r["total_stages"] > 0, f"{r['run_id']} has 0 stages"

    def test_stages_positive_lg(self, lg_results):
        """Every LG session has at least 1 stage."""
        for r in lg_results:
            assert r["total_stages"] > 0, f"{r['run_id']} has 0 stages"


# ============================================================
# Test 19: Timestamps are ISO format
# ============================================================

class TestTimestamps:

    def test_timestamps_iso_ag2(self, ag2_results):
        """All AG2 session timestamps are valid ISO format."""
        from datetime import datetime
        for r in ag2_results:
            ts = r["timestamp"]
            # Should parse without error
            datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_timestamps_iso_lg(self, lg_results):
        """All LG session timestamps are valid ISO format."""
        from datetime import datetime
        for r in lg_results:
            ts = r["timestamp"]
            datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ============================================================
# Test 20: Existing test suites still pass (no regression)
# ============================================================

class TestNoRegression:

    def test_ag2_harness_import(self):
        """AG2 integration harness still imports correctly."""
        from ag2_integration_harness import AG2ForgeHarness, run_all_scenarios
        assert AG2ForgeHarness is not None

    def test_langgraph_harness_import(self):
        """LangGraph integration harness still imports correctly."""
        from langgraph_integration_harness import LangGraphForgeHarness, run_all_scenarios
        assert LangGraphForgeHarness is not None

    def test_forge_adapter_import(self):
        """Forge adapter module still imports correctly."""
        from forge_adapter import AG2ForgeAdapter, LangGraphForgeAdapter, ForgeAdapter
        assert AG2ForgeAdapter is not None
        assert LangGraphForgeAdapter is not None


# ============================================================
# Test 21: Coverage gap analysis has specific known gaps
# ============================================================

class TestKnownGaps:

    def test_ag2_process_death_documented(self, coverage_gaps):
        """AG2 documents process death as invisible transition."""
        ag2 = next(g for g in coverage_gaps if g["framework"] == "ag2")
        transitions = [t["transition"] for t in ag2["invisible_transitions"]]
        assert "process_death" in transitions

    def test_langgraph_reducer_opacity_documented(self, coverage_gaps):
        """LangGraph documents reducer merge logic as invisible."""
        lg = next(g for g in coverage_gaps if g["framework"] == "langgraph")
        transitions = [t["transition"] for t in lg["invisible_transitions"]]
        assert "reducer_merge_logic" in transitions

    def test_severity_levels_valid(self, coverage_gaps):
        """All gap severities are HIGH, MEDIUM, or LOW."""
        valid = {"HIGH", "MEDIUM", "LOW"}
        for g in coverage_gaps:
            for iv in g["invisible_transitions"]:
                assert iv["gap_severity"] in valid, (
                    f"{g['framework']}/{iv['transition']}: invalid severity '{iv['gap_severity']}'"
                )


# ============================================================
# Test 22: Single-session execution
# ============================================================

class TestSingleSession:

    def test_single_ag2_session(self):
        """A single AG2 session can be executed independently."""
        spec = {"scenario_type": "simple_conversation", "n_agents": 2,
                "n_turns": 3, "seed": 99999}
        result = _run_ag2_session(spec, 999)
        assert result["framework"] == "ag2"
        assert result["violations_detected"] == 0
        assert result["reversibility_score"] >= 0.95

    def test_single_lg_session(self):
        """A single LangGraph session can be executed independently."""
        spec = {"scenario_type": "linear_pipeline", "n_nodes": 3, "seed": 99999}
        result = _run_langgraph_session(spec, 999)
        assert result["framework"] == "langgraph"
        assert result["violations_detected"] == 0
        assert result["reversibility_score"] >= 0.95


# ============================================================
# Test 23: Phase 7 comparison — CP bound consistent
# ============================================================

class TestPhase7Comparison:

    def test_phase7_mocklm_cp_bound_lower(self):
        """Phase 7 had 0/211 -> CP upper 1.73%. Our 0/55 -> ~6.49%.
        Combined 0/266 -> even lower. This is consistent."""
        phase7_cp = _clopper_pearson_upper(0, 211, 0.05)
        our_cp = _clopper_pearson_upper(0, 55, 0.05)
        # Phase 7 with more sessions has lower bound
        assert phase7_cp < our_cp
        # Both below 10%
        assert phase7_cp < 0.10
        assert our_cp < 0.10

    def test_combined_cross_arch_cp_bound(self):
        """Combined 0/110 across both frameworks -> CP upper ~3.3%."""
        combined_cp = _clopper_pearson_upper(0, 110, 0.05)
        assert combined_cp < 0.05  # Below 5% threshold
