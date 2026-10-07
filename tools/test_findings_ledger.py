"""Tests for findings_ledger.py."""

import json
import tempfile
import unittest
from pathlib import Path

from findings_ledger import (
    Finding,
    FindingRecord,
    FindingsLedger,
    seed_v1_findings,
    CATEGORIES,
    VERDICTS,
    CONFIDENCE,
)


class TestFinding(unittest.TestCase):

    def test_valid_finding(self):
        f = Finding(phase=6, category="compaction", title="test", description="desc")
        f.validate()  # should not raise

    def test_invalid_category(self):
        f = Finding(phase=6, category="bogus", title="t", description="d")
        with self.assertRaises(ValueError):
            f.validate()

    def test_invalid_verdict(self):
        f = Finding(phase=6, category="compaction", title="t", description="d", verdict="maybe")
        with self.assertRaises(ValueError):
            f.validate()

    def test_invalid_confidence(self):
        f = Finding(phase=6, category="compaction", title="t", description="d", confidence="idk")
        with self.assertRaises(ValueError):
            f.validate()

    def test_empty_title_rejected(self):
        f = Finding(phase=6, category="compaction", title="", description="d")
        with self.assertRaises(ValueError):
            f.validate()

    def test_empty_description_rejected(self):
        f = Finding(phase=6, category="compaction", title="t", description="")
        with self.assertRaises(ValueError):
            f.validate()

    def test_all_categories_valid(self):
        for cat in CATEGORIES:
            f = Finding(phase=1, category=cat, title="t", description="d")
            f.validate()

    def test_all_verdicts_valid(self):
        for v in VERDICTS:
            f = Finding(phase=1, category="compaction", title="t", description="d", verdict=v)
            f.validate()


class TestFindingRecord(unittest.TestCase):

    def test_from_finding(self):
        f = Finding(phase=6, category="compaction", title="test", description="desc")
        rec = FindingRecord.from_finding(f, 1)
        self.assertEqual(rec.id, "F-0001")
        self.assertIn("2026", rec.timestamp)
        self.assertEqual(rec.finding["phase"], 6)
        self.assertEqual(len(rec.content_hash), 16)

    def test_sequential_ids(self):
        f = Finding(phase=6, category="compaction", title="t", description="d")
        r1 = FindingRecord.from_finding(f, 1)
        r2 = FindingRecord.from_finding(f, 42)
        self.assertEqual(r1.id, "F-0001")
        self.assertEqual(r2.id, "F-0042")

    def test_different_content_different_hash(self):
        f1 = Finding(phase=6, category="compaction", title="a", description="d")
        f2 = Finding(phase=6, category="compaction", title="b", description="d")
        r1 = FindingRecord.from_finding(f1, 1)
        r2 = FindingRecord.from_finding(f2, 2)
        self.assertNotEqual(r1.content_hash, r2.content_hash)


