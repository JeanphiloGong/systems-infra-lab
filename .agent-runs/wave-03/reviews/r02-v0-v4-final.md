# R02 v0-v4 independent review

Verdict: pass against the original roadmap scope.

The complete fences model eventual stale reads and convergence (v0),
session-level read-your-writes while another client may remain stale (v1), a
fixed single-writer linearizable contract with a checkable history (v2),
key-scoped read repair for an explicitly single-writer ordered version (v3),
and eventual/session/snapshot/linearizable contracts with a partition
counterexample rejecting linearizable reads (v4). The tutorials state the
single-writer/no-failover boundary and that unread keys are not repaired.

Independent verification:

```text
uv run pytest tests/replication/consistency -q
11 passed in 0.22s
```

The replay suite extracts exactly one source fence for every version and runs
each in a fresh subprocess; fence uniqueness is asserted. No reviewer source
or tutorial edits were made.
