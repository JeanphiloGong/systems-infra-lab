# C03 v7: snapshots preserve absolute positions

Scenario: follower `c` misses entries through index 2 while leader compacts its prefix; the next entry is absolute index 3.

Pressure/change: retain `base`/`last` metadata, snapshot state `x=2`, and send a snapshot when `nextIndex` falls inside the compacted range before appending index 3.

Checkpoint: leader `base=2,last=3`, empty compacted log before the new entry, snapshot `{'x':'2'}`; lagging follower ends at `base=2,last=commit=3,state={'x':'3'}` and trace includes `snapshot`.

Limit/next: one snapshot format and fixed membership. v8 combines all regressions with a real three-process etcd experiment.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v7/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 7`.

**Naive:** compact by deleting the prefix without absolute positions. **Break:** lagging follower asks for an index that no longer exists. **Change:** retain base/term and send snapshot before absolute index 3. **Check:** base/last/commit 2/3/3, snapshot x=2, follower x=3, trace snapshot. **Freeze:** v7 snapshots named above. **Limit/Still-lacks:** one local snapshot format. **Next:** v8 regression plus etcd.
