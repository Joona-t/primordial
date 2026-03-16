#!/usr/bin/env python3
"""Queue Worker v1 helpers (workspace-local).

Constraints:
- No new event kinds/fields in out/activity_feed.jsonl.
- Task bracketing is written to out/queue_ledger.jsonl.
- Cursor advances only after ledger record.

This module is imported by run_queue.py.
Stdlib only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
QUEUE = os.path.join(WORKSPACE, "out", "console_queue.jsonl")
STATE = os.path.join(WORKSPACE, "out", "console_queue_state.json")
LEDGER = os.path.join(WORKSPACE, "out", "queue_ledger.jsonl")


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _atomic_write(path: str, data: bytes) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def load_state() -> dict:
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            st = json.load(f)
        if not isinstance(st, dict):
            return {"schemaVersion": 1, "byte_cursor": 0, "updated_at": ""}
        return {
            "schemaVersion": 1,
            "byte_cursor": int(st.get("byte_cursor", 0) or 0),
            "updated_at": str(st.get("updated_at", "")),
        }
    except FileNotFoundError:
        return {"schemaVersion": 1, "byte_cursor": 0, "updated_at": ""}


def save_state(byte_cursor: int) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    obj = {"schemaVersion": 1, "byte_cursor": int(byte_cursor), "updated_at": _utc_iso_z()}
    _atomic_write(STATE, (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def append_ledger(kind: str, *, task_id: str, ok: bool | None = None, detail: str = "", meta: dict | None = None) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    rec = {
        "ts": _utc_iso_z(),
        "kind": kind,
        "task_id": task_id,
    }
    if ok is not None:
        rec["ok"] = bool(ok)
    if detail:
        rec["detail"] = (detail[:299] + "…") if len(detail) > 300 else detail
    if meta:
        # meta must be non-sensitive and allowlisted per kind
        if kind.startswith("patch."):
            allow={"patch_file","touched_files","pre_validate","post_validate","tests_status","reason"}
            rec["meta"]={k:v for k,v in meta.items() if k in allow}
        elif kind.startswith("task."):
            allow={"queue_byte_start"}
            rec["meta"]={k:v for k,v in meta.items() if k in allow}
        else:
            rec["meta"] = {}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def next_task() -> tuple[dict, int, int] | None:
    """Return (task_obj, line_start, line_end) for the next queue item after cursor."""
    st = load_state()
    cursor = int(st.get("byte_cursor", 0) or 0)

    if not os.path.exists(QUEUE):
        return None

    size = os.path.getsize(QUEUE)
    if cursor > size:
        cursor = size

    with open(QUEUE, "rb") as f:
        f.seek(cursor)
        while True:
            line_start = f.tell()
            line = f.readline()
            if not line:
                return None
            line_end = f.tell()
            if not line.strip():
                cursor = line_end
                continue
            try:
                obj = json.loads(line.decode("utf-8", errors="replace"))
            except Exception:
                # Skip malformed line; do not advance state cursor (operator should fix queue file)
                return None
            if isinstance(obj, dict):
                return obj, line_start, line_end


def advance_cursor_after_ledger(line_end: int) -> None:
    # Only call after writing task.* ledger entries.
    save_state(line_end)
