# Wave 08: R02/R03 version plans

Changed only these plans and this record:

- tutorials/05-replication/02-consistency/v0/plan.md
- tutorials/05-replication/02-consistency/v1/plan.md
- tutorials/05-replication/02-consistency/v2/plan.md
- tutorials/05-replication/02-consistency/v3/plan.md
- tutorials/05-replication/02-consistency/v4/plan.md
- tutorials/05-replication/03-multi-leader/v0/plan.md
- tutorials/05-replication/03-multi-leader/v1/plan.md
- tutorials/05-replication/03-multi-leader/v2/plan.md
- tutorials/05-replication/03-multi-leader/v3/plan.md
- tutorials/05-replication/03-multi-leader/v4/plan.md

Each plan now gives a concrete Pressure/Naive/Break/Change/Check/Freeze/
Still-lacks/Next chain, links its preceding checkpoint, names complete source
dependencies, and contains executable version-specific pytest selectors.
R02 uses one extraction selector plus one behavior selector per version.
R03 has a single selector per version that extracts both the complete dependency
set and the tutorial's semantic check script, then executes both entry points.

Observed from the systems-infra-lab root:

```text
10 plans; 80 labels; 0 generic phrases; 0 broken links; 15 exact commands passed
uv run pytest tests/replication/consistency tests/replication/multi_leader -q
16 passed
```

The scan rejected the previous generic phrases, resolved relative tutorial links,
and executed every pytest command printed in these ten plans. Tests cover Ada
stale/session reads, fixed-writer history, key-local repair, partition rejection;
and R03 event delays, conflict sets, clock-skew LWW loss, counter permutations,
and equivalent single/multi leader workloads.

## Outstanding Roadmap Evidence

These are implementation/tutorial gaps, not changes to the roadmap:

- R02 v2: roadmap calls for checking real-time ordering. Current history omits
  operation invocation/completion intervals and keys; check_history validates
  version monotonicity only and does not validate values. A full history checker
  with overlapping operations and deliberately invalid histories remains work.
- R02 v4: SNAPSHOT rejects newer versions but retains no old versions. Thus
  it cannot return a prior snapshot after an update. Version retention and a
  multi-read snapshot demonstration remain necessary for the stated comparison.
- R02 v4: SESSION returns empty immediately when the replica lacks a key and
  bypasses the modeled network partition when reading the leader. Tests for a
  missing replica key, stale replica during partition, and a declared unavailable
  result are needed before claiming the general session contract under partition.
- R02 extraction tests check child exit status only. Specific behavior tests
  exercise repository modules, not extracted checkpoints; the plans disclose
  this split instead of claiming exact semantic replay is already proven.

R03's detailed tutorial checks already cover the stated small-model progression.
Its logical milliseconds are simulated, not real WAN latency or throughput;
G-Counter needs stable author identity and delivery, and LWW may discard successful
writes. These are declared model boundaries, not hidden production guarantees.

No progress/index files, runtime code, or tests were changed. No commit created.
Independent review remains pending.
