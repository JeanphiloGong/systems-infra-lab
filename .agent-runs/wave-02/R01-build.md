# R01 build evidence

R01 uses a deterministic local leader-follower protocol under `labs/replication/leader_follower/`:

- v0 `v0.py`: ordered log positions, key-value application, and restart-preserved applied progress.
- v1 `v1.py`: delayed follower application and reproducible stale reads.
- v2 `v2.py`: write-position read barriers, bounded waits, timeout, and leader-read fallback.
- v3 `v3.py`: asynchronous versus follower acknowledgment and the corresponding failure-loss boundary.
- v4 `v4.py`: interrupted catch-up, position-based resume, duplicate delivery, and gap rejection.

Each tutorial version under `tutorials/05-replication/01-leader-follower/` contains one complete source fence marked with the exact target path. `tests/replication/leader_follower/test_replay_r01.py` extracts and executes all five fences in isolated subprocesses, and `test_r01.py` checks the behavioral boundaries.

Verification:

```text
uv run python -m compileall -q labs/replication
uv run python -m pytest tests/replication/leader_follower -q
11 passed
```

This is an in-memory teaching model. It does not claim PostgreSQL streaming replication, automatic failover, leader election, or storage durability beyond the modeled state. No commits were made; independent review is required.

