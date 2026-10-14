# T01 author verification

Scope: v0-v4 tutorials, plans, current source and tests. Independent review tracked separately under reviews; this file does not approve its own tutorials.

Environment: PostgreSQL 16.14 on repository disposable Compose database, Python 3.14.0 from uv, dependencies in root uv.lock. SYSTEMS_LAB_DATABASE_URL points to localhost:55432/systems_lab. Tests create random t01_ schemas and remove only their own resources.

## Increment evidence

- v0 RED: test_t01_transfer.py failed collection because labs module absent. After implementation: 10 passed in 0.84s. Includes success, injected failure, missing destination/source, same account, zero/negative/bool amount, insufficient and exact balance.
- v1 RED: observations module absent; GREEN 2 passed in 0.28s, real RC and RU both (70,100,100).
- v2 RED: read_skew import absent; GREEN 4 passed in 0.42s including v1; RC (100,130,200), RR (100,100,200).
- v3 RED: phantom_read import absent; GREEN 6 passed in 0.54s including prior observations; RC (2,3,3), RR (2,2,3).
- v4 RED: acid module absent; GREEN 1 passed in 0.24s; constraint rejection preserves 200, legal single debit gives 199, committed transfer visible after writer connection closes.

Commands used at each stage: `uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -q`, `.../test_t01_observations.py -q`, `.../test_t01_acid.py -q`, with SYSTEMS_LAB_DATABASE_URL set to the disposable instance.

## Isolated frozen checkpoint replay

`SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab' uv run python -m pytest tests/transactions/isolation -q`

Result: **22 passed in 9.56s**. Five parametrized replay cases extract the actual Markdown SQL and complete code blocks into pytest temporary directories; subprocess cwd and PYTHONPATH point there, not current labs. Each runs success/failure transfer; v1 runs both dirty-read levels; v2 additionally both read-skew levels; v3 additionally both phantom levels; v4 runs constraint/reconnect output. Actual expected tuples and exit status are asserted. No sleep-based interleaving, no mocked isolation.

v0 independently reviewed PASS by reviewer, evidence reviews/t01-v0.md. v1/v2 reviewer requested assertions for invalid-level rejection without mutation and committed final 70/130 balances independent of old RR snapshot. Added these checks (plus invalid phantom level); focused observations suite: **9 passed in 0.72s**. Independent reviewer then accepted v1-v4 after 25-test run and intermediate-patch replay, evidence reviews/t01-v1-v4.md. T01 v0-v4 accepted; no runtime changes after review.

Additional v0 connection-failure contract check binds a local socket without listening and passes that port only to a subprocess. `uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -k connection_failure -q`: **1 passed, 10 deselected in 0.48s**; nonzero exit, no success output, OperationalError. The reserved port cannot accidentally select another running database. Total current T01 test cases: 26 (22 initial + 3 invalid-level + 1 connection-failure).

Limitations: no PostgreSQL crash/restart, power loss, external side effects, concurrency retries or serializability claim. Reading after reconnection is explicitly not a durability proof. Observations assume fresh initialized data and idle autocommit connections supplied by experiment CLI. Input transfer validation is intentionally limited to documented integer-ID and amount contract.

Helpers added: transfer business operation, observation functions, constraint experiment and direct CLI main functions; pytest setup/replay utilities only. No adapter, repository or runtime framework added. Temporary learner patch commands are reverted in final checkpoints; no duplicate historical source directories retained. No Git commits created.
