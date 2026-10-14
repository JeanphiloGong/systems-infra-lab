# Wave-18 F03/F04 plan author evidence

## Scope

Rewrote only these version plans:

- `tutorials/02-traffic/03-retry/v0-v4/plan.md`
- `tutorials/02-traffic/04-herd/v0-v3/plan.md`

Added no implementation, tutorial-body, index, or progress changes.

## Plan contract

Each version now names its concrete scenario and previous gap, one pressure,
the naive break, one mechanism in Change, exact observable checks and output,
the frozen source checkpoint, explicit limitations, the next pressure, and a
version-specific replay command. The plans preserve the existing boundaries:
F03 v0-v4 uses the resilience checkpoints and F04 v0-v3 uses the extracted
asyncio herd checkpoints. F04 v3 explicitly records that process-local flights
do not deduplicate across processes.

## Verification commands

```bash
uv run pytest tests/traffic/retry -q
uv run pytest tests/traffic/herd/test_f04.py -q
```

The replay tests execute exact tutorial fences in temporary directories. The
F03 v2 socket check has a short real-time assertion and the F04 v3 check starts
two subprocesses; both remain part of the documented environment contract.

## Environment limits

No external service is required. The checks require the repository's Python
environment and `uv`; timing-sensitive checks may be affected by severe host
load. No claim of production-grade distributed coordination is made.