class TestFindingsLedger(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger = FindingsLedger(data_dir=self.tmpdir)

    def test_record_creates_file(self):
        f = Finding(phase=6, category="compaction", title="t", description="d")
        self.ledger.record(f)
        path = Path(self.tmpdir) / "findings.jsonl"
        self.assertTrue(path.exists())
        content = path.read_text().strip()
        self.assertEqual(len(content.split("\n")), 1)

    def test_record_returns_record(self):
        f = Finding(phase=6, category="compaction", title="t", description="d")
        rec = self.ledger.record(f)
        self.assertEqual(rec.id, "F-0001")

    def test_sequential_records(self):
        for i in range(5):
            f = Finding(phase=6, category="compaction", title=f"t{i}", description="d")
            rec = self.ledger.record(f)
        self.assertEqual(rec.id, "F-0005")

    def test_all_records(self):
        for i in range(3):
            self.ledger.record(Finding(phase=6, category="compaction", title=f"t{i}", description="d"))
        records = self.ledger.all_records()
        self.assertEqual(len(records), 3)

    def test_query_by_phase(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d"))
        self.ledger.record(Finding(phase=7, category="violation", title="b", description="d"))
        self.ledger.record(Finding(phase=6, category="spf", title="c", description="d"))
        results = self.ledger.query(phase=6)
        self.assertEqual(len(results), 2)

    def test_query_by_category(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d"))
        self.ledger.record(Finding(phase=6, category="violation", title="b", description="d"))
        results = self.ledger.query(category="violation")
        self.assertEqual(len(results), 1)

    def test_query_by_verdict(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d", verdict="positive"))
        self.ledger.record(Finding(phase=6, category="compaction", title="b", description="d", verdict="negative"))
        self.ledger.record(Finding(phase=6, category="compaction", title="c", description="d", verdict="negative"))
        negatives = self.ledger.query(verdict="negative")
        self.assertEqual(len(negatives), 2)

    def test_query_by_tag(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d", tags=["COMP-04"]))
        self.ledger.record(Finding(phase=6, category="compaction", title="b", description="d", tags=["SPF-01"]))
        results = self.ledger.query(tag="COMP-04")
        self.assertEqual(len(results), 1)

    def test_query_by_rq(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d", rq="RQ3b"))
        self.ledger.record(Finding(phase=7, category="violation", title="b", description="d", rq="RQ2b"))
        results = self.ledger.query(rq="RQ3b")
        self.assertEqual(len(results), 1)

    def test_query_multi_filter(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d", verdict="positive"))
        self.ledger.record(Finding(phase=6, category="compaction", title="b", description="d", verdict="negative"))
        self.ledger.record(Finding(phase=7, category="compaction", title="c", description="d", verdict="positive"))
        results = self.ledger.query(phase=6, verdict="positive")
        self.assertEqual(len(results), 1)

    def test_count(self):
        for i in range(5):
            self.ledger.record(Finding(phase=6, category="compaction", title=f"t{i}", description="d"))
        self.assertEqual(self.ledger.count(), 5)
        self.assertEqual(self.ledger.count(phase=6), 5)
        self.assertEqual(self.ledger.count(phase=7), 0)

    def test_summary(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="a", description="d", verdict="positive"))
        self.ledger.record(Finding(phase=6, category="negative", title="b", description="d", verdict="negative"))
        summary = self.ledger.summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["positive_findings"], 1)
        self.assertEqual(summary["negative_findings"], 1)
        self.assertEqual(summary["by_category"]["compaction"], 1)

    def test_empty_ledger_summary(self):
        summary = self.ledger.summary()
        self.assertEqual(summary["total"], 0)

    def test_export_markdown(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="test finding", description="details here"))
        report = self.ledger.export_markdown()
        self.assertIn("# Research Findings Ledger", report)
        self.assertIn("test finding", report)
        self.assertIn("details here", report)

    def test_export_markdown_to_file(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="t", description="d"))
        path = Path(self.tmpdir) / "report.md"
        self.ledger.export_markdown(str(path))
        self.assertTrue(path.exists())
        self.assertIn("Research Findings", path.read_text())

    def test_export_json(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="t", description="d"))
        result = self.ledger.export_json()
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(len(result["findings"]), 1)

    def test_persistence_across_instances(self):
        self.ledger.record(Finding(phase=6, category="compaction", title="t", description="d"))
        ledger2 = FindingsLedger(data_dir=self.tmpdir)
        self.assertEqual(len(ledger2.all_records()), 1)
        rec = ledger2.record(Finding(phase=7, category="violation", title="t2", description="d"))
        self.assertEqual(rec.id, "F-0002")  # continues sequence

    def test_record_many(self):
        findings = [
            Finding(phase=6, category="compaction", title=f"t{i}", description="d")
            for i in range(3)
        ]
        records = self.ledger.record_many(findings)
        self.assertEqual(len(records), 3)
        self.assertEqual(self.ledger.count(), 3)


class TestSeedV1(unittest.TestCase):

    def test_seed_creates_5_findings(self):
        tmpdir = tempfile.mkdtemp()
        ledger = FindingsLedger(data_dir=tmpdir)
        records = seed_v1_findings(ledger)
        self.assertEqual(len(records), 5)
        self.assertEqual(ledger.count(), 5)

    def test_seed_includes_negative(self):
        tmpdir = tempfile.mkdtemp()
        ledger = FindingsLedger(data_dir=tmpdir)
        seed_v1_findings(ledger)
        negatives = ledger.query(verdict="negative")
        self.assertEqual(len(negatives), 1)
        self.assertIn("Zero natural violations", negatives[0]["finding"]["title"])

    def test_seed_covers_phases_1_through_5(self):
        tmpdir = tempfile.mkdtemp()
        ledger = FindingsLedger(data_dir=tmpdir)
        seed_v1_findings(ledger)
        phases = set(r["finding"]["phase"] for r in ledger.all_records())
        self.assertIn(1, phases)
        self.assertIn(3, phases)
        self.assertIn(4, phases)
        self.assertIn(5, phases)


if __name__ == "__main__":
    unittest.main()
