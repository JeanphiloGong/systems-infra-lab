# Wave-19 independent plan review: C02/C03

## Findings

No blocking plan-field or contract inconsistency found. All 14 plans were
read individually against their replay contracts. Added fields name concrete
failures, mechanisms, observations, frozen artifacts, and remaining limits;
they do not widen the existing implementation scope.

## Per-version assessment

| Plan | Specific contract checked | Result |
| --- | --- | --- |
| C02 v0 | Timeout-only baseline; a/b/c leader beliefs and split brain at time 6 | PASS |
| C02 v1 | Majority election; a wins term 1, b loses then wins term 2 | PASS |
| C02 v2 | Restart retains term 7/vote b and rejects double voting | PASS |
| C02 v3 | Resource owner/term checks reject stale writes; successor value survives | PASS |
| C02 v4 | Partition, pause, restart distinguish belief from write permission | PASS |
| C03 v0 | Single-node committed contiguous application; no persistence/AppendEntries | PASS |
| C03 v1 | Split election, term-2 winner, durable vote and exit 74 | PASS |
| C03 v2 | Prefix validation and uncommitted suffix repair preserve committed data | PASS |
| C03 v3 | Durable acknowledgments and current-term commit: 0 then 2 | PASS |
| C03 v4 | Log freshness rejects stale candidate and preserves committed suffix | PASS |
| C03 v5 | Twelve publication crash cases, exit codes 71-73, old/new recovery | PASS |
| C03 v6 | Deterministic dropped/duplicated/reordered messages; final commit 2 | PASS |
| C03 v7 | Absolute positions and snapshot catch-up: base 2, last/commit 3 | PASS |
| C03 v8 | Existing model regressions plus three-process etcd 3.5.17 probe | Plan PASS; live runtime unverified |

C02 explicitly acknowledges shared helper code in its baseline; the new fields
do not claim version-isolated implementation. C03 retains historical checkpoint
references and the fixed-membership/local-model limitations. The corrected C02
v0/v1 observations agree with independent output.

## Independent verification

- `uv run python tests/consensus/leader_election/replay_c02.py`: all v0-v4 passed.
- Loaded `tests/consensus/raft/replay_c03.py` with `runpy` and called
  `replay(v)` for v0-v7: all eight exact-fence replays passed.
- C03 v8 was not rerun in this review. The author reports missing `ETCD_BINARY`;
  neither field completeness nor prior source comparison verifies live etcd.

## Verdict

PASS for this plan-expression revision. C03 v8 live acceptance remains open.
This review changed only its evidence file, added no code abstraction, and
performed no implementation cleanup.
