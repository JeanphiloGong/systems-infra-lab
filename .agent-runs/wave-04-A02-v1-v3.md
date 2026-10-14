# A02 v1-v3 author evidence

v0 was left unchanged. v1-v3 add `labs/recovery/checkpoint/store.py`, immutable numbered segments, checksummed snapshots, atomic manifest publication, reclamation after publication, and two-generation fallback.

```text
$ uv run pytest tests/recovery/checkpoint -q
11 passed in 2.61s

$ uv run python tests/recovery/checkpoint/replay_a02.py
A02 tutorial v1-v3 replay ok
```

The tests use fresh subprocesses for the three manifest publication crash points and recover with a new `Store` instance. v3 corrupts the newest snapshot, recovers from the older snapshot and its retained log tail, then removes a required segment and expects recovery to fail. Tutorial replay extracts the complete `store.py` fence for each version into a fresh temporary package and checks source equality before execution.

Scope remains the roadmap boundary: paused single writer, no background snapshot thread, no ARIES or concurrent writers.
