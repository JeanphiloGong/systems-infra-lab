# C03 v6: queued network faults

Scenario: a three-node cluster loses, duplicates, and reorders AppendEntries and votes while one leader is partitioned.

Pressure/change: route messages through a deterministic queue, replay selected drops/duplicates/reordering, and retain prefix repair plus quorum commit.

Checkpoint: at least one message is dropped; final `commit=2`, state is `{'stable': 'yes', 'mode': 'successor'}`, and the old leader becomes follower.

Limit/next: queue faults are deterministic and in-process, with fixed membership. v7 adds snapshot compaction for a lagging follower.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v6/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 6`.

**Naive:** assume reliable ordered delivery. **Break:** drop, duplicate, and reorder messages during a partition. **Change:** deterministic queue fault injection with existing prefix repair/quorum commit. **Check:** dropped count positive, final commit 2, successor state, old leader follower. **Freeze:** v6 snapshots named above. **Limit/Still-lacks:** in-process fixed membership. **Next:** v7 snapshots.
