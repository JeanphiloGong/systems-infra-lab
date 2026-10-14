# R01 Independent Closeout Review: PASS

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Independent verification

```text
$ uv run pytest tests/replication/leader_follower -q
14 passed in 0.54s

$ uv run pytest tests/replication/leader_follower/test_replay_r01.py -q
6 passed in 0.37s

$ uv run python ...
5 exact fence parity checks passed
```

The full suite covers the v0 two-interpreter writer/reader checkpoint, v0
restart and ordered application, v1 stale visibility, v2 leader reads and
bounded read-after-write barriers, v3 asynchronous versus follower
acknowledgment and measured injected delay, and v4 persisted resume,
duplicate delivery, and gap rejection. The replay suite executes each
complete v0-v4 tutorial checkpoint in isolation. An independent parity check
compared each single Markdown Python fence with its referenced implementation
file; all five matched exactly.

## Closeout comparison

`wave-10-r01-author-closeout.md` accurately describes the current source and
tests. The v0 `--writer` and `--reader` modes launch as separate Python
interpreters in `test_v0_writer_and_receiver_are_separate_processes`, and the
reader recovers position 2 plus the `paid` value from the JSON checkpoint.
The later versions match their stated pressure and checkpoint behavior.

The teaching boundaries remain explicit and acceptable for this module:
checkpoint writes are local JSON writes without atomic rename or checksums,
v3 latency measures local follower application with injected delay, and the
model has no multi-replica failover protocol. Those limits are disclosed in
the closeout and belong to later durability and distributed-state topics.

Decision: **PASS** for R01 v0-v4 closeout and current tutorial/source scope.
No implementation, tutorial, plan, progress, or index files were changed;
only this review artifact was added. No abstraction or cleanup was
introduced.
