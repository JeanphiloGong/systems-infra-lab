# F01-F04 Plan Batch Independent Review: REVISE

Repository: `/home/gong/date/2026/oct/systems-infra-lab`  
Date: 2026-10-14

## Replay evidence

The author-listed commands were independently run:

```text
$ uv run python tests/traffic/admission/replay_f02.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok
v4 replay ok

$ uv run pytest tests/traffic/retry/test_replay_f03.py -q
12 passed in 0.65s

$ uv run pytest tests/traffic/herd/test_f04.py -q
4 passed in 0.76s

$ uv run pytest tests/traffic/connections/test_f01_pool.py -q
6 skipped in 0.16s
```

The F01 result is a skip, not a pass. The six integration tests require
`SYSTEMS_LAB_DATABASE_URL`; the PgBouncer-specific v3 path additionally
requires `SYSTEMS_LAB_POOL_URL` and the Compose service. No PostgreSQL or
PgBouncer run was claimed from this environment.

## Plan and source consistency

### F01: REVISE

The four revised plans are scenario-specific and include pressure, one
mechanism change, checks, limits, and replay commands. However, the current
tutorial fences are not linked to repository source paths:

- v0 marks `direct.py`, but there is no repository `direct.py` at that path;
- v1 marks `pool.py`, but there is no repository `pool.py` at that path;
- v2 marks `pool_cleanup.py`, but no such lab file exists;
- v3 marks `proxy.py` and `session_boundary.py`, but neither marker resolves to
  a repository file.

The actual files under `labs/traffic/connections/` are `direct.py`, `pool.py`,
and `proxy.py`, while `session_boundary.py` and `pool_cleanup.py` are absent.
Thus the plans describe runnable tutorial fences, but the current
tutorial/lab boundary cannot provide exact implementation parity or a
repository replay target. The skipped database tests also leave the real
connection behavior unverified.

### F02: REVISE

The five plans now describe distinct admission pressures and checks, and the
isolated replay passes all five fences. The source audit nevertheless found
that the fences are not synchronized with the lab files:

```text
v0 unbounded.py       exists, fence != labs/traffic/admission/unbounded.py
v1 bounded.py         exists, fence != labs/traffic/admission/bounded.py
v2 token_bucket.py    exists, fence != labs/traffic/admission/token_bucket.py
v3 balancer.py        exists, fence != labs/traffic/admission/balancer.py
v4 backpressure.py    missing from labs/traffic/admission/
```

The replay proves each plan's embedded fence runs in isolation, but not that
the current lab implementation delivers the plan's checkpoint. The v4 plan
cannot point to a current implementation file at all.

### F03: PASS for plan fidelity and current checkpoint boundary

The five plans are version-specific and align with the retry/breaker/budget
progression. The 12 replay tests passed, and an independent source audit
found every F03 checkpoint fence equal to its referenced file, including the
v2 I/O deadline support fence. The plan and implementation limits (local
breaker state, shared leaf budget, synchronous non-preemption) are explicit.

### F04: PASS for plan fidelity and current checkpoint boundary

The four plans identify the pressure, exact concurrency or cache observation,
one change, limits, and next pressure. The full extracted replay passed all
four versions. The tutorial dependencies and all seven referenced fences were
checked against `labs/traffic/herd/`; every fence matched its source file.

## Decision

**REVISE** for the F01-F04 batch. F03 and F04 are independently acceptable;
F01 and F02 require tutorial/lab checkpoint synchronization before their
plans can be treated as implementation-grounded. F01's PostgreSQL/PgBouncer
coverage remains an explicit environment limitation rather than a pass.

No implementation, tutorial, plan, progress, or index files were changed;
only this review artifact was added. No abstraction or cleanup was
introduced.
