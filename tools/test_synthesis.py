"""
Test suite for tools/synthesis.py -- synthesis data loading, table
computation, consistency checks, and anchor verification.

Tests categories:
  1. Data loading (structure validation, error handling)
  2. Table completeness (12 rows, no None, all columns)
  3. Consistency (three-tier ordering, pre-compaction match, rate sums)
  4. Anchor (MockLM ceiling values)
  5. Gap arithmetic (ceiling - forge computations)

Run: python3 -m pytest tools/test_synthesis.py -v
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

# Import the synthesis module
from tools.synthesis import (
    MOCKLM_CEILING,
    compute_gaps,
    compute_side_by_side_table,
    load_baseline_data,
    load_campaign_data,
    load_compaction_data,
    run_consistency_checks,
)

# ── Project root ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def campaign():
    """Load campaign data once for all tests in this module."""
    return load_campaign_data()


@pytest.fixture(scope="module")
def compaction():
    """Load compaction data once for all tests in this module."""
    return load_compaction_data()


@pytest.fixture(scope="module")
def baselines():
    """Load baseline data once for all tests in this module."""
    return load_baseline_data()


@pytest.fixture(scope="module")
def table(campaign, compaction, baselines):
    """Compute the side-by-side table once for all tests."""
    return compute_side_by_side_table(campaign, compaction, baselines)


@pytest.fixture(scope="module")
def gaps(table):
    """Compute gaps once for all tests."""
    return compute_gaps(table)


@pytest.fixture(scope="module")
def checks(table, campaign, compaction, baselines):
    """Run consistency checks once for all tests."""
    return run_consistency_checks(table, campaign, compaction, baselines)


# ═══════════════════════════════════════════════════════════════════════
# 1. DATA LOADING TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestLoadCampaignData:
    """Tests for load_campaign_data() structure validation."""

    def test_load_campaign_data_structure(self, campaign):
        """campaign-report.json loads and has required top-level keys."""
        assert "per_type" in campaign
        assert "aggregate" in campaign
        assert "clean" in campaign
        assert "anchor" in campaign
        assert "source_file" in campaign

    def test_campaign_per_type_has_all_types(self, campaign):
        """Per-type detection rates exist for all 9 fault types."""
        expected = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"}
        assert set(campaign["per_type"].keys()) == expected

    def test_campaign_per_type_fields(self, campaign):
        """Each per-type entry has required fields."""
        for dtype, entry in campaign["per_type"].items():
            assert "forge_detected" in entry, f"{dtype} missing forge_detected"
            assert "forge_total" in entry, f"{dtype} missing forge_total"
            assert "forge_rate" in entry, f"{dtype} missing forge_rate"
            assert "forge_ci" in entry, f"{dtype} missing forge_ci"
            assert "uninstrumented_rate" in entry, f"{dtype} missing uninstrumented_rate"
            assert "structured_rate" in entry, f"{dtype} missing structured_rate"

    def test_campaign_aggregate_fields(self, campaign):
        """Aggregate detection has required fields."""
        agg = campaign["aggregate"]
        assert "forge_detected" in agg
        assert "forge_total" in agg
        assert "forge_rate" in agg
        assert "forge_ci" in agg

    def test_campaign_clean_fields(self, campaign):
        """Clean summary has required fields."""
        clean = campaign["clean"]
        assert "n_runs" in clean
        assert "fpr" in clean
        assert "fpr_ci" in clean
        assert "natural_violations" in clean


class TestLoadCompactionData:
    """Tests for load_compaction_data() structure validation."""

    def test_load_compaction_data_structure(self, compaction):
        """compaction-report.json loads and has required keys."""
        assert "pre_compaction" in compaction
        assert "deletion_sweep" in compaction
        assert "violation_regression" in compaction
        assert "backtracking" in compaction
        assert "source_file" in compaction

    def test_compaction_deletion_sweep_not_empty(self, compaction):
        """Deletion sweep has at least one entry."""
        assert len(compaction["deletion_sweep"]) > 0

    def test_compaction_sweep_fields(self, compaction):
        """Each deletion sweep entry has required fields."""
        for entry in compaction["deletion_sweep"]:
            assert "fraction" in entry
            assert "structural_reachability" in entry
            assert "bfs_reachability" in entry
            assert "above_backtracking_threshold" in entry


class TestLoadBaselineData:
    """Tests for load_baseline_data() structure validation."""

    def test_load_baseline_data_structure(self, baselines):
        """baseline-report.json loads and has required keys."""
        assert "uninstrumented" in baselines
        assert "structured" in baselines
        assert "forge" in baselines
        assert "source_file" in baselines

    def test_baseline_uninstrumented_fields(self, baselines):
        """Uninstrumented tier has required fields."""
        u = baselines["uninstrumented"]
        assert "reachability" in u
        assert "depth" in u
        assert "detection" in u

    def test_baseline_forge_fields(self, baselines):
        """Forge tier has required fields."""
        f = baselines["forge"]
        assert "reachability" in f
        assert "depth" in f
        assert "compression" in f


class TestLoadErrorHandling:
    """Tests for error handling on missing/corrupt files."""

    def test_load_missing_file_raises(self):
        """Missing file raises FileNotFoundError."""
        fake_path = Path("/nonexistent/path/data.json")
        with pytest.raises(FileNotFoundError):
            load_campaign_data(fake_path)

    def test_load_corrupt_json_raises(self):
        """Malformed JSON raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json content")
            tmp_path = Path(f.name)
        try:
            with pytest.raises(ValueError, match="Malformed JSON"):
                load_campaign_data(tmp_path)
        finally:
            os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════
