# R01 acceptance closeout

R01 v0-v4 are aligned across implementation sources and tutorial
checkpoints. A parity check reports no differences between each complete
Markdown Python fence and its corresponding `labs/replication/leader_follower`
module.

Scope by version:

- **v0:** ordered log positions, durable local JSON checkpoint, and explicit
  `--writer`/`--reader` modes. The focused test launches two separate Python
  processes and asserts that the reader recovers position 2 and `paid` data.
- **v1:** separates receipt (`receive`) from visibility (`apply_one`), showing
  the stale-read interval.
- **v2:** adds leader reads and a follower read-after-write barrier with a
  bounded timeout.
- **v3:** contrasts async and follower acknowledgment, measures local
  follower-apply confirmation latency with injected delay, reports the
  unconfirmed loss boundary, and supports checkpoint reload.
- **v4:** resumes interrupted catch-up from a durable position, offers the
  complete delivered prefix so duplicate delivery is exercised, skips already
  applied positions, and rejects gaps.

```text
$ uv run pytest tests/replication/leader_follower -q
14 passed
$ uv run pytest tests/replication/leader_follower/test_replay_r01.py -q
6 passed
$ uv run pytest tests/replication/leader_follower/test_r01.py::test_v0_writer_and_receiver_are_separate_processes tests/replication/leader_follower/test_replay_r01.py -q
7 passed
```

Independent review status: `.agent-runs/wave-10-r01-v0-independent-review.md`
is **PASS** and confirms the two-process v0 behavior plus all five fence
parity checks. `.agent-runs/wave-09-r01-independent-review.md` records the
earlier v0 gap before that repair and should be read as superseded by the
wave-10 process review.

The implementation intentionally remains a teaching model: checkpoints are
local JSON writes without atomic rename or checksums; v3 latency is the local
follower apply call rather than network or disk replication latency; and there
is no multi-replica failover protocol. Those concerns belong to later
durability and distributed-state topics. No new abstraction was added in this
closeout, and no cleanup outside the R01 sources/tests/tutorials/evidence was
needed.
