# R02 build evidence

R02 uses a deterministic versioned in-memory replication model under `labs/replication/consistency/`:

- v0 `v0.py`: asynchronous stale reads and eventual convergence after pending updates apply.
- v1 `v1.py`: session write versions and read-your-writes fallback while other clients can still read stale replica state.
- v2 `v2.py`: fixed single-writer linearizable reads with a small history check.
- v3 `v3.py`: read repair for the selected stale key only; unread keys remain unchanged.
- v4 `v4.py`: eventual, session, snapshot, and linearizable contract comparison, with linearizable reads rejecting a partition.

Each tutorial version under `tutorials/05-replication/02-consistency/` contains one complete source fence marked with its exact target path. Replay extracts each fence into an isolated subprocess and executes it.

Verification:

```text
uv run python -m compileall -q labs/replication/consistency
uv run python -m pytest tests/replication/consistency -q
11 passed
```

This is a local teaching model. It does not provide a formal consistency proof, consensus, automatic failover, or PostgreSQL behavior. No commits were made; independent review is required.

