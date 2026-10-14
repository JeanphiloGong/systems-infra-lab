# C02/C03 version-plan revision evidence

Rewrote all 14 version plans with concrete, version-specific contracts:

- C02 leader election v0-v4: quorum campaigns, timeout/candidacy, durable
  votes, term/owner fencing, and partition/restart recovery.
- C03 Raft v0-v8: state-machine baseline, durable elections, prefix repair,
  durable acknowledgments, log freshness, filesystem crash points, queued
  network faults, snapshots, and the final etcd regression experiment.

Each plan identifies the real scenario, prior gap, deterministic pressure or
failure, one mechanism change, exact replay observation/assertion, complete
source fence as freeze artifact, limits, next pressure, and version-specific
replay command. Only the 14 plan files and this evidence record were changed.

Verification:

```text
$ uv run python tests/consensus/leader_election/replay_c02.py
v0-v4 replay ok
$ uv run python tests/consensus/raft/replay_c03.py --version 0 ... --version 7
v0-v7 replay ok
$ uv run pytest tests/consensus/leader_election/test_c02.py tests/consensus/raft/test_c03.py -q
12 passed
$ uv run python tests/consensus/raft/replay_c03.py --version 8
RuntimeError: set ETCD_BINARY to an installed etcd v3.5.17 executable
```

The v8 failure is an external prerequisite: the bundled replay requires an
installed etcd v3.5.17 executable via `ETCD_BINARY`. The v8 plan records this
requirement rather than treating the unavailable three-process etcd result as
verified. No code, tutorial body, docs/progress, or index files were changed;
no abstraction was added and no cleanup outside the requested plans was
needed.
