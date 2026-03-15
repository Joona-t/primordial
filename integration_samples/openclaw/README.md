# OpenClaw integration samples

These samples were copied from the VM-side OpenClaw workspace to support Phase 2 of Primordial.

## Included
- queue_worker.py
- check_queue_ledger.py
- queue_ledger.sample.jsonl

## Observed event kinds
- task.start
- task.done
- patch.proposed
- patch.failed
- patch.rejected
- patch.applied

## Notes
queue_worker.py states that it is imported by run_queue.py.
This sample captures the real queue/patch lifecycle path already present on the VM.
