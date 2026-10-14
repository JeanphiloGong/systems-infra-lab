# Q02/Q04 Plan Batch Independent Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Plan and model checks

The author-listed non-live checks passed:

```text
$ uv run pytest tests/query/indexes/test_q02_indexes.py \
    tests/query/derived/replay_q04.py -q
2 passed in 0.02s
```

The nine revised version plans were inspected. Each contains the stated
Pressure/Naive/Break/Change/Check/Freeze/Still-lacks/Next progression and
references the current tutorial commands and observations. The model-level
Q02 checks cover result preservation, composite ordering, and visibility
metrics; Q04's replay script covers all five versions.

## Q02: REVISE

The live PostgreSQL service was available at
`postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab`.
The live command produced:

```text
$ SYSTEMS_LAB_DATABASE_URL=... uv run pytest \
    tests/query/indexes/test_postgres.py -q
...F                                                                   [100%]
1 failed, 3 passed in 5.92s
```

The independent live replay passed v0-v2 and failed at v3 with the same
visibility-map assertion:

```text
AssertionError
assert measure(plans["vacuumed"])["heap_fetches"] == 0
```

The live v0-v2 observations were valid: the baseline sequential scan was
measured, the selective/common predicate plans diverged as expected, and the
`user_id,created_at` index used fewer buffer accesses than the reverse order.
Q02 v3 cannot currently claim that `VACUUM` restores an index-only scan with
zero heap fetches on the repository PostgreSQL environment. The exact
checkpoint replay therefore fails at v3 as well. The plan's v3 assertion or
experiment needs repair before Q02 is accepted; this is an implementation
behavior failure, not a PostgreSQL skip.

## Q04: PASS

The isolated PostgreSQL replay was initially run without a DSN and correctly
reported the required-DSN error; no skip was treated as a pass. With the live
DSN above, all five derived-data checkpoints passed:

```text
$ SYSTEMS_LAB_DATABASE_URL=... uv run python tests/query/derived/replay_q04.py
v0 live replay ok
v1 live replay ok
v2 live replay ok
v3 live replay ok
v4 live replay ok
```

Observed results matched the plans: repeated aggregate baseline, stale then
refreshed materialized view, ordinary versus concurrent refresh behavior and
SQLSTATEs, cache-aside TTL loads/hits, and the v4 epoch guard rejecting one
stale fill while returning the current value. The tutorial fences and
`labs/query/derived` checkpoints were executed by the replay script.

The PostgreSQL test invocation without a DSN produced `2 passed, 9 skipped`;
those nine skips are an environment limitation and are superseded for Q04 by
the independent live replay above.

## Decision

**REVISE for the Q02/Q04 batch.** Q04 is independently acceptable. Q02 v3's
live visibility-map assertion fails, so Q02 remains open until the source,
experiment, or stated contract is corrected and replayed on PostgreSQL.

No implementation, tutorial, plan, progress, or index files were changed;
only this review artifact was added. No abstraction or cleanup was
introduced.
