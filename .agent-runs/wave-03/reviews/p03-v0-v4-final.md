# P03 v0-v4 final independent review

Verdict: pass.

The complete checkpoints now embed the migration protocol itself. v0 pauses
writes and verifies copied contents; v1 records the post-watermark background
gap; v2 replays update and delete deltas with sequence deduplication; v3
applies a barrier, switches route version, verifies reads, and rejects a stale
client route; v4 persists phase, owners, route version, fence, sequence, log,
and shard state, launches a fresh child process, reconstructs `Migration` and
`Route`, rejects a stale old-owner `write_from_owner`, and accepts a current
owner write after restart.

Independent verification:

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

The replay extracts each tutorial checkpoint into a temporary directory and
executes it without importing the repository implementation. No reviewer
source or tutorial edits were made.
