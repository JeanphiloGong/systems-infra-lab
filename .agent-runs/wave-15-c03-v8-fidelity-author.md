# C03 v8 source-fidelity repair evidence

Synchronized all three v8 tutorial checkpoints with the root lab sources:
`advanced.py`, `advanced_experiments.py`, and `etcd_demo.py`. Exact v8 copies
are also retained under `labs/consensus/raft/checkpoints/v8/`. The parity test
now covers v1-v8 and expects three fences for v8, so the replay's explicit v8
source-drift check passes before any runtime prerequisite is evaluated.

```text
$ uv run pytest tests/consensus/raft/test_fence_parity.py -q
1 passed
$ uv run python tests/consensus/raft/replay_c03.py --version 0 ... --version 7
v0-v7 replay ok
$ uv run python tests/consensus/raft/replay_c03.py --version 8
RuntimeError: set ETCD_BINARY to an installed etcd v3.5.17 executable
```

The remaining v8 failure is now solely the documented external etcd binary
requirement; source drift is resolved. No docs/progress/index files were
changed. The versioned snapshot and parity test are permanent checkpoint
fidelity artifacts; no temporary compatibility layer was added.
