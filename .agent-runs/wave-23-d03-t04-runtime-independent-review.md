# Wave-23 independent runtime review: D03/T04

## Independent execution

D03 was rerun against the already-running disposable container
`systems-d03-postgres` on `127.0.0.1:55434`:

```text
D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03' \
  uv run pytest tests/coordination/commit -q
.........                                                                [100%]
9 passed in 8.41s
```

This covers the D03 replay suite's PostgreSQL transfer, commit/abort,
recovery, phase, partition-counterexample, durable-decision, and prepared
cleanup checks. A direct query after the run reported zero `d03_%` prepared
transactions. The container predated this wave, so it was not stopped or
removed by this review.

For T04 I started a review-owned, no-volume container from the pinned
PostgreSQL 16 image on `127.0.0.1:55436`, waited for `pg_isready`, and ran:

```text
SYSTEMS_LAB_DATABASE_URL='postgresql://t04:t04_local_only@127.0.0.1:55436/t04' \
  uv run pytest tests/transactions/serializable -q
......                                                                   [100%]
6 passed in 1.61s
```

The suite includes v1-v3 isolated tutorial-fence replay and live
serialization abort, retry, conflict, and metrics checks. The container was
removed with `docker rm -f systems-wave23-t04-review`; no review-owned
container or volume remained afterward.

## Fence and cleanup boundary

The T04 suite extracts the tutorial fences into isolated temporary files before
running them, so its six passing tests include the documented source replay
contract. D03's nine-test replay suite likewise exercises its versioned
PostgreSQL fences and cleanup paths. No tutorial or implementation changes
were needed. The pre-existing D03 service remains an environment resource,
not a leaked resource from this review.

## Verdict

**PASS.** Both author claims were independently reproduced with the required
services. D03 and T04 runtime acceptance is supported by the outputs above;
container ownership and cleanup are explicitly distinguished.
