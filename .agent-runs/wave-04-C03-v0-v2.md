# C03 v0-v2 verification

Scope: `labs/consensus/raft/`, `tests/consensus/raft/`, and the three tutorial checkpoints. v3-v8 remain deferred.

Commands and observed results:

```text
$ uv run pytest tests/consensus/raft -q
3 passed in 0.30s

$ for v in 0 1 2; do uv run python -m labs.consensus.raft.experiments "$v"; done
{"commit_index": 1, "state": {"mode": "safe"}}
{"double_vote_rejected": true, "term": 4, "vote": "b"}
{"repaired_term": 3, "state": {"mode": "new"}}
```

The v1 command performs a real child-process exit and recovery from the persisted JSON file. v2 exercises a real prefix rejection and conflicting suffix replacement. This evidence does not claim majority replication, complete elections, crash recovery at every boundary, or production consensus.

Tutorial-only extraction replay:

```text
$ uv run python tests/consensus/raft/replay_c03.py
C03 tutorial v0-v2 replay ok
```

The replay writes each version's marked files into a fresh temporary package. v0 asserts that its extracted model has neither persistence nor AppendEntries; v1 executes a real crash/restart vote recovery; v2 executes the extracted AppendEntries conflict repair.

The same replay now executes the standalone v3-v8 fences in fresh temporary directories and requires non-empty output for each checkpoint.
