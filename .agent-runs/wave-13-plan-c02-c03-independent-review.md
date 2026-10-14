# C02/C03 Plan Batch Independent Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Replay evidence

C02 v0-v4 replay passed with the expected election, durable vote, fencing,
partition, and restart observations:

```text
$ uv run python tests/consensus/leader_election/replay_c02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
```

C03 v0-v7 replay passed independently. Representative outputs included the
v3 current-term commit boundary, v5 filesystem crash-point exit matrix, v6
queued network-fault delivery, and v7 snapshot compaction/recovery:

```text
$ uv run python tests/consensus/raft/replay_c03.py --version 0 ... --version 7
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok
v5 replay ok
v6 replay ok
v7 replay ok

$ uv run pytest tests/consensus/leader_election/test_c02.py \
    tests/consensus/raft/test_c03.py -q
12 passed in 2.06s
```

The requested v8 check was also run:

```text
$ uv run python tests/consensus/raft/replay_c03.py --version 8
RuntimeError: set ETCD_BINARY to an installed etcd v3.5.17 executable
```

This is an explicit external prerequisite and remains **unverified**. It is
not counted as a pass or as an implementation failure.

## Source/tutorial fidelity

C02's ten checkpoint fences (two per v0-v4) resolve to existing files and
match their corresponding `labs/consensus/leader_election` sources exactly.

C03 replay executes all version fences in isolated temporary directories, but
an independent source comparison found drift in the repository boundary:

- v0's two fences match their lab files.
- v1's `advanced.py` and `advanced_experiments.py` fences differ from the
  corresponding lab files.
- v2's `model.py` and `experiments.py` fences differ from their lab files.
- v3-v7 `advanced_experiments.py` fences differ from the lab file.
- v8's three fences are explicitly compared to repository sources by the
  replay script, but the etcd experiment could not run without the binary.

The isolated replay proves that the embedded C03 fences run and produce the
stated observations. It does not prove parity with the current lab files for
v1-v7. This matters because each revised plan names the complete source fence
as its freeze artifact; the current tutorial/lab mismatch makes that claim
ambiguous and can let later source changes bypass the plan checkpoint.

## Verdicts

**C02: PASS.** All five replays and focused tests passed, and tutorial/source
fidelity is exact for the checkpoint files.

**C03: REVISE.** v0-v7 behavior replays and tests pass, and v8's missing etcd
binary is correctly disclosed, but v1-v7 tutorial fences are not synchronized
with their current lab files. Align the fences and sources or explicitly
define the fences as independent historical checkpoints before accepting the
14-plan batch.

Overall decision: **REVISE** for C02/C03. No implementation, tutorial, plan,
progress, or index files were changed; only this review artifact was added.
No abstraction or cleanup was introduced.
