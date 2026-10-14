# P03 build evidence

Implemented `labs/partitioning/migration/store.py` with route versions, pause/copy, delta replay deduplication, barrier cutover, and stale owner fencing. Added v0-v4 tutorials and standalone checkpoints under `tutorials/03-partitioning-scaling/03-migration/`.

Verification:

```text
uv run pytest tests/partitioning/migration -q
3 passed

uv run python tests/partitioning/migration/replay_p03.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

The examples are deterministic in-memory migration models; they do not claim zero-downtime production behavior.

Each v0-v4 tutorial checkpoint now embeds the complete `Migration`/`Route` implementation and its version-specific scenario. Replay executes those extracted implementations in temporary directories; it does not import `labs.partitioning.migration`.

The v4 checkpoint persists phase, route owners/version, fence, sequence, log, and shard state to `migration-state.json`. A fresh subprocess reconstructs `Migration`/`Route`, calls `write_from_owner` with a stale token (raising `ValueError`), then calls it with the current token and persists the successful write.
