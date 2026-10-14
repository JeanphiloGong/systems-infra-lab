# C03 v1: election terms and durable votes

Scenario: three nodes time out together, split the vote, then only `a` times out and wins term 2; node `b` crashes after voting.

Pressure/change: add `tick`, candidate/leader roles, ordered vote messages, and `persist` before a vote response.

Checkpoint: `simultaneous_candidates=3`, `elected_term=2`, restart vote is `a`, and the crash subprocess exits 74 while rejecting a second same-term vote.

Limit/next: no replicated log or commit quorum yet. v2 adds AppendEntries prefix validation and suffix repair.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v1/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 1`.

**Naive:** grant votes without durable term state. **Break:** crash after voting enables a second vote. **Change:** tick-driven roles/messages and persist before response. **Check:** three candidates, term-2 election, exit 74, and restart vote. **Freeze:** v1 snapshots named above. **Limit/Still-lacks:** no replicated log/commit quorum. **Next:** v2 prefix repair.
