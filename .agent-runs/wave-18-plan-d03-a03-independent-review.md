# Wave-18 independent review: D03/A03

## Scope

Reviewed the revised plans:

- D03 distributed commit, `tutorials/01-coordination/03-commit/v0-v4/plan.md`
- A03 high availability/failover, `tutorials/03-recovery/03-ha/v0-v4/plan.md`

## Plan fidelity

**PASS.** D03 v0-v4 forms a clear chain from partial local commit divergence,
through prepare-before-decide and durable coordinator recovery, to a visible
precommit phase and a timeout counterexample to consensus. A03 v0-v4 forms a
clear chain from RTO/RPO modeling, through human promotion and stale clients,
to Patroni failover, isolated-old-primary fencing, rebuild/catch-up, and
planned switchover. Each version states pressure, naive break, one mechanism,
observable checks, frozen source, limits, next pressure, and replay command.

## Independent runtime evidence

```text
$ uv run pytest tests/coordination/commit -q
2 passed, 7 failed

$ uv run pytest tests/recovery/ha/test_a03.py -q
5 passed

$ uv run pytest tests/recovery/ha/test_patroni_probe.py -q
1 skipped
```

The D03 failures require the disposable PostgreSQL service configured by
`D03_DATABASE_URL`; that service was unavailable, so the database-backed
behavior is unverified here. The two non-database checks passed. A03's model
tests passed. Its Patroni probe was skipped because Docker/Patroni was
unavailable, so live failover behavior is unverified in this environment.

## Verdict

**PASS with environment limitations.** The plans are faithful and complete as
learning contracts. Runtime evidence supports the model-level behavior, but
the D03 PostgreSQL path and A03 Patroni path require their dedicated external
services before those live claims can be accepted. No implementation, tutorial
body, index, or progress file was changed by this review.
