"""
forge_chamber.py — Chamber/Context system for multi-stage Forge runs.

Tracks all artifacts produced during a run, resolves cross-stage refs,
and provides upstream context to each seat. Composes with all existing
Phase 1/2 tools.

A chamber is an in-memory container with append-only stage registration.
The artifact_index grows monotonically — each new stage's refs validate
against all previously registered artifacts.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge_nulls import (
    ForgeNullError,
    normalize_absence_state,
    validate_record,
)
from forge_stage_output import validate_v1_stage
from forge_v1_bridge import (
    validate_artifact_envelope_v1,
    validate_summary_view_v1,
)

PROTOCOL_ID = "forge.internal.v1"

# Chamber IDs: "chamber:<seg1>:<seg2>[:<segN>]"
# Same colon-separated pattern as artifact IDs but with chamber: prefix.
_CHAMBER_ID_RE = re.compile(r"^chamber:[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)+$")

_DEFAULT_BASE_DIR = Path(__file__).parent / "data"


class ForgeChamberError(Exception):
    """Chamber-level invariant violation."""


def _validate_chamber_id(chamber_id: str) -> str:
    """Validate a chamber ID matches the expected format."""
    if not isinstance(chamber_id, str) or not chamber_id.strip():
        raise ForgeChamberError("chamber_id must be a non-empty string")
    if not _CHAMBER_ID_RE.match(chamber_id):
        raise ForgeChamberError(
            f"chamber_id does not match pattern "
            f"'chamber:<seg1>:<seg2>[:<segN>]': {chamber_id!r}"
        )
    return chamber_id


# --- Creation ---

def create_chamber(chamber_id: str, *, metadata: dict | None = None) -> dict:
    """Create a new chamber container.

    Args:
        chamber_id: ID in format "chamber:<seg1>:<seg2>[:<segN>]"
        metadata: Optional freeform metadata, null-disciplined if provided

    Returns:
        Chamber dict with empty stages and open status.
    """
    _validate_chamber_id(chamber_id)

    if metadata is not None:
        validate_record(metadata)

    now = datetime.now(timezone.utc).isoformat()

    chamber: dict[str, Any] = {
        "chamber_id": chamber_id,
        "schema_version": PROTOCOL_ID,
        "created_at": now,
        "status": "open",
        "stages": [],
        "artifact_index": {chamber_id},
    }

    if metadata is not None:
        chamber["metadata"] = metadata

    return chamber


# --- Registration ---

def register_stage(
    chamber: dict,
    artifact: dict,
    summary: dict | None = None,
    summary_state: str | None = None,
) -> dict:
    """Register a stage artifact (and optional summary) in the chamber.

    Validates the artifact against the chamber's artifact_index, catching
    dangling cross-stage refs at registration time.

    Args:
        chamber: The chamber dict (mutated in place)
        artifact: Full v1 ArtifactEnvelope dict
        summary: Optional v1 SummaryView dict
        summary_state: Required when summary is None (null discipline)

    Returns:
        The appended stage entry dict.

    Raises:
        ForgeChamberError: On sealed chamber, duplicate ID, or null discipline violation
    """
    if chamber["status"] == "sealed":
        raise ForgeChamberError("Cannot register stage in sealed chamber")

    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str):
        raise ForgeChamberError("Artifact missing 'id' field")

    if artifact_id in chamber["artifact_index"]:
        raise ForgeChamberError(f"Duplicate artifact ID: {artifact_id!r}")

    if summary is None and summary_state is None:
        raise ForgeChamberError(
            "summary is None but no summary_state provided. "
            "Null discipline requires typed absence."
        )

    if summary_state is not None:
        summary_state = normalize_absence_state(summary_state)

    errors = validate_v1_stage(
        artifact, summary, known_artifact_ids=chamber["artifact_index"]
    )
    if errors:
        formatted = "; ".join(
            f"{e.get('code')}:{e.get('path')}:{e.get('message')}" for e in errors
        )
        raise ForgeChamberError(f"Stage validation failed: {formatted}")

    stage_index = len(chamber["stages"])
    seat = artifact.get("seat", artifact.get("producer", {}).get("role", "unknown"))
    now = datetime.now(timezone.utc).isoformat()

    stage_entry = {
        "stage_index": stage_index,
        "stage_id": artifact_id,
        "seat": seat,
        "artifact": artifact,
        "summary": summary,
        "summary_state": summary_state if summary is None else None,
        "registered_at": now,
    }

    chamber["stages"].append(stage_entry)
    chamber["artifact_index"].add(artifact_id)

    if summary is not None:
        summary_id = summary.get("id")
        if isinstance(summary_id, str):
            chamber["artifact_index"].add(summary_id)

    return stage_entry


# --- Context View ---

def get_context_view(
    chamber: dict,
    *,
    for_seat: str | None = None,
    up_to_index: int | None = None,
) -> dict:
    """Get a snapshot of upstream context for a seat.

    Args:
        chamber: The chamber dict
        for_seat: Optional seat name (informational)
        up_to_index: Filter stages to stage_index < up_to_index (None = all)

    Returns:
        Context view dict with upstream_stages and available_artifact_ids.
    """
    if up_to_index is not None:
        stages = [s for s in chamber["stages"] if s["stage_index"] < up_to_index]
    else:
        stages = list(chamber["stages"])

    available_ids = {chamber["chamber_id"]}
    for stage in stages:
        available_ids.add(stage["stage_id"])
        summary = stage.get("summary")
        if summary is not None:
            sid = summary.get("id")
            if isinstance(sid, str):
                available_ids.add(sid)

    by_seat: dict[str, list[dict]] = {}
    for stage in stages:
        by_seat.setdefault(stage["seat"], []).append(stage)

    return {
        "chamber_id": chamber["chamber_id"],
        "for_seat": for_seat,
        "available_artifact_ids": set(available_ids),
        "upstream_stages": stages,
        "upstream_by_seat": by_seat,
        "stage_count": len(stages),
    }


# --- Query ---

def get_artifact_by_id(chamber: dict, artifact_id: str) -> dict | None:
    """Find a stage artifact by its ID. Linear scan."""
    for stage in chamber["stages"]:
        if stage["stage_id"] == artifact_id:
            return stage["artifact"]
    return None


def get_stages_by_seat(chamber: dict, seat: str) -> list[dict]:
    """Get all stage entries for a given seat."""
    return [s for s in chamber["stages"] if s["seat"] == seat]


def get_stage_at_index(chamber: dict, index: int) -> dict | None:
    """Get a stage entry by its index."""
    for stage in chamber["stages"]:
        if stage["stage_index"] == index:
            return stage
    return None


# --- Seal ---

def seal_chamber(chamber: dict) -> dict:
    """Transition chamber status from 'open' to 'sealed'."""
    if chamber["status"] == "sealed":
        raise ForgeChamberError("Chamber is already sealed")
    chamber["status"] = "sealed"
    return chamber


# --- Chamber-Level Validation ---

def validate_chamber(chamber: dict) -> list[dict]:
    """Validate chamber-level invariants that per-stage validation cannot catch.

    Checks:
    1. All refs resolve within artifact_index
    2. No duplicate stage IDs
    3. stage_index monotonically increasing (0, 1, 2, ...)
    4. artifact_index matches actual registered artifacts (no desync)
    5. All artifacts + summaries pass v1 validation
    6. Metadata passes null discipline

    Returns list of error dicts: {"code": str, "message": str, "path": str}
    """
    errors: list[dict] = []

    def _err(code: str, message: str, path: str) -> dict:
        return {"code": code, "message": message, "path": path}

    expected_ids = {chamber["chamber_id"]}
    seen_stage_ids: set[str] = set()

    for i, stage in enumerate(chamber["stages"]):
        stage_id = stage.get("stage_id", "")

        # 2. No duplicate stage IDs
        if stage_id in seen_stage_ids:
            errors.append(_err(
                "CHAMBER.DUPLICATE_STAGE_ID",
                f"Duplicate stage ID: {stage_id}",
                f"stages[{i}].stage_id",
            ))
        seen_stage_ids.add(stage_id)
        expected_ids.add(stage_id)

        summary = stage.get("summary")
        if summary is not None:
            sid = summary.get("id")
            if isinstance(sid, str):
                expected_ids.add(sid)

        # 3. stage_index monotonically increasing
        if stage.get("stage_index") != i:
            errors.append(_err(
                "CHAMBER.INDEX_NOT_MONOTONIC",
                f"Expected stage_index={i}, got {stage.get('stage_index')}",
                f"stages[{i}].stage_index",
            ))

    # 4. artifact_index matches actual registered artifacts
    actual_index = chamber.get("artifact_index", set())
    if isinstance(actual_index, list):
        actual_index = set(actual_index)

    if actual_index != expected_ids:
        missing = expected_ids - actual_index
        extra = actual_index - expected_ids
        if missing:
            errors.append(_err(
                "CHAMBER.INDEX_DESYNC",
                f"artifact_index missing IDs: {sorted(missing)}",
                "artifact_index",
            ))
        if extra:
            errors.append(_err(
                "CHAMBER.INDEX_DESYNC",
                f"artifact_index has extra IDs: {sorted(extra)}",
                "artifact_index",
            ))

    # 5. All artifacts + summaries pass v1 validation
    for i, stage in enumerate(chamber["stages"]):
        artifact = stage.get("artifact")
        summary = stage.get("summary")

        if artifact is not None:
            art_errors = validate_artifact_envelope_v1(artifact, actual_index)
            for e in art_errors:
                errors.append(_err(
                    e.get("code", "UNKNOWN"),
                    e.get("message", "validation error"),
                    f"stages[{i}].artifact.{e.get('path', '')}",
                ))

        if summary is not None:
            sum_errors = validate_summary_view_v1(summary, actual_index)
            for e in sum_errors:
                errors.append(_err(
                    e.get("code", "UNKNOWN"),
                    e.get("message", "validation error"),
                    f"stages[{i}].summary.{e.get('path', '')}",
                ))

    # 1. All refs resolve within artifact_index
    for i, stage in enumerate(chamber["stages"]):
        artifact = stage.get("artifact", {})
        for j, ref_entry in enumerate(artifact.get("refs", [])):
            if isinstance(ref_entry, dict) and ref_entry.get("state") == "resolved":
                ref_id = ref_entry.get("ref", "")
                if ref_id not in actual_index:
                    errors.append(_err(
                        "REF.REF_UNRESOLVED",
                        f"Ref {ref_id!r} not in chamber artifact_index",
                        f"stages[{i}].artifact.refs[{j}]",
                    ))

    # 6. Metadata passes null discipline
    if "metadata" in chamber:
        metadata = chamber["metadata"]
        if metadata is not None and isinstance(metadata, dict):
            try:
                validate_record(metadata)
            except ForgeNullError as e:
                errors.append(_err(
                    "ABSENCE.MISSING_STATE_LABEL",
                    f"Metadata null discipline violation: {e}",
                    "metadata",
                ))

    return errors


# --- Persistence: JSON Primary ---

def _safe_filename(chamber_id: str) -> str:
    return chamber_id.replace(":", "_")


def _get_base_dir(base_dir: str | Path | None) -> Path:
    if base_dir is not None:
        return Path(base_dir)
    return _DEFAULT_BASE_DIR


def _chambers_dir(base_dir: Path) -> Path:
    return base_dir / "chambers"


def save_chamber(chamber: dict, *, base_dir: str | Path | None = None) -> Path:
    """Serialize chamber to JSON and update SQLite index.

    Converts artifact_index set -> sorted list for JSON.
    Creates directories if needed. Returns the written file path.
    """
    bd = _get_base_dir(base_dir)
    chambers = _chambers_dir(bd)
    chambers.mkdir(parents=True, exist_ok=True)

    data = dict(chamber)
    idx = data.get("artifact_index", set())
    if isinstance(idx, set):
        data["artifact_index"] = sorted(idx)

    filename = _safe_filename(chamber["chamber_id"]) + ".json"
    file_path = chambers / filename

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _index_chamber(chamber, str(file_path), base_dir=bd)

    return file_path


def load_chamber(chamber_id: str, *, base_dir: str | Path | None = None) -> dict:
    """Load chamber from JSON, converting artifact_index list -> set.

    Raises ForgeChamberError if file not found.
    """
    bd = _get_base_dir(base_dir)
    chambers = _chambers_dir(bd)
    filename = _safe_filename(chamber_id) + ".json"
    file_path = chambers / filename

    if not file_path.exists():
        raise ForgeChamberError(f"Chamber file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    idx = data.get("artifact_index", [])
    if isinstance(idx, list):
        data["artifact_index"] = set(idx)

    return data


# --- Persistence: SQLite Index ---

def _get_db_path(base_dir: Path) -> Path:
    chambers = _chambers_dir(base_dir)
    chambers.mkdir(parents=True, exist_ok=True)
    return chambers / "chamber_index.db"


def _init_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chambers (
                chamber_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                stage_count INTEGER NOT NULL,
                seats TEXT NOT NULL,
                file_path TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _index_chamber(
    chamber: dict,
    file_path: str,
    *,
    base_dir: str | Path | None = None,
) -> None:
    """Upsert chamber row into SQLite index. Called by save_chamber."""
    bd = base_dir if isinstance(base_dir, Path) else _get_base_dir(base_dir)
    db_path = _get_db_path(bd)
    _init_db(db_path)

    seats = sorted({s["seat"] for s in chamber.get("stages", [])})

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO chambers
                (chamber_id, status, created_at, stage_count, seats, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chamber["chamber_id"],
                chamber["status"],
                chamber["created_at"],
                len(chamber.get("stages", [])),
                json.dumps(seats),
                file_path,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_chambers(
    *,
    base_dir: str | Path | None = None,
    status: str | None = None,
) -> list[dict]:
    """List chambers from SQLite index.

    Optional status filter ('open' or 'sealed').
    Reads from SQLite only — no JSON loading.
    """
    bd = _get_base_dir(base_dir)
    db_path = _get_db_path(bd)
    _init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM chambers WHERE status = ? ORDER BY created_at",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chambers ORDER BY created_at"
            ).fetchall()

        return [
            {
                "chamber_id": row["chamber_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "stage_count": row["stage_count"],
                "seats": json.loads(row["seats"]),
                "file_path": row["file_path"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_chamber_summary(
    chamber_id: str,
    *,
    base_dir: str | Path | None = None,
) -> dict | None:
    """Quick metadata lookup from SQLite without loading full JSON.

    Returns None if not found.
    """
    bd = _get_base_dir(base_dir)
    db_path = _get_db_path(bd)
    _init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM chambers WHERE chamber_id = ?",
            (chamber_id,),
        ).fetchone()

        if row is None:
            return None

        return {
            "chamber_id": row["chamber_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "stage_count": row["stage_count"],
            "seats": json.loads(row["seats"]),
            "file_path": row["file_path"],
        }
    finally:
        conn.close()


# --- End-to-end demo ---

if __name__ == "__main__":
    import shutil
    import tempfile

    print("=== forge_chamber.py — Chamber/Context System (Phase 3) ===\n")

    from forge_nulls import AbsenceState
    from forge_stage_output import create_v1_stage_artifact, create_v1_stage_summary

    tmp_dir = Path(tempfile.mkdtemp(prefix="forge_chamber_"))

    try:
        # 1. Create chamber
        print("1. Creating chamber 'chamber:run100:v1':")
        chamber = create_chamber("chamber:run100:v1")
        print(f"   chamber_id: {chamber['chamber_id']}")
        print(f"   status: {chamber['status']}")
        print(f"   artifact_index: {chamber['artifact_index']}")
        print()

        # 2. Stage 0 — Architect produces plan
        print("2. Stage 0 — Architect produces plan:")
        architect_art = create_v1_stage_artifact(
            stage_id="artifact:run100:stage:architect:r1",
            seat="architect",
            producer_name="architect-agent",
            producer_role="architect",
            output="Build a schema validator with strict fail-closed defaults.",
        )
        architect_summary = create_v1_stage_summary(
            architect_art,
            "Architect proposes strict fail-closed schema validator.",
        )
        entry0 = register_stage(chamber, architect_art, architect_summary)
        print(f"   stage_index: {entry0['stage_index']}")
        print(f"   stage_id: {entry0['stage_id']}")
        print(f"   seat: {entry0['seat']}")
        print()

        # 3. Stage 1 — Builder uses context view
        print("3. Stage 1 — Builder gets context, produces code:")
        ctx = get_context_view(chamber, for_seat="builder")
        print(f"   context.for_seat: {ctx['for_seat']}")
        print(f"   context.stage_count: {ctx['stage_count']}")
        print(f"   context.available_artifact_ids: {sorted(ctx['available_artifact_ids'])}")

        builder_art = create_v1_stage_artifact(
            stage_id="artifact:run100:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="def validate(schema): return check(schema, strict=True)",
            source_refs=["artifact:run100:stage:architect:r1"],
        )
        builder_summary = create_v1_stage_summary(
            builder_art,
            "Builder implemented strict schema validation.",
            extra_source_refs=["artifact:run100:stage:architect:r1"],
        )
        entry1 = register_stage(chamber, builder_art, builder_summary)
        print(f"   registered stage_index: {entry1['stage_index']}")
        print()

        # 4. Stage 2 — Critic sees all upstream
        print("4. Stage 2 — Critic gets full context, produces critique:")
        ctx2 = get_context_view(chamber, for_seat="critic")
        print(f"   context.stage_count: {ctx2['stage_count']}")
        print(f"   upstream seats: {list(ctx2['upstream_by_seat'].keys())}")

        critic_art = create_v1_stage_artifact(
            stage_id="artifact:run100:stage:critic:r1",
            seat="critic",
            producer_name="critic-agent",
            producer_role="critic",
            output="Schema validation looks correct. One concern: no input size limit.",
            source_refs=[
                "artifact:run100:stage:architect:r1",
                "artifact:run100:stage:builder:r1",
            ],
            findings=[
                {"code": "CRITIQUE.CRIT_SECURITY", "detail": "No input size limit on schema"},
            ],
        )
        critic_summary = create_v1_stage_summary(
            critic_art,
            "Critic approved with one security concern about input size.",
            extra_source_refs=[
                "artifact:run100:stage:architect:r1",
                "artifact:run100:stage:builder:r1",
            ],
        )
        entry2 = register_stage(chamber, critic_art, critic_summary)
        print(f"   registered stage_index: {entry2['stage_index']}")
        print()

        # 5. Seal chamber
        print("5. Sealing chamber:")
        seal_chamber(chamber)
        print(f"   status: {chamber['status']}")
        print()

        # 6. Validate chamber
        print("6. Validating sealed chamber:")
        errors = validate_chamber(chamber)
        print(f"   errors: {errors}")
        assert errors == [], f"FAILED: {errors}"
        print("   PASSED")
        print()

        # 7. Persistence round-trip
        print("7. Persistence round-trip:")
        saved_path = save_chamber(chamber, base_dir=tmp_dir)
        print(f"   saved to: {saved_path}")
        loaded = load_chamber("chamber:run100:v1", base_dir=tmp_dir)
        print(f"   loaded chamber_id: {loaded['chamber_id']}")
        print(f"   artifact_index type: {type(loaded['artifact_index']).__name__}")
        errors_loaded = validate_chamber(loaded)
        print(f"   post-load validation errors: {errors_loaded}")
        assert errors_loaded == [], f"FAILED post-load: {errors_loaded}"
        print("   PASSED")
        print()

        # 8. SQLite index
        print("8. SQLite index listing:")
        chambers_list = list_chambers(base_dir=tmp_dir)
        print(f"   chambers found: {len(chambers_list)}")
        for c in chambers_list:
            print(f"   - {c['chamber_id']}: status={c['status']}, "
                  f"stages={c['stage_count']}, seats={c['seats']}")

        summary_info = get_chamber_summary("chamber:run100:v1", base_dir=tmp_dir)
        print(f"   get_chamber_summary: {summary_info}")
        print()

        # 9. Rejections
        print("9. Rejection tests:")

        # 9a. Sealed registration
        print("   9a. Reject registration on sealed chamber:")
        try:
            dummy_art = create_v1_stage_artifact(
                stage_id="artifact:run100:stage:extra:r1",
                seat="extra",
                producer_name="extra-agent",
                producer_role="extra",
                output="Should not be allowed",
            )
            register_stage(chamber, dummy_art, summary_state="not_generated")
            print("      UNEXPECTED PASS")
        except ForgeChamberError as e:
            print(f"      ForgeChamberError: {e}")

        # 9b. Duplicate ID
        print("   9b. Reject duplicate artifact ID:")
        chamber2 = create_chamber("chamber:run101:v1")
        art_dup = create_v1_stage_artifact(
            stage_id="artifact:run101:stage:builder:r1",
            seat="builder",
            producer_name="builder-agent",
            producer_role="builder",
            output="First registration",
        )
        register_stage(chamber2, art_dup, summary_state="not_generated")
        try:
            register_stage(chamber2, art_dup, summary_state="not_generated")
            print("      UNEXPECTED PASS")
        except ForgeChamberError as e:
            print(f"      ForgeChamberError: {e}")

        # 9c. Dangling ref
        print("   9c. Reject dangling ref:")
        chamber3 = create_chamber("chamber:run102:v1")
        try:
            dangling_art = create_v1_stage_artifact(
                stage_id="artifact:run102:stage:builder:r1",
                seat="builder",
                producer_name="builder-agent",
                producer_role="builder",
                output="References non-existent upstream",
                source_refs=["artifact:run102:stage:architect:r1"],
            )
            register_stage(chamber3, dangling_art, summary_state="not_generated")
            print("      UNEXPECTED PASS")
        except ForgeChamberError as e:
            print(f"      ForgeChamberError: {e}")

        # 9d. Missing summary_state
        print("   9d. Reject missing summary_state:")
        chamber4 = create_chamber("chamber:run103:v1")
        try:
            art_no_state = create_v1_stage_artifact(
                stage_id="artifact:run103:stage:builder:r1",
                seat="builder",
                producer_name="builder-agent",
                producer_role="builder",
                output="No summary provided",
            )
            register_stage(chamber4, art_no_state)
            print("      UNEXPECTED PASS")
        except ForgeChamberError as e:
            print(f"      ForgeChamberError: {e}")
        print()

        # 10. Query demo
        print("10. Query demos:")
        art_found = get_artifact_by_id(chamber, "artifact:run100:stage:builder:r1")
        print(f"    get_artifact_by_id('...builder:r1'): "
              f"{art_found['id'] if art_found else None}")

        critic_stages = get_stages_by_seat(chamber, "critic")
        print(f"    get_stages_by_seat('critic'): {len(critic_stages)} stage(s)")

        stage1 = get_stage_at_index(chamber, 1)
        print(f"    get_stage_at_index(1): "
              f"{stage1['stage_id'] if stage1 else None}")

        missing = get_artifact_by_id(chamber, "artifact:nonexistent:v1")
        print(f"    get_artifact_by_id('nonexistent'): {missing}")

        print("\nAll Phase 3 scenarios passed.")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
