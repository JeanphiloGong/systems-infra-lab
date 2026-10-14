# D02 v0-v4 final rereview

Verdict: pass.

The v3 checkpoint now uses its own `LockService` API and proves stale-owner
renewal is rejected while the current owner renews with the same token and
extends expiry to 5. Together with v0-v2 and v4, the series covers atomic
competition, lease-expiry overlap, fencing-resource stale-write rejection,
ownership-aware renew/release, and explicit no-write behavior when the lock
service is unavailable.

```text
uv run pytest tests/coordination/locks -q
4 passed in 0.02s
uv run python tests/coordination/locks/replay_d02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

No reviewer source or tutorial edits were made.
