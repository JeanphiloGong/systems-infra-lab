# R01 Repair Independent Review: REVISE

Independent verification passed:

```text
uv run pytest tests/replication/leader_follower -q
13 passed in 0.39s
uv run pytest tests/replication/leader_follower/test_replay_r01.py -q
6 passed in 0.37s
```

I additionally compared each v0-v4 tutorial fence with its implementation
source; all five have exact source parity.

The repair closes several prior gaps:

- v0/v4 support JSON checkpoint state and a fresh follower instance reloads
  applied position/data.
- v3 injects follower delay, records measured local follower-apply latency,
  tracks async versus follower acknowledgement, and reloads persisted data.
- v4 passes the complete delivered prefix to `apply`, so duplicate entries are
  actually offered to the idempotent position check; its fresh-instance
  catch-up test resumes from the persisted checkpoint.

## Remaining Original-Scope Gap

Roadmap R01 v0 requires “两个进程按日志复制键值更新；验证顺序和重启后的进度”.
The current v0 checkpoint only constructs Leader and Follower in one Python
process. Its JSON path is tested by creating a second `Follower` object in the
same pytest process; the extracted tutorial entry point uses no subprocess and
no inter-process log transport. This proves serialization/reload behavior, not
two-process replication. Add a deterministic writer/receiver subprocess
checkpoint (or explicitly revise the roadmap scope before acceptance) and
verify progress after the receiver process restarts.

The implementation honestly discloses that JSON writes are not atomic and that
v3 latency is local follower apply latency rather than network or disk
replication latency. Those are valid teaching boundaries, but they do not close
the explicit v0 process requirement.

Decision: **REVISE** for original R01 scope. The repaired behavior and fence
parity pass; v0 remains unaccepted until an independent-process replay is
demonstrated. No implementation, tutorial, plan, progress, or index files were
changed; only this review record was added.
