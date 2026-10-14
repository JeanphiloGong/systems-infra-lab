# R02 v2/v4 author evidence

Implemented the review findings in only R02 sources, tests, v2/v4 tutorials,
plans, and this record.

v2 now records `Operation(kind, key, value, version, invoked, returned)`.
`check_history` validates read values and keys against writes visible at the
read invocation, validates referenced versions, and rejects invalid intervals.
Failure-first tests cover a wrong value, wrong key, impossible version, and a
history that returns a value before its write can be observed.

v4 now retains per-key historical versions. A snapshot read selects the newest
version at or before its cut, including repeated multi-key reads after later
writes. Session reads with missing or stale replicas raise `ConnectionError`
when partitioned instead of bypassing the network boundary; after catch-up,
the same session read succeeds. The tutorial source fences were refreshed from
the implementation and their previous limitations were corrected.

```text
$ uv run pytest tests/replication/consistency -q
16 passed
$ uv run pytest tests/replication/consistency/test_replay_r02.py -q
6 passed
$ uv run python labs/replication/consistency/v2.py
Ada True
$ uv run python labs/replication/consistency/v4.py
Read(value='Ada', version=1)
ConnectionError
```

The model remains fixed-writer/in-memory: history validation is not a general
concurrent linearizability checker, and retained snapshot versions are not
durable storage. R03 and shared progress/index files were untouched.
