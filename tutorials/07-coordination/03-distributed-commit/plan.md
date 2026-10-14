# D03 implementation and teaching plan

Prerequisites: T04 transaction failure/retry, C01 partition ambiguity, S03 durable logs. Scenario: two independently committed account resources must agree on one transfer. Real PostgreSQL is required for v0-v2; v3-v4 are explicitly labeled state-machine experiments.

1. v0, small: commit debit and fail credit in separate databases. Target v0.py plus pg.py; verify [70,100], total 170, and temporary-database cleanup. Teach why two local transactions do not compose into atomic commit.
2. v1, medium, depends on v0: preflight max_prepared_transactions, prepare each update, inspect visibility and prepared rows, commit both. Target v1.py; verify two prepared transactions and [100,100] before [70,130]. Keep failure recovery out until v2.
3. v2, large, depends on v1: write an immutable durable decision before phase-two messages; exit a real worker after prepare or partial decision delivery. Target v2.py; verify locked rows, in-doubt blocking, commit/abort recovery, repeated recovery and refusal to reverse decisions. Explain retained membership in the supervisor and process-versus-host durability scope.
4. v3, medium, depends on v2's blocking observation: model READY/PRECOMMIT/COMMITTED transitions and count command/reply messages. Target v3.py; verify legal history, refusal to skip phases and 12-versus-8 message cost under stated counting rules.
5. v4, medium, depends on v3: partition between participants after asymmetric precommit delivery. Target v4.py plus printed v3.py dependency; verify an intentionally unsafe timeout rule gives commit/abort disagreement and explain why blocking remains necessary under unknown delay.

Every version tutorial is its own document target and includes complete source dependencies, runnable commands, observed result, scope and next limitation. tests/coordination/commit/test_d03_replay.py extracts and checks semantic outcomes in subprocesses with isolated import paths. No checkpoint commits are requested. Independent review must inspect real-PG requirements, recovery authorization, cleanup scope and the distinction between 3PC models and complete protocols.