# 2. TABLE COMPLETENESS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestTableCompleteness:
    """Tests for side-by-side table structure and completeness."""

    def test_table_has_12_rows(self, table):
        """Exactly 12 rows in the side-by-side table."""
        assert len(table) == 12

    def test_no_none_values(self, table):
        """No None in any cell (N/A string is acceptable)."""
        for i, row in enumerate(table):
            for key, value in row.items():
                assert value is not None, (
                    f"Row {i + 1} ({row['observable']}) has None in '{key}'"
                )

    def test_all_rows_have_required_columns(self, table):
        """Every row has all 9 required columns."""
        required = {
            "observable",
            "mockLM_ceiling",
            "uninstrumented_floor",
            "structured_logging",
            "forge_instrumented",
            "gap_ceiling_forge",
            "differential_forge_floor",
            "source_file",
            "source_field",
        }
        for i, row in enumerate(table):
            missing = required - set(row.keys())
            assert not missing, (
                f"Row {i + 1} ({row['observable']}) missing columns: {missing}"
            )

    def test_observable_names_unique(self, table):
        """All observable names are unique."""
        names = [row["observable"] for row in table]
        assert len(names) == len(set(names))


# ═══════════════════════════════════════════════════════════════════════
# 3. CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestConsistency:
    """Tests for data consistency across sources."""

    def test_three_tier_ordering(self, checks):
        """forge >= structured >= uninstrumented for detection, reachability, depth."""
        assert checks["three_tier_ordering"] is True

    def test_pre_compaction_reachability_match(self, checks):
        """Phase 2 baseline = Phase 4 pre-compaction = MockLM = 1.0."""
        assert checks["pre_compaction_match"] is True

    def test_detection_rate_aggregate(self, campaign):
        """40/90 = 0.4444... matches aggregate from JSON."""
        agg_rate = campaign["aggregate"]["forge_rate"]
        expected = 40 / 90
        assert abs(agg_rate - expected) < 1e-10

    def test_detection_rate_sum(self, checks):
        """sum(per_type_detected) = 40."""
        assert checks["detection_rate_sum"] is True
        assert checks["detection_rate_sum_detail"]["sum_per_type"] == 40
        assert checks["detection_rate_sum_detail"]["aggregate"] == 40

    def test_fpr_zero(self, campaign):
        """FPR = 0.0 from clean results."""
        assert campaign["clean"]["fpr"] == 0.0

    def test_natural_violations_zero(self, campaign):
        """0 natural violations from clean results."""
        assert campaign["clean"]["natural_violations"] == 0

    def test_detection_rate_arithmetic(self, checks):
        """Aggregate rate matches expected 40/90."""
        assert checks["detection_rate_arithmetic"] is True


# ═══════════════════════════════════════════════════════════════════════
# 4. ANCHOR TESTS (MockLM ceiling)
# ═══════════════════════════════════════════════════════════════════════

