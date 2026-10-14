# C03 v3: commit after durable acknowledgments

Scenario: leader replicates an old-term entry and a current-term entry to fixed members. Only the current-term entry may advance the commit index after durable acks.

Pressure/change: followers validate prefix and persist before returning request-id acknowledgments; leader tracks `matchIndex` for current members.

Checkpoint: `old_term_commit=0`, `current_term_commit=2`, and `durable_lengths=[2,2,2]`.

Limit/next: assumes trusted non-Byzantine members and fixed membership. v4 rejects a stale candidate whose log is behind.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v3/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 3`.

**Naive:** commit on a caller-supplied member list or before durable ack. **Break:** old-term entries appear committed. **Change:** persist followers before request-id ack and track matchIndex. **Check:** old-term 0, current-term 2, durable lengths `[2,2,2]`. **Freeze:** v3 snapshots named above. **Limit/Still-lacks:** trusted fixed members only. **Next:** v4 log freshness.
