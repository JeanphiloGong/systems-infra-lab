# S05 v5, F01, and F02 final review

## S05 v5

Verdict: pass. The manifest checkpoint now uses real child termination
(`os._exit(71)` before replace and `os._exit(72)` after replace), fsyncs input
files and the temporary manifest, and fsyncs the directory after replacement.
The isolated replay seeds a valid old manifest, runs the publish child, starts
a fresh reader child, and verifies old/new coherent visibility and temporary
file behavior. Direct-child `.sst` validation rejects traversal, duplicates,
missing files, and symlinks. The printed checkpoint includes SSTable and
Tombstone dependencies and executes the actual CLI sequence.

```text
uv run pytest tests/storage/lsm -q
53 passed in 2.73s
uv run pytest tests/storage/lsm/test_s05_manifest_replay.py -q
1 passed in 0.76s
```

## F01

Verdict: pass. The official pool now sets `max_waiting=32`, while v0 reports
connect/query/total timings and repeated-connection counts. v3 includes the
transaction-pooling proxy experiment: two clients observe the same backend
PID while transaction-local session state and temporary tables do not survive
between clients. The client-pool example separately records that
`application_name` persists across reuse in this installed version.

With both PostgreSQL and PgBouncer endpoints configured:

```text
uv run pytest tests/traffic/connections -q
6 passed in 0.40s
uv run python tests/traffic/connections/replay_f01.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
```

The replay extracts each printed checkpoint into a temporary directory and
executes all non-test commands. Proxy replay is skipped only when the explicit
PgBouncer DSN is absent; it passed with `SYSTEMS_LAB_POOL_URL` configured.

## F02

Verdict: pass against the original roadmap scope. The bounded worker catches
job failures, keeps workers alive, and counts accepted queued/executing work
until completion. The balancer models overlapping arrivals with per-worker
FIFO queues, allowing least-inflight to account for heterogeneous service
times. v4 reports latency/backpressure behavior with a slow worker and source
arrival interval. Token-bucket tests use an injected clock for burst/refill
boundaries.

```text
uv run pytest tests/traffic/admission -q
5 passed in 0.11s
uv run python tests/traffic/admission/replay_f02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

No reviewer implementation edits were made. This supersedes the earlier
initial-draft blocker note for S05 v5 and F02; the earlier F01 scope reopening
is also superseded for the integrated proxy/max-waiting checkpoint.
