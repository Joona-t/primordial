"""
test_forge_v1_convergence.py — Regression tests for v1 convergence.

Proves that tool-generated outputs pass v1 validation:
1. SummaryView from create_summary_view
2. Absence records from forge_nulls
3. Dictionary loading/normalization
4. Unresolved ref behavior
"""

from __future__ import annotations

import json
import unittest
import warnings
from pathlib import Path

from forge_nulls import (
    AbsenceState,
    ForgeNullError,
    V1_ABSENCE_STATES,
    absent,
    normalize_absence_state,
    normalize_record,
    validate_record,
)
from forge_reversible_summary import (
    ForgeRefError,
    create_summary_view,
    validate_summary_view,
)
from forge_v1_bridge import (
    get_legacy_usage_counts,
    get_legacy_usage_events,
    get_validator_source,
    load_protocol_dict,
    normalize_code,
    reset_legacy_usage_counts,
    validate_absence_field_v1,
    validate_dict_entry_v1,
    validate_summary_view_v1,
)


class TestSummaryViewV1(unittest.TestCase):
    """Tool-generated v1 SummaryView passes the v1 validator."""

    def test_create_summary_view_passes_v1(self):
        sv = create_summary_view(
            summary_id="artifact:run52:summary:builder:v1",
            text="Builder proposes strict fail-closed JSON boundaries.",
            source_refs=[
                "artifact:run52:builder_output:r1",
                "artifact:run52:architect_plan:r1",
            ],
            view_of="artifact:run52:builder_output:r1",
        )
        errors = validate_summary_view_v1(sv)
        self.assertEqual(errors, [], f"v1 validation errors: {errors}")

    def test_summary_view_has_required_fields(self):
        sv = create_summary_view(
            summary_id="artifact:run99:summary:v1",
            text="Test summary.",
            source_refs=["artifact:run99:output:r1"],
            view_of="artifact:run99:output:r1",
        )
        for field in ["id", "type", "schema_version", "summary", "source_refs", "view_of", "summary_hash"]:
            self.assertIn(field, sv, f"Missing field: {field}")
        self.assertEqual(sv["type"], "summary_view")
        self.assertEqual(sv["schema_version"], "forge.internal.v1")

    def test_create_summary_view_bridge_assertion_runs(self):
        sv = create_summary_view(
            summary_id="artifact:run200:summary:v1",
            text="Bridge assertion check.",
            source_refs=["artifact:run200:output:r1"],
            view_of="artifact:run200:output:r1",
        )
        self.assertEqual(sv["schema_version"], "forge.internal.v1")

    def test_summary_view_source_refs_are_structured(self):
        sv = create_summary_view(
            summary_id="artifact:run99:summary:v1",
            text="Test.",
            source_refs=["artifact:run99:output:r1"],
            view_of="artifact:run99:output:r1",
        )
        for ref in sv["source_refs"]:
            self.assertIsInstance(ref, dict)
            self.assertIn("ref", ref)
            self.assertIn("state", ref)
            self.assertEqual(ref["state"], "resolved")

    def test_summary_view_hash_is_sha256(self):
        text = "Deterministic hash test."
        sv = create_summary_view(
            summary_id="artifact:run99:summary:v1",
            text=text,
            source_refs=["artifact:run99:output:r1"],
            view_of="artifact:run99:output:r1",
        )
        import hashlib
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.assertEqual(sv["summary_hash"]["algorithm"], "sha256")
        self.assertEqual(sv["summary_hash"]["value"], expected)

    def test_reject_empty_source_refs(self):
        with self.assertRaises(ForgeRefError):
            create_summary_view(
                summary_id="artifact:run99:summary:v1",
                text="Text.",
                source_refs=[],
                view_of="artifact:run99:output:r1",
            )

    def test_reject_empty_text(self):
        with self.assertRaises(ValueError):
            create_summary_view(
                summary_id="artifact:run99:summary:v1",
                text="",
                source_refs=["artifact:run99:output:r1"],
                view_of="artifact:run99:output:r1",
            )


