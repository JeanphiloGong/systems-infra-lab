# C03 v5: crash at file publication boundaries

Scenario: a node is killed before/after writing term, log, commit, and state files. Recovery must expose an old complete state or the fully published new state, never a mixed record.

Pressure/change: use temporary files, flush/fsync, directory replacement, and deterministic `os._exit` points in the advanced checkpoint.

Checkpoint: 12 crash cases exit with codes `{71,72,73}`; `commit:before_replace` recovers commit 0 while `commit:after_directory_sync` recovers commit 1, with corresponding term/vote/log/state assertions.

Limit/next: local filesystem durability only; no replicated failover. v6 drives replication through a queue with loss, duplicate, and reordering.

Freeze artifact: the exact historical fences are retained at `labs/consensus/raft/checkpoints/v5/advanced.py` and `advanced_experiments.py` for parity comparison.

Replay: `uv run python tests/consensus/raft/replay_c03.py --version 5`.

**Naive:** replace a durable file in one unobservable step. **Break:** kill between write/replace/fsync and recover mixed state. **Change:** temporary file, flush/fsync, replace, directory sync, deterministic exits. **Check:** 12 cases and exit codes 71–73 with old-or-new state. **Freeze:** v5 snapshots named above. **Limit/Still-lacks:** local filesystem only. **Next:** v6 queued network faults.
