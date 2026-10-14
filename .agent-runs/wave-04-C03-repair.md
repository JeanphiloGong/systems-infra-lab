# C03 repair evidence

This supersedes the rejected v3-v8 evidence. The original evidence remains immutable.

The repaired core is `labs/consensus/raft/advanced.py`: all acknowledgements come from fixed-member followers after they persist the received log; leaders track request IDs and match indexes; commits require a majority and the current term. Timers use an explicit logical clock. `advanced_experiments.py` runs simultaneous candidacies, stale-log voting, 12 subprocess crash boundaries, dropped/duplicated/reordered messages, and absolute-index snapshot installation.

Commands:

```text
$ uv run pytest tests/consensus -q
31 passed in 5.00s

$ ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd uv run python tests/consensus/raft/replay_c03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
v5 replay ok
v6 replay ok
v7 replay ok
v8 replay ok
```

The v8 replay also starts three local etcd 3.5.17 processes, kills the elected leader, writes through the surviving majority, restarts the old leader, verifies catch-up, then stops two members and verifies a minority write is not acknowledged. The binary is an external temporary test prerequisite and is not committed.

The tutorial replay extracts every marked source file into a fresh temporary package. It checks v0/v1 version boundaries, concrete JSON results for v3-v7, and the real etcd result for v8. Dynamic membership, joint consensus, linearizable reads, authentication, and production operations remain outside this tutorial.
