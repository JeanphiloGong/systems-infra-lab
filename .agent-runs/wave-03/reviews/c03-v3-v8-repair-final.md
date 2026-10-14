# C03 v0-v8 repair review

Verdict: PASS for the repaired original roadmap scope, with the stated deferred boundaries. This supersedes `c03-v3-v8-revise.md`; v0-v2 continuity and v3-v8 were independently replayed. No blocking findings.

## Actual verification

Ran `uv run pytest tests/consensus -q`: **31 passed in 5.00s**.

Ran each isolated replay version from the extracted tutorial files:

- v0, v2, v3, v4, v5, v6 and v7 all passed with the expected concrete JSON results.
- v1 passed with simultaneous candidates, elected term2, durable restart vote and exit74.
- With `ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd`, v8 passed: **three real etcd 3.5.17 processes**, elected leader kill, majority write/recovery, old-leader catch-up and minority write rejection.

The full `replay_c03.py` command was also inspected: it extracts each version's marked files into a fresh temporary package and runs a fresh interpreter with only that package on PYTHONPATH. For v8 it additionally checks source equality for all three current-worktree fences. v0-v7 are intentionally version-specific snapshots rather than byte-identical copies of the final current modules; their extracted outputs are asserted semantically. The v0/v1 boundary checks prevent future persistence/AppendEntries helpers from leaking into those early checkpoints.

## Roadmap evidence

- v1 now runs a deterministic logical-clock election with three simultaneous candidates, then a staggered election, and performs a real child process vote/restart trajectory. Persisted term/vote survives exits at the documented boundaries.
- v3 uses actual fixed-member follower ACK messages, validates membership/request identity, requires a majority, and refuses to commit an old-term entry directly. A current-term entry commits and carries the earlier entry; durable lengths are checked.
- v4 wires log freshness into the same candidate/vote model. A stale candidate receives only its self vote while an eligible successor wins and preserves the prior committed state.
- v5 executes 12 child processes covering vote/append/commit/snapshot actions at before-replace, after-replace and after-directory-fsync boundaries. Fresh-process recovery checks term/log/commit/snapshot effects for each exit result.
- v6 creates deterministic message schedules with dropped, duplicated and reversed deliveries plus a partition. After majority recovery all nodes converge to commit2 and the expected state.
- v7 compacts only committed prefixes while retaining absolute base index/term. A lagging node receives/install a snapshot, appends index3 after base2 and converges to state `x=3`; replay asserts base2/last3/commit3.
- v8 runs the real etcd process demonstration described in the original roadmap boundary: three members, leader kill, surviving majority write, restarted member catch-up and minority rejection.

## Remaining limits

The teaching cluster is fixed-membership, trusted and sequentially scheduled; dynamic/joint membership, linearizable read protocols, authentication, production operations and a proof of Raft safety remain out of scope as the roadmap says. The etcd demonstration is a real local process test, not independent-host or production-failure evidence. Those limitations do not narrow the v0-v8 requirements that were claimed here.

Review artifact only; no implementation abstraction or source cleanup added.
