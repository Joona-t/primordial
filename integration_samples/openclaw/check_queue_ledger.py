#!/usr/bin/env python3
'''Validate out/queue_ledger.jsonl basic invariants.

Stdlib only. Does not read secrets. Workspace-local.
'''

from __future__ import annotations

import json
import os
import sys

WS = os.path.expanduser("~/.openclaw/workspace")
LEDGER = os.path.join(WS, "out", "queue_ledger.jsonl")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not os.path.exists(LEDGER):
        fail("missing queue_ledger.jsonl")

    required = {"ts", "kind", "task_id"}
    seen = 0
    for i, line in enumerate(open(LEDGER, "r", encoding="utf-8")):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            fail(f"line {i}: invalid JSON")
        if not isinstance(e, dict):
            fail(f"line {i}: not an object")
        miss = required - set(e.keys())
        if miss:
            fail(f"line {i}: missing {sorted(miss)}")
        if "detail" in e and isinstance(e["detail"], str) and len(e["detail"]) > 300:
            fail(f"line {i}: detail too long")
        seen += 1

    if seen == 0:
        fail("empty ledger")

    print("PASS")


if __name__ == "__main__":
    main()
