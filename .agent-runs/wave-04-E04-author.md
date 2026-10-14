# E04 author evidence

Status: revised with a real PostgreSQL FDW experiment.

The v0-v3 tutorials now fence the complete runnable files in
`labs/dataflows/analytics/`. Each fence is extracted into a fresh temporary
directory and executed by `tests/dataflows/analytics/test_e04_replay.py`.

```text
$ uv run pytest tests/dataflows/analytics -q
....                                                                     [100%]
4 passed in 1.06s
```

Observed checkpoints:

```text
v0: two source batches (orders-1, customers-1), 2 order rows, 2 customer rows,
    joined sales [(1, A, 30), (2, B, 20)], watermarks orders=2/customers=1
v1: repeated batch remains 55; late order correction changes 50 -> 55;
    corrected row lineage is batch-2
v2: fixed connector exposes independent customers/orders sources; each source
    has 100 rows, indexed predicates transfer 3 rows, and both plans report USING INDEX
v3: copied total is 30 while independently evolved sources produce federated total 60;
    customer source outage raises "source unavailable: customers" and copied data remains readable
```

The revised experiment uses three independent PostgreSQL 16.14 processes and
`postgres_fdw` 1.1. v2 observed 200 rows transferred for unrestricted reads and
6 rows transferred for the selective two-source join; each source still scanned
100 rows. v3 observed an orphan order between independent source commits,
SQLSTATE `08001` after stopping the customer source, unchanged foreign-server
configuration, copied warehouse availability, and convergence after catch-up.

The experiment does not claim enterprise scheduling, cross-source transactions,
or a global consistent snapshot.
