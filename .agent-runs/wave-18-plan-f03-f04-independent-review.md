# Wave-18 independent review: F03/F04

## Scope

Reviewed the revised plans:

- `tutorials/02-traffic/03-retry/v0-v4/plan.md`
- `tutorials/02-traffic/04-herd/v0-v3/plan.md`

## Plan fidelity

**PASS.** Every version names a concrete scenario and previous-version gap,
states the pressure and naive failure, introduces one mechanism change, gives
exact observations and a frozen source checkpoint, and records limitations,
next pressure, and a replay command. F03 progresses from retry amplification
through classification, bounded backoff, circuit breaking, and a shared
attempt budget. F04 progresses from an expiry herd through per-key
single-flight, cancellation/timeout isolation, and jitter/SWR with the
process-boundary limitation made explicit.

## Independent runtime evidence

```text
$ uv run pytest tests/traffic/retry -q
19 passed in 0.89s

$ uv run pytest tests/traffic/herd/test_f04.py -q
4 passed in 0.74s
```

The replay tests execute the exact tutorial fences in temporary directories.
The checks cover the version-specific behavior, including the short socket
timeout assertion and the multi-process F04 boundary. No external service was
required. Timing-sensitive checks remain subject to severe host load.

## Verdict

**PASS.** The plans are concrete, versioned, replayable, and independently
verified against their stated behavior. No implementation, tutorial body,
index, or progress file was changed by this review.
