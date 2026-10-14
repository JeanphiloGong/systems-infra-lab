# R01 v0/v3/v4 author evidence

Implemented the reviewed R01 gaps in the leader/follower sources, exact
tutorial checkpoints, and focused tests. v0 and v4 followers optionally write
JSON checkpoints after each applied entry and reload them in a fresh instance;
v0 keeps the original in-memory restart behavior when no path is configured.
v3 now supports an injected follower delay, records measured follower-ack
latency, and can recover acknowledged data from a checkpoint. v4 catch-up
passes the complete delivered prefix to `apply`, so duplicate delivery is
actually exercised and skipped by applied position.

```text
$ uv run pytest tests/replication/leader_follower -q
13 passed
$ uv run pytest tests/replication/leader_follower/test_replay_r01.py -q
6 passed
```

The examples remain intentionally small and use local JSON files rather than
an external process supervisor or database. Checkpoint writes are not atomic
rename-based commits, and v3's latency measures the local follower apply call;
these are teaching boundaries for the next durability/distributed-state
topics. R02 and shared progress/index files were untouched.