class TestAbsenceRecordV1(unittest.TestCase):
    """Tool-generated absence records pass the v1 validator."""

    def test_absent_produces_v1_canonical_state(self):
        for state in AbsenceState:
            if state == AbsenceState.PRUNED:
                continue  # deprecated alias
            a = absent(state)
            self.assertIn(a["state"], V1_ABSENCE_STATES)

    def test_pruned_recoverable_is_canonical(self):
        a = absent(AbsenceState.PRUNED_RECOVERABLE, "compressed")
        self.assertEqual(a["state"], "pruned_recoverable")
        self.assertIn(a["state"], V1_ABSENCE_STATES)

    def test_pruned_alias_normalizes_with_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            a = absent(AbsenceState.PRUNED, "old-style")
            self.assertEqual(a["state"], "pruned_recoverable")
            self.assertTrue(any("deprecated" in str(w.message).lower() for w in caught))

    def test_legacy_absent_mode_is_ingress_only(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            legacy = absent(AbsenceState.NOT_GENERATED, mode="legacy")
            self.assertIn("absence_state", legacy)
            self.assertNotIn("state", legacy)
            self.assertTrue(any("legacy" in str(w.message).lower() for w in caught))

    def test_normalize_absence_state_maps_legacy(self):
        self.assertEqual(normalize_absence_state("pruned"), "pruned_recoverable")
        self.assertEqual(normalize_absence_state("not_generated"), "not_generated")

    def test_normalize_absence_state_rejects_unknown(self):
        with self.assertRaises(ValueError):
            normalize_absence_state("made_up_state")

    def test_v1_absence_tagged_field_passes(self):
        field_obj = {
            "field": "summary",
            "value": None,
            "state": "not_generated",
            "intentional_empty": True,
        }
        errors = validate_absence_field_v1(field_obj)
        self.assertEqual(errors, [], f"v1 validation errors: {errors}")

    def test_v1_absence_tagged_field_rejects_legacy_pruned(self):
        field_obj = {
            "field": "data",
            "value": None,
            "state": "pruned",  # not in v1 ABSENCE_STATES
        }
        errors = validate_absence_field_v1(field_obj)
        codes = {e["code"] for e in errors}
        self.assertIn("ABSENCE.MISSING_STATE_LABEL", codes)

    def test_validate_record_with_v1_states(self):
        record = {
            "output": None,
            "output_state": "pruned_recoverable",
            "summary": None,
            "summary_state": "not_invoked",
        }
        result = validate_record(record)
        self.assertEqual(result, record)

    def test_normalize_record_rewrites_legacy(self):
        record = {
            "data": None,
            "data_state": "pruned",
            "summary": None,
            "summary_state": "not_generated",
        }
        normalized = normalize_record(record)
        self.assertEqual(normalized["data_state"], "pruned_recoverable")
        self.assertEqual(normalized["summary_state"], "not_generated")

    def test_legacy_absent_object_ingress_normalizes_without_egress_leak(self):
        legacy_record = {
            "summary": {"value": None, "absence_state": "pruned"},
        }
        # Legacy ingress is tolerated.
        self.assertEqual(validate_record(legacy_record), legacy_record)

        # Internal normalization rewrites to canonical v1 state form.
        normalized = normalize_record(legacy_record)
        self.assertEqual(normalized["summary"]["state"], "pruned_recoverable")
        self.assertNotIn("absence_state", normalized["summary"])

        # Canonical egress helper does not emit legacy key.
        emitted = absent(AbsenceState.NOT_GENERATED)
        self.assertIn("state", emitted)
        self.assertNotIn("absence_state", emitted)

    def test_ambiguous_empty_still_rejected(self):
        for val in ["", {}, [], None]:
            with self.assertRaises(ForgeNullError, msg=f"Should reject {val!r}"):
                validate_record({"field": val})


class TestDictionaryLoadingNormalization(unittest.TestCase):
    """Protocol dict loads in both old and new formats, codes normalize."""

    def test_load_v1_container_format(self):
        codes = load_protocol_dict()
        self.assertIn("REVISION.REV_BLOCK_SCHEMA", codes)
        self.assertIn("STOP.STOP_TIMEOUT", codes)
        self.assertIn("SUMMARY.MISSING_SOURCE_REFS", codes)

    def test_all_entries_pass_v1_dict_validator(self):
        dict_path = Path(__file__).parent / "forge_protocol_dict.json"
        with open(dict_path) as f:
            doc = json.load(f)

        for entry in doc["entries"]:
            errors = validate_dict_entry_v1(entry)
            self.assertEqual(errors, [], f"Entry {entry['code']} failed: {errors}")

    def test_legacy_underscore_codes_accessible(self):
        codes = load_protocol_dict()
        # Legacy keys should also be registered
        self.assertIn("STOP_TIMEOUT", codes)
        self.assertIn("ERR_SCHEMA_FAIL", codes)
        # And should point to same entry as v1 key
        self.assertEqual(
            codes["STOP_TIMEOUT"]["meaning"],
            codes["STOP.STOP_TIMEOUT"]["meaning"],
        )

    def test_normalize_code_underscore_to_domain_dot(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.assertEqual(normalize_code("ABS_UNKNOWN"), "ABSENCE.ABS_UNKNOWN")
            self.assertEqual(normalize_code("STOP_TIMEOUT"), "STOP.STOP_TIMEOUT")
            self.assertEqual(normalize_code("ERR_SCHEMA_FAIL"), "ERROR.ERR_SCHEMA_FAIL")
            self.assertEqual(normalize_code("CRIT_SECURITY"), "CRITIQUE.CRIT_SECURITY")
            self.assertEqual(normalize_code("REV_BLOCK_SCHEMA"), "REVISION.REV_BLOCK_SCHEMA")

    def test_normalize_code_passthrough_domain_dot(self):
        self.assertEqual(normalize_code("REVISION.REV_BLOCK_SCHEMA"), "REVISION.REV_BLOCK_SCHEMA")

    def test_v1_container_shape(self):
        dict_path = Path(__file__).parent / "forge_protocol_dict.json"
        with open(dict_path) as f:
            doc = json.load(f)
        self.assertEqual(doc["proto"], "forge.internal.v1")
        self.assertEqual(doc["version"], "1.0.0")
        self.assertIsInstance(doc["entries"], list)
        self.assertGreater(len(doc["entries"]), 0)

    def test_no_duplicate_codes(self):
        dict_path = Path(__file__).parent / "forge_protocol_dict.json"
        with open(dict_path) as f:
            doc = json.load(f)
        codes = [e["code"] for e in doc["entries"]]
        self.assertEqual(len(codes), len(set(codes)), f"Duplicate codes: {[c for c in codes if codes.count(c) > 1]}")

    def test_deprecated_entries_have_replaced_by(self):
        dict_path = Path(__file__).parent / "forge_protocol_dict.json"
        with open(dict_path) as f:
            doc = json.load(f)
        for entry in doc["entries"]:
            if entry.get("lifecycle") == "deprecated":
                self.assertIn("replaced_by", entry, f"Deprecated {entry['code']} missing replaced_by")

    def test_load_old_flat_list_format(self):
        """Verify the loader handles a legacy flat-list dict file."""
        import tempfile
        legacy = [
            {
                "code": "ABS_UNKNOWN",
                "category": "absence_state",
                "meaning": "Unknown",
                "human_decode": "Unknown",
                "severity": "info",
                "allowed_contexts": ["field"],
                "version": "0.1.0"
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(legacy, f)
            tmp_path = f.name

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                codes = load_protocol_dict(tmp_path)
            # Legacy code normalized to domain-dot
            self.assertIn("ABSENCE.ABS_UNKNOWN", codes)
            # Original key also accessible
            self.assertIn("ABS_UNKNOWN", codes)
        finally:
            import os
            os.unlink(tmp_path)


class TestLegacyTelemetry(unittest.TestCase):
    """Compatibility-only legacy paths emit auditable telemetry signals."""

    def setUp(self):
        reset_legacy_usage_counts()

    def test_legacy_absent_mode_records_usage(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            absent(AbsenceState.NOT_GENERATED, mode="legacy")

        counts = get_legacy_usage_counts()
        self.assertGreaterEqual(counts.get("absent.mode_legacy", 0), 1)
        events = get_legacy_usage_events()
        self.assertTrue(any(e.get("surface") == "absent.mode_legacy" for e in events))
        event = next(e for e in events if e.get("surface") == "absent.mode_legacy")
        self.assertIn("location", event)
        self.assertIn("detail", event)

    def test_legacy_create_summary_records_usage(self):
        from forge_reversible_summary import create_summary

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            create_summary(
                "Legacy summary path.",
                ["artifact:run70:builder_output:r1"],
            )

        counts = get_legacy_usage_counts()
        self.assertGreaterEqual(counts.get("summary.create_summary", 0), 1)

    def test_legacy_create_stage_output_records_usage(self):
        from forge_stage_output import create_stage_output

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            create_stage_output(
                stage_id="artifact:run71:stage:builder:r1",
                seat="builder",
                output=None,
                output_state=AbsenceState.NOT_GENERATED,
            )

        counts = get_legacy_usage_counts()
        self.assertGreaterEqual(counts.get("stage.create_stage_output", 0), 1)

    def test_flat_list_dict_ingress_records_usage(self):
        import tempfile
        legacy = [
            {
                "code": "ABS_UNKNOWN",
                "category": "absence_state",
                "meaning": "Unknown",
                "human_decode": "Unknown",
                "severity": "info",
                "allowed_contexts": ["field"],
                "version": "0.1.0",
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(legacy, f)
            tmp_path = f.name

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                load_protocol_dict(tmp_path)
            counts = get_legacy_usage_counts()
            self.assertGreaterEqual(counts.get("dict.flat_list_ingress", 0), 1)
        finally:
            import os
            os.unlink(tmp_path)

    def test_underscore_code_ingress_records_usage(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            mapped = normalize_code("STOP_TIMEOUT")
        self.assertEqual(mapped, "STOP.STOP_TIMEOUT")
        counts = get_legacy_usage_counts()
        self.assertGreaterEqual(counts.get("code.underscore_ingress", 0), 1)


class TestUnresolvedRefBehavior(unittest.TestCase):
    """Unresolved references are handled explicitly, never silently."""

    def test_summary_view_with_unresolved_ref_in_index(self):
        sv = create_summary_view(
            summary_id="artifact:run99:summary:v1",
            text="Summary of missing artifact.",
            source_refs=["artifact:run99:output:r1"],
            view_of="artifact:run99:output:r1",
        )
        # Pass an index that does NOT contain the referenced artifacts.
        # The v1 validator should report unresolved refs.
        fake_index = {"artifact:other:thing:v1"}
        errors = validate_summary_view_v1(sv, artifact_index=fake_index)
        # Should have errors about unresolved refs
        codes = {e["code"] for e in errors}
        self.assertTrue(
            "REF.REF_UNRESOLVED" in codes or len(errors) > 0,
            f"Expected ref resolution errors, got: {errors}"
        )

    def test_summary_view_with_complete_index_passes(self):
        sv = create_summary_view(
            summary_id="artifact:run99:summary:v1",
            text="All refs present.",
            source_refs=["artifact:run99:output:r1"],
            view_of="artifact:run99:output:r1",
        )
        # Index contains all referenced artifacts plus the summary itself
        full_index = {
            "artifact:run99:summary:v1",
            "artifact:run99:output:r1",
        }
        errors = validate_summary_view_v1(sv, artifact_index=full_index)
        self.assertEqual(errors, [], f"Unexpected errors: {errors}")

    def test_reject_invalid_ref_format(self):
        with self.assertRaises(ForgeRefError):
            create_summary_view(
                summary_id="artifact:run99:summary:v1",
                text="Bad ref.",
                source_refs=["not-an-artifact-id"],
                view_of="artifact:run99:output:r1",
            )

    def test_reject_invalid_view_of(self):
        with self.assertRaises(ForgeRefError):
            create_summary_view(
                summary_id="artifact:run99:summary:v1",
                text="Bad view_of.",
                source_refs=["artifact:run99:output:r1"],
                view_of="not-valid",
            )


class TestBridgeValidator(unittest.TestCase):
    """Bridge validator is available and functional."""

    def test_validator_source_is_known(self):
        source = get_validator_source()
        self.assertIn(source, {"codex", "shim"})

    def test_validator_rejects_missing_summary_field(self):
        bad = {"type": "summary_view", "source_refs": [{"ref": "artifact:x:y:z", "state": "resolved"}]}
        errors = validate_summary_view_v1(bad)
        self.assertGreater(len(errors), 0)


class TestV1StageArtifactPath(unittest.TestCase):
    """End-to-end: v1 stage artifact + summary pass the canonical validator."""

    def setUp(self):
        from forge_stage_output import (
            ForgeProtocolError,
            create_v1_stage_artifact,
            create_v1_stage_summary,
            validate_v1_stage,
        )
        self.create_artifact = create_v1_stage_artifact
        self.create_summary = create_v1_stage_summary
        self.validate = validate_v1_stage
        self.ProtocolError = ForgeProtocolError

    def test_complete_stage_validates_cleanly(self):
        """Happy path: artifact + summary, zero v1 errors."""
        art = self.create_artifact(
            stage_id="artifact:run80:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="def main(): pass",
            source_refs=["artifact:run80:plan:r1"],
        )
        sv = self.create_summary(art, "Builder produced main function.")
        chamber = {"artifact:run80:plan:r1"}
        errors = self.validate(art, sv, known_artifact_ids=chamber)
        self.assertEqual(errors, [], f"v1 errors: {errors}")

    def test_complete_stage_has_v1_envelope_fields(self):
        art = self.create_artifact(
            stage_id="artifact:run81:stage:critic:r1",
            seat="critic",
            producer_name="critic-agent",
            producer_role="critic",
            output="LGTM, no issues found.",
            source_refs=["artifact:run81:builder:r1"],
        )
        for field in ["id", "type", "schema_version", "hash", "loc", "refs", "created_at", "producer"]:
            self.assertIn(field, art, f"Missing envelope field: {field}")
        self.assertEqual(art["type"], "stage_output")
        self.assertEqual(art["schema_version"], "forge.internal.v1")
        self.assertEqual(art["hash"]["algorithm"], "sha256")
        self.assertIsInstance(art["producer"], dict)
        self.assertEqual(art["producer"]["role"], "critic")

    def test_absent_output_validates_cleanly(self):
        """Typed absence path: no output, stop_reason, one finding."""
        art = self.create_artifact(
            stage_id="artifact:run82:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output=None,
            output_state=AbsenceState.NOT_GENERATED,
            stop_reason="STOP.STOP_TIMEOUT",
            findings=[
                {"code": "ERROR.ERR_TIMEOUT_SEAT", "detail": "Exceeded 30s"},
            ],
        )
        errors = self.validate(art)
        self.assertEqual(errors, [], f"v1 errors: {errors}")
        self.assertEqual(art["output_state"], "not_generated")
        self.assertEqual(art["stop_reason"], "STOP.STOP_TIMEOUT")
        self.assertEqual(art["findings"][0]["code"], "ERROR.ERR_TIMEOUT_SEAT")

    def test_absent_output_typed_absence_states_are_v1(self):
        art = self.create_artifact(
            stage_id="artifact:run83:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output=None,
            output_state=AbsenceState.WITHHELD,
        )
        self.assertIn(art["output_state"], V1_ABSENCE_STATES)
        self.assertEqual(art["stop_reason_state"], "not_invoked")
        self.assertIn(art["stop_reason_state"], V1_ABSENCE_STATES)

    def test_findings_use_domain_dot_codes(self):
        art = self.create_artifact(
            stage_id="artifact:run84:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output=None,
            output_state=AbsenceState.INVALID,
            findings=[
                {"code": "ERROR.ERR_SCHEMA_FAIL", "detail": "Output schema mismatch"},
                {"code": "CRITIQUE.CRIT_INVARIANT", "detail": "Null discipline violated"},
            ],
        )
        for f in art["findings"]:
            self.assertRegex(f["code"], r"^[A-Z]+\.[A-Z]")
            self.assertIn("severity", f)

    def test_legacy_underscore_codes_normalized(self):
        """Legacy codes like ERR_TIMEOUT_SEAT get normalized to domain-dot."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            art = self.create_artifact(
                stage_id="artifact:run85:stage:builder:r1",
                seat="builder",
                producer_name="builder-agent",
                producer_role="builder",
                output=None,
                output_state=AbsenceState.NOT_GENERATED,
                stop_reason="STOP_TIMEOUT",
                findings=[
                    {"code": "ERR_TIMEOUT_SEAT", "detail": "Legacy code test"},
                ],
            )
        self.assertEqual(art["stop_reason"], "STOP.STOP_TIMEOUT")
        self.assertEqual(art["findings"][0]["code"], "ERROR.ERR_TIMEOUT_SEAT")

    def test_reject_ambiguous_null_output(self):
        with self.assertRaises(ForgeNullError):
            self.create_artifact(
                stage_id="artifact:run86:stage:builder:r1",
                seat="builder",
                producer_name="builder-agent",
                producer_role="builder",
                output=None,
            )

    def test_reject_unknown_finding_code(self):
        with self.assertRaises(self.ProtocolError):
            self.create_artifact(
                stage_id="artifact:run87:stage:builder:r1",
                seat="builder",
                producer_name="builder-agent",
                producer_role="builder",
                output=None,
                output_state=AbsenceState.INVALID,
                findings=[{"code": "FAKE.FAKE_CODE", "detail": "nope"}],
            )

    def test_summary_is_v1_summary_view(self):
        art = self.create_artifact(
            stage_id="artifact:run88:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="result = 42",
            source_refs=["artifact:run88:plan:r1"],
        )
        sv = self.create_summary(art, "Builder computed result.")
        self.assertEqual(sv["type"], "summary_view")
        self.assertEqual(sv["schema_version"], "forge.internal.v1")
        self.assertEqual(sv["view_of"], art["id"])
        self.assertIn("summary_hash", sv)
        self.assertTrue(len(sv["source_refs"]) > 0)


class TestChamberV1(unittest.TestCase):
    """Chamber creation, registration, context views, queries, sealing, validation."""

    def setUp(self):
        from forge_chamber import (
            ForgeChamberError,
            create_chamber,
            get_artifact_by_id,
            get_context_view,
            get_stage_at_index,
            get_stages_by_seat,
            register_stage,
            seal_chamber,
            validate_chamber,
        )
        from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary

        self.create_chamber = create_chamber
        self.register_stage = register_stage
        self.get_context_view = get_context_view
        self.get_artifact_by_id = get_artifact_by_id
        self.get_stages_by_seat = get_stages_by_seat
        self.get_stage_at_index = get_stage_at_index
        self.seal_chamber = seal_chamber
        self.validate_chamber = validate_chamber
        self.ChamberError = ForgeChamberError
        self.create_artifact = create_v1_stage_artifact
        self.create_summary = create_v1_stage_summary

    def _make_artifact(self, run, seat, output="test output", source_refs=None):
        return self.create_artifact(
            stage_id=f"artifact:{run}:stage:{seat}:r1",
            seat=seat,
            producer_name=f"{seat}-agent",
            producer_role=seat,
            output=output,
            source_refs=source_refs,
        )

    def test_create_chamber(self):
        c = self.create_chamber("chamber:run200:v1")
        self.assertEqual(c["chamber_id"], "chamber:run200:v1")
        self.assertEqual(c["status"], "open")
        self.assertEqual(c["schema_version"], "forge.internal.v1")
        self.assertIn("chamber:run200:v1", c["artifact_index"])
        self.assertEqual(len(c["stages"]), 0)

    def test_create_chamber_with_metadata(self):
        c = self.create_chamber(
            "chamber:run201:v1",
            metadata={"run_type": "convergence_test", "version": "1.0"},
        )
        self.assertEqual(c["metadata"]["run_type"], "convergence_test")

    def test_reject_invalid_chamber_id(self):
        with self.assertRaises(self.ChamberError):
            self.create_chamber("bad-id")
        with self.assertRaises(self.ChamberError):
            self.create_chamber("")

    def test_register_stage_with_summary(self):
        c = self.create_chamber("chamber:run202:v1")
        art = self._make_artifact("run202", "builder")
        sv = self.create_summary(art, "Builder produced output.")
        entry = self.register_stage(c, art, sv)
        self.assertEqual(entry["stage_index"], 0)
        self.assertEqual(entry["seat"], "builder")
        self.assertIsNotNone(entry["summary"])
        self.assertIsNone(entry["summary_state"])

    def test_register_stage_without_summary(self):
        c = self.create_chamber("chamber:run203:v1")
        art = self._make_artifact("run203", "builder")
        entry = self.register_stage(c, art, summary_state="not_generated")
        self.assertIsNone(entry["summary"])
        self.assertEqual(entry["summary_state"], "not_generated")

    def test_reject_sealed_registration(self):
        c = self.create_chamber("chamber:run204:v1")
        self.seal_chamber(c)
        art = self._make_artifact("run204", "builder")
        with self.assertRaises(self.ChamberError):
            self.register_stage(c, art, summary_state="not_generated")

    def test_reject_duplicate_artifact_id(self):
        c = self.create_chamber("chamber:run205:v1")
        art = self._make_artifact("run205", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        with self.assertRaises(self.ChamberError):
            self.register_stage(c, art, summary_state="not_generated")

    def test_reject_missing_summary_state(self):
        c = self.create_chamber("chamber:run206:v1")
        art = self._make_artifact("run206", "builder")
        with self.assertRaises(self.ChamberError):
            self.register_stage(c, art)

    def test_reject_dangling_ref(self):
        c = self.create_chamber("chamber:run207:v1")
        art = self._make_artifact(
            "run207", "builder",
            source_refs=["artifact:run207:stage:architect:r1"],
        )
        with self.assertRaises(self.ChamberError):
            self.register_stage(c, art, summary_state="not_generated")

    def test_context_view_all_stages(self):
        c = self.create_chamber("chamber:run208:v1")
        art1 = self._make_artifact("run208", "architect")
        self.register_stage(c, art1, summary_state="not_generated")
        art2 = self._make_artifact(
            "run208", "builder",
            source_refs=["artifact:run208:stage:architect:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")

        ctx = self.get_context_view(c, for_seat="critic")
        self.assertEqual(ctx["stage_count"], 2)
        self.assertEqual(ctx["for_seat"], "critic")
        self.assertIn("artifact:run208:stage:architect:r1", ctx["available_artifact_ids"])
        self.assertIn("artifact:run208:stage:builder:r1", ctx["available_artifact_ids"])

    def test_context_view_up_to_index(self):
        c = self.create_chamber("chamber:run209:v1")
        art1 = self._make_artifact("run209", "architect")
        self.register_stage(c, art1, summary_state="not_generated")
        art2 = self._make_artifact(
            "run209", "builder",
            source_refs=["artifact:run209:stage:architect:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")

        ctx = self.get_context_view(c, up_to_index=1)
        self.assertEqual(ctx["stage_count"], 1)
        self.assertIn("artifact:run209:stage:architect:r1", ctx["available_artifact_ids"])
        self.assertNotIn("artifact:run209:stage:builder:r1", ctx["available_artifact_ids"])

    def test_context_view_upstream_by_seat(self):
        c = self.create_chamber("chamber:run210:v1")
        art1 = self._make_artifact("run210", "architect")
        self.register_stage(c, art1, summary_state="not_generated")
        art2 = self._make_artifact(
            "run210", "builder",
            source_refs=["artifact:run210:stage:architect:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")

        ctx = self.get_context_view(c)
        self.assertIn("architect", ctx["upstream_by_seat"])
        self.assertIn("builder", ctx["upstream_by_seat"])
        self.assertEqual(len(ctx["upstream_by_seat"]["architect"]), 1)

    def test_query_get_artifact_by_id(self):
        c = self.create_chamber("chamber:run211:v1")
        art = self._make_artifact("run211", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        found = self.get_artifact_by_id(c, "artifact:run211:stage:builder:r1")
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], "artifact:run211:stage:builder:r1")
        self.assertIsNone(self.get_artifact_by_id(c, "artifact:nonexistent:v1"))

    def test_query_get_stages_by_seat(self):
        c = self.create_chamber("chamber:run212:v1")
        art = self._make_artifact("run212", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        stages = self.get_stages_by_seat(c, "builder")
        self.assertEqual(len(stages), 1)
        self.assertEqual(self.get_stages_by_seat(c, "critic"), [])

    def test_query_get_stage_at_index(self):
        c = self.create_chamber("chamber:run213:v1")
        art = self._make_artifact("run213", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        stage = self.get_stage_at_index(c, 0)
        self.assertIsNotNone(stage)
        self.assertEqual(stage["stage_index"], 0)
        self.assertIsNone(self.get_stage_at_index(c, 99))

    def test_seal_chamber(self):
        c = self.create_chamber("chamber:run214:v1")
        self.seal_chamber(c)
        self.assertEqual(c["status"], "sealed")

    def test_reject_double_seal(self):
        c = self.create_chamber("chamber:run215:v1")
        self.seal_chamber(c)
        with self.assertRaises(self.ChamberError):
            self.seal_chamber(c)

    def test_validate_empty_chamber(self):
        c = self.create_chamber("chamber:run216:v1")
        errors = self.validate_chamber(c)
        self.assertEqual(errors, [])

    def test_validate_multi_stage_chamber(self):
        c = self.create_chamber("chamber:run217:v1")
        art1 = self._make_artifact("run217", "architect")
        sv1 = self.create_summary(art1, "Architect plan.")
        self.register_stage(c, art1, sv1)

        art2 = self._make_artifact(
            "run217", "builder",
            source_refs=["artifact:run217:stage:architect:r1"],
        )
        sv2 = self.create_summary(
            art2, "Builder output.",
            extra_source_refs=["artifact:run217:stage:architect:r1"],
        )
        self.register_stage(c, art2, sv2)

        art3 = self._make_artifact(
            "run217", "critic",
            source_refs=[
                "artifact:run217:stage:architect:r1",
                "artifact:run217:stage:builder:r1",
            ],
        )
        sv3 = self.create_summary(
            art3, "Critic review.",
            extra_source_refs=[
                "artifact:run217:stage:architect:r1",
                "artifact:run217:stage:builder:r1",
            ],
        )
        self.register_stage(c, art3, sv3)
        self.seal_chamber(c)

        errors = self.validate_chamber(c)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    def test_artifact_index_grows_monotonically(self):
        c = self.create_chamber("chamber:run218:v1")
        self.assertEqual(len(c["artifact_index"]), 1)

        art1 = self._make_artifact("run218", "architect")
        sv1 = self.create_summary(art1, "Plan.")
        self.register_stage(c, art1, sv1)
        self.assertGreater(len(c["artifact_index"]), 1)
        size_after_1 = len(c["artifact_index"])

        art2 = self._make_artifact(
            "run218", "builder",
            source_refs=["artifact:run218:stage:architect:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")
        self.assertGreater(len(c["artifact_index"]), size_after_1)


class TestChamberPersistence(unittest.TestCase):
    """Save/load round-trip, artifact_index set/list fidelity, SQLite index."""

    def setUp(self):
        import tempfile
        from forge_chamber import (
            ForgeChamberError,
            create_chamber,
            get_chamber_summary,
            list_chambers,
            load_chamber,
            register_stage,
            save_chamber,
            seal_chamber,
            validate_chamber,
        )
        from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary

        self.tmp_dir = Path(tempfile.mkdtemp(prefix="forge_test_chamber_"))
        self.create_chamber = create_chamber
        self.register_stage = register_stage
        self.seal_chamber = seal_chamber
        self.validate_chamber = validate_chamber
        self.save_chamber = save_chamber
        self.load_chamber = load_chamber
        self.list_chambers = list_chambers
        self.get_chamber_summary = get_chamber_summary
        self.ChamberError = ForgeChamberError
        self.create_artifact = create_v1_stage_artifact
        self.create_summary = create_v1_stage_summary

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_artifact(self, run, seat, output="test output", source_refs=None):
        return self.create_artifact(
            stage_id=f"artifact:{run}:stage:{seat}:r1",
            seat=seat,
            producer_name=f"{seat}-agent",
            producer_role=seat,
            output=output,
            source_refs=source_refs,
        )

    def test_save_load_round_trip(self):
        c = self.create_chamber("chamber:run300:v1")
        art = self._make_artifact("run300", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        self.seal_chamber(c)

        path = self.save_chamber(c, base_dir=self.tmp_dir)
        self.assertTrue(path.exists())

        loaded = self.load_chamber("chamber:run300:v1", base_dir=self.tmp_dir)
        self.assertEqual(loaded["chamber_id"], "chamber:run300:v1")
        self.assertEqual(loaded["status"], "sealed")
        self.assertEqual(len(loaded["stages"]), 1)

    def test_artifact_index_set_list_fidelity(self):
        c = self.create_chamber("chamber:run301:v1")
        art = self._make_artifact("run301", "builder")
        self.register_stage(c, art, summary_state="not_generated")

        self.assertIsInstance(c["artifact_index"], set)

        self.save_chamber(c, base_dir=self.tmp_dir)

        # Verify JSON has sorted list
        import json
        json_path = self.tmp_dir / "chambers" / "chamber_run301_v1.json"
        with open(json_path) as f:
            raw = json.load(f)
        self.assertIsInstance(raw["artifact_index"], list)
        self.assertEqual(raw["artifact_index"], sorted(raw["artifact_index"]))

        # Verify load converts back to set
        loaded = self.load_chamber("chamber:run301:v1", base_dir=self.tmp_dir)
        self.assertIsInstance(loaded["artifact_index"], set)
        self.assertEqual(loaded["artifact_index"], c["artifact_index"])

    def test_load_nonexistent_raises(self):
        with self.assertRaises(self.ChamberError):
            self.load_chamber("chamber:nonexistent:v1", base_dir=self.tmp_dir)

    def test_post_load_validation_passes(self):
        c = self.create_chamber("chamber:run302:v1")
        art1 = self._make_artifact("run302", "architect")
        sv1 = self.create_summary(art1, "Plan.")
        self.register_stage(c, art1, sv1)

        art2 = self._make_artifact(
            "run302", "builder",
            source_refs=["artifact:run302:stage:architect:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")
        self.seal_chamber(c)

        self.save_chamber(c, base_dir=self.tmp_dir)
        loaded = self.load_chamber("chamber:run302:v1", base_dir=self.tmp_dir)
        errors = self.validate_chamber(loaded)
        self.assertEqual(errors, [], f"Post-load errors: {errors}")

    def test_sqlite_list_chambers(self):
        c1 = self.create_chamber("chamber:run303:v1")
        self.save_chamber(c1, base_dir=self.tmp_dir)

        c2 = self.create_chamber("chamber:run304:v1")
        self.seal_chamber(c2)
        self.save_chamber(c2, base_dir=self.tmp_dir)

        all_chambers = self.list_chambers(base_dir=self.tmp_dir)
        self.assertEqual(len(all_chambers), 2)

    def test_sqlite_status_filter(self):
        c1 = self.create_chamber("chamber:run305:v1")
        self.save_chamber(c1, base_dir=self.tmp_dir)

        c2 = self.create_chamber("chamber:run306:v1")
        self.seal_chamber(c2)
        self.save_chamber(c2, base_dir=self.tmp_dir)

        open_chambers = self.list_chambers(base_dir=self.tmp_dir, status="open")
        sealed_chambers = self.list_chambers(base_dir=self.tmp_dir, status="sealed")
        self.assertEqual(len(open_chambers), 1)
        self.assertEqual(open_chambers[0]["chamber_id"], "chamber:run305:v1")
        self.assertEqual(len(sealed_chambers), 1)
        self.assertEqual(sealed_chambers[0]["chamber_id"], "chamber:run306:v1")

    def test_get_chamber_summary(self):
        c = self.create_chamber("chamber:run307:v1")
        art = self._make_artifact("run307", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        self.save_chamber(c, base_dir=self.tmp_dir)

        summary = self.get_chamber_summary("chamber:run307:v1", base_dir=self.tmp_dir)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["chamber_id"], "chamber:run307:v1")
        self.assertEqual(summary["stage_count"], 1)
        self.assertIn("builder", summary["seats"])

    def test_get_chamber_summary_not_found(self):
        result = self.get_chamber_summary("chamber:nonexistent:v1", base_dir=self.tmp_dir)
        self.assertIsNone(result)

    def test_sqlite_index_updates_on_resave(self):
        c = self.create_chamber("chamber:run308:v1")
        self.save_chamber(c, base_dir=self.tmp_dir)

        summary1 = self.get_chamber_summary("chamber:run308:v1", base_dir=self.tmp_dir)
        self.assertEqual(summary1["stage_count"], 0)
        self.assertEqual(summary1["status"], "open")

        art = self._make_artifact("run308", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        self.seal_chamber(c)
        self.save_chamber(c, base_dir=self.tmp_dir)

        summary2 = self.get_chamber_summary("chamber:run308:v1", base_dir=self.tmp_dir)
        self.assertEqual(summary2["stage_count"], 1)
        self.assertEqual(summary2["status"], "sealed")


class TestTraceCodec(unittest.TestCase):
    """Trace codec: encode/decode round-trip, verification, stats."""

    def setUp(self):
        from forge_chamber import (
            create_chamber,
            register_stage,
            seal_chamber,
        )
        from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary
        from forge_trace_codec import (
            ForgeTraceError,
            decode_trace,
            encode_trace,
            trace_stats,
            verify_trace,
        )

        self.create_chamber = create_chamber
        self.register_stage = register_stage
        self.seal_chamber = seal_chamber
        self.create_artifact = create_v1_stage_artifact
        self.create_summary = create_v1_stage_summary
        self.encode_trace = encode_trace
        self.decode_trace = decode_trace
        self.verify_trace = verify_trace
        self.trace_stats = trace_stats
        self.TraceError = ForgeTraceError

    def _make_artifact(self, run, seat, output="test output", source_refs=None):
        return self.create_artifact(
            stage_id=f"artifact:{run}:stage:{seat}:r1",
            seat=seat,
            producer_name=f"{seat}-agent",
            producer_role=seat,
            output=output,
            source_refs=source_refs,
        )

    def _build_3_stage_chamber(self, run="run400"):
        c = self.create_chamber(f"chamber:{run}:v1")
        art1 = self._make_artifact(run, "architect")
        sv1 = self.create_summary(art1, "Plan.")
        self.register_stage(c, art1, sv1)

        art2 = self._make_artifact(
            run, "builder",
            source_refs=[f"artifact:{run}:stage:architect:r1"],
        )
        sv2 = self.create_summary(
            art2, "Built.",
            extra_source_refs=[f"artifact:{run}:stage:architect:r1"],
        )
        self.register_stage(c, art2, sv2)

        art3 = self._make_artifact(
            run, "critic",
            source_refs=[
                f"artifact:{run}:stage:architect:r1",
                f"artifact:{run}:stage:builder:r1",
            ],
        )
        sv3 = self.create_summary(
            art3, "Reviewed.",
            extra_source_refs=[
                f"artifact:{run}:stage:architect:r1",
                f"artifact:{run}:stage:builder:r1",
            ],
        )
        self.register_stage(c, art3, sv3)
        self.seal_chamber(c)
        return c

    def test_encode_decode_round_trip(self):
        c = self._build_3_stage_chamber("run400")
        trace = self.encode_trace(c)
        decoded = self.decode_trace(trace)
        self.assertEqual(len(decoded), 3)
        # Compare each stage's artifact ID
        for i, stage in enumerate(decoded):
            self.assertEqual(stage["stage_index"], i)
            self.assertIsInstance(stage["artifact"], dict)
            self.assertIn("id", stage["artifact"])

    def test_verify_valid_trace(self):
        c = self._build_3_stage_chamber("run401")
        trace = self.encode_trace(c)
        result = self.verify_trace(trace, c)
        self.assertTrue(result["valid"])
        self.assertTrue(result["hash_match"])
        self.assertTrue(result["content_match"])

    def test_verify_tampered_trace(self):
        import copy
        c = self._build_3_stage_chamber("run402")
        trace = self.encode_trace(c)
        tampered = copy.deepcopy(trace)
        tampered["stages"][0]["seat"] = "TAMPERED"
        result = self.verify_trace(tampered, c)
        self.assertFalse(result["valid"])
        self.assertFalse(result["hash_match"])

    def test_verify_without_chamber(self):
        c = self._build_3_stage_chamber("run403")
        trace = self.encode_trace(c)
        result = self.verify_trace(trace)
        self.assertTrue(result["valid"])
        self.assertTrue(result["hash_match"])
        self.assertIsNone(result["content_match"])

    def test_empty_chamber(self):
        c = self.create_chamber("chamber:run404:v1")
        trace = self.encode_trace(c)
        self.assertEqual(len(trace["stages"]), 0)
        self.assertEqual(trace["shared"], {})
        decoded = self.decode_trace(trace)
        self.assertEqual(decoded, [])
        result = self.verify_trace(trace, c)
        self.assertTrue(result["valid"])

    def test_single_stage(self):
        c = self.create_chamber("chamber:run405:v1")
        art = self._make_artifact("run405", "builder")
        self.register_stage(c, art, summary_state="not_generated")
        trace = self.encode_trace(c)
        decoded = self.decode_trace(trace)
        self.assertEqual(len(decoded), 1)
        result = self.verify_trace(trace, c)
        self.assertTrue(result["valid"])

    def test_shared_ref_entries_detected(self):
        c = self._build_3_stage_chamber("run406")
        trace = self.encode_trace(c)
        # Architect ref entry should appear in builder and critic stages
        self.assertGreater(len(trace["shared"]), 0)
        stats = self.trace_stats(trace)
        self.assertGreater(stats["ref_replacements"], 0)

    def test_shared_producers_detected(self):
        """Same seat producing 2 stages → producer dedup."""
        c = self.create_chamber("chamber:run407:v1")
        art1 = self.create_artifact(
            stage_id="artifact:run407:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="First attempt",
        )
        self.register_stage(c, art1, summary_state="not_generated")

        art2 = self.create_artifact(
            stage_id="artifact:run407:stage:builder:r2",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="Second attempt",
            source_refs=["artifact:run407:stage:builder:r1"],
        )
        self.register_stage(c, art2, summary_state="not_generated")

        trace = self.encode_trace(c)
        # Producer dict should be shared (appears in both stages)
        shared_values = list(trace["shared"].values())
        producer_shared = [
            v for v in shared_values
            if isinstance(v, dict) and "name" in v and v.get("name") == "builder-agent"
        ]
        self.assertEqual(len(producer_shared), 1)

    def test_stats_accuracy(self):
        c = self._build_3_stage_chamber("run408")
        trace = self.encode_trace(c)
        stats = self.trace_stats(trace)
        self.assertEqual(stats["stage_count"], 3)
        self.assertEqual(stats["shared_structures"], len(trace["shared"]))
        self.assertEqual(stats["encoding"], "forge.trace.v1")
        self.assertGreater(stats["original_size"], 0)
        self.assertGreater(stats["encoded_size"], 0)

    def test_unknown_encoding_rejected(self):
        bad_trace = {"encoding": "unknown.v99", "shared": {}, "stages": []}
        with self.assertRaises(self.TraceError):
            self.decode_trace(bad_trace)

    def test_decoded_artifacts_are_independent_copies(self):
        """Decoded stages from same shared ref should be independent objects."""
        c = self._build_3_stage_chamber("run409")
        trace = self.encode_trace(c)
        decoded = self.decode_trace(trace)
        # Mutating a ref in stage 1 should not affect stage 2
        if len(decoded[1]["artifact"].get("refs", [])) > 0:
            decoded[1]["artifact"]["refs"][0]["state"] = "MUTATED"
            if len(decoded[2]["artifact"].get("refs", [])) > 0:
                self.assertNotEqual(
                    decoded[2]["artifact"]["refs"][0].get("state"),
                    "MUTATED",
                )


class TestOrchestrator(unittest.TestCase):
    """Phase 5 — orchestrator drives multi-seat runs via grammar API."""

    def setUp(self):
        # Reset run counter for deterministic IDs
        import forge_orchestrator
        forge_orchestrator._run_counter = 599  # first call -> run600

    # --- Mock agent fns ---

    @staticmethod
    def _agent_architect(ctx):
        return {
            "output": "Plan: build a schema validator.",
            "summary_text": "Architect proposes schema validator.",
            "findings": None,
            "stop_reason": None,
        }

    @staticmethod
    def _agent_builder(ctx):
        rev = ctx.get("revision", 1)
        if rev == 1:
            return {"output": "def validate(s): return check(s)", "findings": None, "stop_reason": None}
        return {"output": "def validate(s, max_size=1024): return check(s, max_size=max_size)",
                "findings": None, "stop_reason": None}

    @staticmethod
    def _agent_critic_approve(ctx):
        return {"output": "Approved.", "findings": None, "stop_reason": None}

    @staticmethod
    def _agent_critic_block_then_approve(ctx):
        rev = ctx.get("revision", 1)
        if rev == 1:
            return {
                "output": "Security concern.",
                "findings": [{"code": "CRITIQUE.CRIT_SECURITY", "detail": "No size limit"}],
                "stop_reason": None,
            }
        return {"output": "Fixed. Approved.", "findings": None, "stop_reason": None}

    @staticmethod
    def _agent_crash(ctx):
        raise RuntimeError("API connection failed")

    @staticmethod
    def _agent_stop(ctx):
        return {"output": "Done.", "findings": None, "stop_reason": "STOP.STOP_CONSENSUS"}

    @staticmethod
    def _agent_critic_med(ctx):
        """Returns med-severity critique."""
        return {
            "output": "Schema concern.",
            "findings": [{"code": "CRITIQUE.CRIT_SCHEMA", "detail": "Schema needs work"}],
            "stop_reason": None,
        }

    @staticmethod
    def _agent_critic_always_block(ctx):
        """Always returns blocking critique."""
        return {
            "output": "Security issue.",
            "findings": [{"code": "CRITIQUE.CRIT_SECURITY", "detail": "Still broken"}],
            "stop_reason": None,
        }

    def _specs_3_seat(self, critic_fn=None):
        if critic_fn is None:
            critic_fn = self._agent_critic_approve
        return [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_architect,
             "producer_name": "architect-agent", "is_critic": False},
            {"name": "builder", "role": "builder", "agent_fn": self._agent_builder,
             "producer_name": "builder-agent", "is_critic": False},
            {"name": "critic", "role": "critic", "agent_fn": critic_fn,
             "producer_name": "critic-agent", "is_critic": True},
        ]

    # --- Tests ---

    def test_happy_path_3_seats(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(self._specs_3_seat(), run_id="run600")
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 3)
        self.assertEqual(rr["revision_cycles"], 0)
        self.assertEqual(rr["chamber_validation"], [])

    def test_happy_path_trace_verifies(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(self._specs_3_seat(), run_id="run601")
        self.assertTrue(result["run_report"]["trace_verification"]["valid"])
        self.assertTrue(result["run_report"]["trace_verification"]["hash_match"])
        self.assertTrue(result["run_report"]["trace_verification"]["content_match"])

    def test_revision_cycle_block_critique(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_block_then_approve),
            run_id="run602",
        )
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 5)
        self.assertEqual(rr["revision_cycles"], 1)
        self.assertEqual(rr["chamber_validation"], [])

    def test_revision_actual_sequence(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_block_then_approve),
            run_id="run603",
        )
        self.assertEqual(
            result["run_report"]["actual_seat_sequence"],
            ["architect", "builder", "critic", "builder", "critic"],
        )

    def test_revision_feedback_passed(self):
        """Revision target receives critic findings in its input."""
        received_feedback = []

        def builder_capture(ctx):
            received_feedback.append(ctx.get("revision_feedback"))
            rev = ctx.get("revision", 1)
            if rev == 1:
                return {"output": "first attempt", "findings": None, "stop_reason": None}
            return {"output": "revised", "findings": None, "stop_reason": None}

        specs = [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_architect,
             "producer_name": "architect-agent", "is_critic": False},
            {"name": "builder", "role": "builder", "agent_fn": builder_capture,
             "producer_name": "builder-agent", "is_critic": False},
            {"name": "critic", "role": "critic", "agent_fn": self._agent_critic_block_then_approve,
             "producer_name": "critic-agent", "is_critic": True},
        ]
        from forge_orchestrator import run_chamber
        run_chamber(specs, run_id="run604")

        # First call: no feedback; second call: has findings
        self.assertIsNone(received_feedback[0])
        self.assertIsNotNone(received_feedback[1])
        self.assertEqual(received_feedback[1][0]["code"], "CRITIQUE.CRIT_SECURITY")

    def test_max_revisions_stops_run(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_always_block),
            run_id="run605",
            policy={"max_revisions": 1},
        )
        rr = result["run_report"]
        self.assertEqual(rr["status"], "stopped")
        self.assertEqual(rr["stop_reason"], "STOP.STOP_FORCED")
        self.assertEqual(rr["chamber_validation"], [])

    def test_med_critique_continue_default(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_med),
            run_id="run606",
        )
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 3)
        self.assertEqual(rr["revision_cycles"], 0)

    def test_med_critique_revise_policy(self):
        from forge_orchestrator import run_chamber

        call_count = [0]

        def critic_med_then_approve(ctx):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "output": "Schema concern.",
                    "findings": [{"code": "CRITIQUE.CRIT_SCHEMA", "detail": "Schema needs work"}],
                    "stop_reason": None,
                }
            return {"output": "Fixed.", "findings": None, "stop_reason": None}

        specs = self._specs_3_seat(critic_fn=critic_med_then_approve)
        result = run_chamber(specs, run_id="run607", policy={"on_med_critique": "revise"})
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 5)
        self.assertEqual(rr["revision_cycles"], 1)

    def test_agent_exception_halt(self):
        from forge_orchestrator import run_chamber
        specs = [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_architect,
             "producer_name": "architect-agent", "is_critic": False},
            {"name": "builder", "role": "builder", "agent_fn": self._agent_crash,
             "producer_name": "builder-agent", "is_critic": False},
            {"name": "critic", "role": "critic", "agent_fn": self._agent_critic_approve,
             "producer_name": "critic-agent", "is_critic": True},
        ]
        result = run_chamber(specs, run_id="run608")
        rr = result["run_report"]
        self.assertEqual(rr["status"], "error")
        self.assertEqual(rr["total_stages"], 2)
        self.assertEqual(len(rr["errors"]), 1)
        self.assertIn("RuntimeError", rr["errors"][0]["error"])
        self.assertEqual(rr["stop_reason"], "STOP.STOP_ERROR")

    def test_agent_exception_record(self):
        from forge_orchestrator import run_chamber
        specs = [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_architect,
             "producer_name": "architect-agent", "is_critic": False},
            {"name": "builder", "role": "builder", "agent_fn": self._agent_crash,
             "producer_name": "builder-agent", "is_critic": False},
            {"name": "critic", "role": "critic", "agent_fn": self._agent_critic_approve,
             "producer_name": "critic-agent", "is_critic": True},
        ]
        result = run_chamber(specs, run_id="run609", policy={"on_agent_error": "record"})
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 3)
        self.assertEqual(len(rr["errors"]), 1)

    def test_agent_stop_reason(self):
        from forge_orchestrator import run_chamber
        specs = [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_stop,
             "producer_name": "architect-agent", "is_critic": False},
            {"name": "builder", "role": "builder", "agent_fn": self._agent_builder,
             "producer_name": "builder-agent", "is_critic": False},
        ]
        result = run_chamber(specs, run_id="run610")
        rr = result["run_report"]
        self.assertEqual(rr["status"], "stopped")
        self.assertEqual(rr["total_stages"], 1)
        self.assertEqual(rr["stop_reason"], "STOP.STOP_CONSENSUS")

    def test_error_stage_typed_absence(self):
        """Failed stage has output=None with proper typed absence."""
        from forge_orchestrator import run_chamber
        specs = [
            {"name": "builder", "role": "builder", "agent_fn": self._agent_crash,
             "producer_name": "builder-agent", "is_critic": False},
        ]
        result = run_chamber(specs, run_id="run611")
        chamber = result["chamber"]
        # Find the error stage
        error_stage = chamber["stages"][-1]
        art = error_stage["artifact"]
        self.assertIsNone(art["output"])
        self.assertEqual(art["output_state"], "not_generated")

    def test_single_seat_run(self):
        from forge_orchestrator import run_chamber
        specs = [
            {"name": "architect", "role": "architect", "agent_fn": self._agent_architect,
             "producer_name": "architect-agent", "is_critic": False},
        ]
        result = run_chamber(specs, run_id="run612")
        rr = result["run_report"]
        self.assertEqual(rr["status"], "complete")
        self.assertEqual(rr["total_stages"], 1)
        self.assertEqual(rr["chamber_validation"], [])

    def test_revision_ids_increment(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_block_then_approve),
            run_id="run613",
        )
        chamber = result["chamber"]
        stage_ids = [s["stage_id"] for s in chamber["stages"]]
        self.assertIn("artifact:run613:stage:architect:r1", stage_ids)
        self.assertIn("artifact:run613:stage:builder:r1", stage_ids)
        self.assertIn("artifact:run613:stage:critic:r1", stage_ids)
        self.assertIn("artifact:run613:stage:builder:r2", stage_ids)
        self.assertIn("artifact:run613:stage:critic:r2", stage_ids)

    def test_chamber_clean_after_revision(self):
        from forge_orchestrator import run_chamber
        result = run_chamber(
            self._specs_3_seat(critic_fn=self._agent_critic_block_then_approve),
            run_id="run614",
        )
        self.assertEqual(result["run_report"]["chamber_validation"], [])


if __name__ == "__main__":
    print(f"Validator backend: {get_validator_source()}\n")
    unittest.main(verbosity=2)
