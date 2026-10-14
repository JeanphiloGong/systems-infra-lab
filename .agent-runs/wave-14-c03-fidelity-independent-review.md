# C03 Fidelity Independent Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## v1-v7 verification

The historical snapshot parity check passed:

```text
$ uv run pytest tests/consensus/raft/test_fence_parity.py -q
.                                                                        [100%]
1 passed in 0.02s
```

The focused C03 tests also passed:

```text
$ uv run pytest tests/consensus/raft/test_c03.py -q
...                                                                      [100%]
3 passed in 0.10s
```

Each isolated replay v0-v7 passed independently, including v5's filesystem
crash-point matrix and v7's snapshot recovery:

```text
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
v5 replay ok
v6 replay ok
v7 replay ok
```

The parity test confirms v1-v7 tutorial fences equal their versioned files in
`labs/consensus/raft/checkpoints/vN/`. The replay output confirms those
historical checkpoints execute with the expected results.

## v8 status

The requested v8 replay was run:

```text
$ uv run python tests/consensus/raft/replay_c03.py --version 8
AssertionError: source drift: labs/consensus/raft/advanced_experiments.py
```

The replay stops at its explicit source comparison before launching etcd, so
the stated missing `ETCD_BINARY` prerequisite was not reached. The etcd
three-process experiment is therefore **UNVERIFIED**, and this run also
reveals a source synchronization issue: the v8 tutorial fence for
`advanced_experiments.py` is not equal to the current root lab file. The
author's v8 limitation remains valid, but the current failure is not solely an
environmental etcd absence.

## Decision

**REVISE overall.** C03 v1-v7 fidelity, replay, and focused tests pass. v8
remains unverified and additionally needs its source fence synchronized before
an etcd prerequisite result can be interpreted. No implementation, tutorial,
plan, progress, or index files were changed; only this review artifact was
added. No abstraction or cleanup was introduced.
