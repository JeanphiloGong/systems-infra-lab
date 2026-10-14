# C03 v0-v7 checkpoint fidelity evidence

Addressed the independent review's source/tutorial drift. The tutorial fences
remain the historical version checkpoints used by the isolated replay, and
each v1-v7 fence is now also stored as an exact versioned source snapshot:
`labs/consensus/raft/checkpoints/vN/{advanced,advanced_experiments}.py` (v2
uses `model.py` and `experiments.py`). A parity test compares every fence to
its corresponding snapshot. The current root lab files remain the formal
latest implementation; the versioned snapshots prevent historical freeze
artifacts from being silently replaced by later code.

The root `experiments.run` compatibility entry point was restored for the
existing focused tests while preserving the v2 behavior.

```text
$ uv run pytest tests/consensus/raft/test_fence_parity.py -q
1 passed
$ uv run pytest tests/consensus/raft/test_c03.py -q
3 passed
$ uv run python tests/consensus/raft/replay_c03.py --version 0 ... --version 7
v0-v7 replay ok
```

The v8 etcd experiment remains unverified because `ETCD_BINARY` for etcd
v3.5.17 is not installed. No docs/progress/index files were changed.
