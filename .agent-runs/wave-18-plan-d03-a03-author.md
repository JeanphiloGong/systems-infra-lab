# D03/A03 version-plan revision evidence

Rewrote the D03 distributed-commit v0-v4 and A03 failover v0-v4 plans with
real scenarios, prior baselines, deterministic failure pressure, one mechanism
change, exact checks, freeze artifacts, limitations, next pressure, and
version-specific replay commands.

Verification:

```text
$ uv run pytest tests/coordination/commit -q
2 passed, 7 failed (D03 PostgreSQL service/D03_DATABASE_URL unavailable)
$ uv run pytest tests/recovery/ha/test_a03.py -q
5 passed
$ uv run pytest tests/recovery/ha/test_patroni_probe.py -q
1 skipped (Docker/Patroni unavailable)
```

D03's live checks require the disposable PostgreSQL service configured by
`D03_DATABASE_URL`; only its non-database checks passed here. A03 model tests
passed, while the Patroni probe remains skipped without its Docker lab. No
code, tutorial body, docs/progress, or index files were changed.
