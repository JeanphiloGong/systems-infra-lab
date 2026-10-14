# T04 v2-v3 review against original roadmap

## Findings

No remaining required fixes in the reviewed v2/v3 revision. Earlier acceptance
of no-contention examples did not prove the roadmap's retry/load requirements;
this review supersedes that narrower acceptance.

## Original requirements and evidence

- v2 must retry an actual serialization failure, reread, and reevaluate the
  business condition. The first-attempt Barrier forces both transactions to
  read two doctors before updating. A real PostgreSQL serialization failure
  is caught outside the transaction context; only the first attempt waits at
  the Barrier. The retried transaction returns a refusal, preserving one
  doctor. Tests assert at least one retry and refusal on any retried operation,
  then inspect the committed database count.
- v2 retry exhaustion must propagate. A separate actual conflict with
  max_retries=0 produces one propagated SerializationFailure and leaves one
  doctor. This establishes the bound without fabricated exceptions.
- v3 must impose contention and report throughput, failures, and retries.
  Each round calls the same real concurrent-retry path. The CLI reports 20
  operations/commits, 10 allowed, 10 refused, at least 10 aborted/retried
  attempts, remaining=1, elapsed time, and throughput. It states that resets,
  thread creation, and retry overhead are included.
- Strict serializability is distinguished by real-time order of nonoverlapping
  operations. The guide does not claim the experiment proves that property.

## Independent replay

Inspected `tests/transactions/serializable/test_t04_replay.py`: it extracts the
actual printed Python and SQL, creates a temporary package, removes PYTHONPATH,
uses Python `-I`, executes v1 default/v2 --retry/v3 --metrics, parses the
outputs structurally, and asserts behavioral counters. It does not import
the evolving source implementation. It also enforces that retry appears at
v2 and metrics only at v3.

Executed with isolated PostgreSQL:

```text
uv run pytest tests/transactions/serializable -q
6 passed in 1.71s
```

This includes the three independent printed-code replays and actual conflict,
fresh reread, final-state, workload, and retry-exhaustion checks.

## Exact accepted hashes

```text
v2 d63c10424ca1f98d2f44c97b7ec8e79d528f3ac8616d87e6f48498030a03e32c
v3 4a16023844ca443dfafecb64128ec2c071d9edeb2b9702e3e3179558661b2a9a
```

Verdict: pass for original T04 v2/v3 roadmap scope. No source, test, or tutorial
edits performed by the reviewer.
