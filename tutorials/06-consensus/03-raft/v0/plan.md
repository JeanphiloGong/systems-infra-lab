# C03 v0: one log drives one state machine

Scenario: a node appends one command and applies only committed contiguous entries.

Pressure/change: freeze `model.py` and `experiments.py` with one safe entry, commit index advancement, and state-machine application.

Checkpoint: replay output is exactly `commit_index=1` and `state={'mode': 'safe'}`; the source must not contain persistence or `append_entries` yet.

Limit/next: single node, no terms, votes, replication, or crash recovery. v1 adds elections and durable term/vote state.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 0`.

**Naive:** apply an appended command immediately. **Break:** uncommitted state changes are visible. **Change:** advance commit index and apply contiguous entries only. **Check:** exact commit/state output and no persistence/AppendEntries. **Freeze:** model and experiment fences. **Limit/Still-lacks:** single node, no election or crash recovery. **Next:** v1 adds terms and votes.
