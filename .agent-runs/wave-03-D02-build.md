# D02 build evidence

Implemented `labs/coordination/locks/model.py` with atomic acquisition, lease expiry/renewal, monotonic fencing tokens, ownership-checked release, and fenced resource writes. Added v0-v4 tutorials, focused concurrency tests, and isolated replay.

Verification:

```text
uv run pytest tests/coordination/locks -q
3 passed

uv run python tests/coordination/locks/replay_d02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

v3 review fix: the checkpoint now exercises `LockService.renew` through the stale-owner rejection and current-owner extension paths, preserving token `2` and expiry `5`. Focused tests now report 4 passed.
