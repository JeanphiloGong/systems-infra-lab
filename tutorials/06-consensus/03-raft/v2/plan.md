# C03 v2: reject bad prefixes and repair conflicts

Scenario: follower receives a leader entry whose previous index/term does not match, then receives a valid term-3 replacement for an old suffix.

Pressure/change: implement `append_entries` prefix checks, truncate conflicting suffixes, append the leader entry, and apply through commit index.

Checkpoint: invalid prefix is false; valid repair reports `repaired_term=3`, `state={'mode': 'new'}`; a committed record cannot be overwritten.

Limit/next: replication is still manually driven and acknowledgments do not advance a leader commit. v3 commits only after durable follower acknowledgments.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v2/model.py` and `experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 2`.

**Naive:** append entries without checking the previous term. **Break:** stale prefixes overwrite unrelated history. **Change:** validate prefix and truncate only uncommitted conflicts. **Check:** invalid false, repaired term/state exact, committed overwrite rejected. **Freeze:** v2 snapshots named above. **Limit/Still-lacks:** no leader commit advancement. **Next:** v3 durable acknowledgments.