class TestAnchor:
    """Tests for MockLM ceiling values in the table."""

    def test_mockLM_detection_ceiling(self, table):
        """Table row 1 MockLM = '6/6'."""
        row1 = table[0]
        assert row1["mockLM_ceiling"] == "6/6"

    def test_mockLM_reachability_ceiling(self, table):
        """Table row 6 MockLM = '1.0'."""
        row6 = table[5]
        assert row6["mockLM_ceiling"] == "1.0"

    def test_mockLM_compression_ceiling(self, table):
        """Table row 10 MockLM = '1.096x'."""
        row10 = table[9]
        assert row10["mockLM_ceiling"] == "1.096x"

    def test_mockLM_constants_source(self):
        """MockLM ceiling constants reference experiment_results.json."""
        assert "experiment_results.json" in MOCKLM_CEILING["source"]


# ═══════════════════════════════════════════════════════════════════════
# 5. GAP ARITHMETIC TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestGapArithmetic:
    """Tests for gap computation correctness."""

    def test_gap_d1_d6(self, gaps):
        """D1-D6 detection gap: 6 - 3 = 3."""
        d1_d6_gap = next(g for g in gaps if "D1-D6" in g["observable"])
        assert d1_d6_gap["gap"] == 3

    def test_gap_pre_compaction_reachability(self, gaps):
        """Pre-compaction reachability gap: 1.0 - 1.0 = 0."""
        reach_gap = next(g for g in gaps if "reachability" in g["observable"])
        assert reach_gap["gap"] == 0.0

    def test_gap_compression(self, gaps):
        """Compression gap: 1.1959 - 1.096 = 0.0999."""
        comp_gap = next(g for g in gaps if "compression" in g["observable"])
        assert abs(comp_gap["gap"] - 0.0999) < 0.0001

    def test_all_gaps_classified(self, gaps):
        """Every gap has a classification (zero or explained)."""
        for gap in gaps:
            assert gap["classification"] in ("zero", "explained", "unexplained")

    def test_all_gaps_have_explanation(self, gaps):
        """Every gap has a non-empty explanation."""
        for gap in gaps:
            assert len(gap["explanation"]) > 0

    def test_differential_detection(self, table):
        """Differential: forge - uninstrumented detection = +3 types (D1-D6)."""
        row1 = table[0]
        assert row1["differential_forge_floor"] == "+3 types"

    def test_differential_aggregate(self, table):
        """Differential: forge - uninstrumented aggregate = +0.444..."""
        row3 = table[2]
        assert row3["differential_forge_floor"].startswith("+0.4444")


# ═══════════════════════════════════════════════════════════════════════
# 6. INTEGRATION TEST: END-TO-END
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests."""

    def test_json_output_exists_and_parses(self):
        """synthesis-report.json exists and parses cleanly."""
        json_path = PROJECT_ROOT / "data" / "synthesis" / "synthesis-report.json"
        assert json_path.exists(), f"JSON output missing: {json_path}"
        with open(json_path) as f:
            report = json.load(f)
        assert "side_by_side_table" in report
        assert "gaps" in report
        assert "consistency_checks" in report

    def test_markdown_output_exists(self):
        """side-by-side-table.md exists and has table content."""
        md_path = PROJECT_ROOT / "data" / "synthesis" / "side-by-side-table.md"
        assert md_path.exists(), f"Markdown output missing: {md_path}"
        content = md_path.read_text()
        # Should have the header row
        assert "Observable" in content
        assert "MockLM Ceiling" in content
        # Should have at least 12 data rows
        table_rows = [
            line for line in content.split("\n")
            if line.startswith("| ") and "---" not in line and "Observable" not in line
            and "Row" not in line
        ]
        assert len(table_rows) >= 12

    def test_consistency_checks_all_pass(self, checks):
        """All automated consistency checks pass."""
        for key, value in checks.items():
            if not key.endswith("_detail"):
                assert value is True, f"Consistency check '{key}' failed"

    def test_source_traceability_complete(self, table):
        """Every row has non-empty source_file and source_field."""
        for i, row in enumerate(table):
            assert row["source_file"], f"Row {i + 1} missing source_file"
            assert row["source_field"], f"Row {i + 1} missing source_field"
