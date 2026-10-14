# Wave 19: C02/C03 explicit planning fields

Updated only C02 v0-v4 and C03 v0-v8 plans and this record. All 14 plans
now explicitly contain Naive, Break, Change, Check, Freeze,
Limit/Still-lacks, and Next. Existing checkpoint references and replay commands
remain in place. Corrected C02 v0/v1 prose that had confused the election
experiments: v0 reports three leader beliefs at logical time 6; v1 elects a
in term 1 and b in term 2 after isolating a.

Verification performed:

- Field check: all seven explicit fields present in all 14 plans.
- `uv run python tests/consensus/leader_election/replay_c02.py`: v0-v4 passed.
- Called `replay(version)` from `tests/consensus/raft/replay_c03.py` for
  each version 0 through 7: all eight isolated replays passed.
- Called the same replay for v8 with captured subprocess stderr: source
  comparison passed; execution reached `RuntimeError: set ETCD_BINARY to an
  installed etcd v3.5.17 executable`. Live etcd remains unverified.

No code, tutorial bodies, progress, or index files were changed. No new
abstraction was introduced; cleanup was limited to correcting the inaccurate
C02 plan statements noted above.
