# Wave-19 E01/A02 author evidence

Scope: nine version plans only, under `tutorials/08-dataflows/01-cdc/v0-v4`
and `tutorials/09-recovery/02-checkpoint/v0-v3`, plus this evidence file.
No implementation, tutorial body, index or progress file was changed.

Preserved concrete scenarios and added explicit Pressure, Naive/Break, Change,
Check, Freeze, Still-lacks, Next and Replay fields. Checks are grounded in the
current tutorial fences and corresponding tests. A02 distinguishes the 100+5
transaction store test from the 10+5 independent fence probe. E01 v3 preserves
the initial snapshot after a pre-commit crash and commits checkpoint with the
incremental projection before acknowledging the source slot.

Validation actually run:

- Field audit over all nine plans: passed, all nine required labels present.
- `uv run pytest tests/recovery/checkpoint -q`: 16 passed in 9.36s.
- `uv run python tests/recovery/checkpoint/replay_a02.py`: passed; v1 output
  `({'alice': 85, 'bob': 115}, 15)`, v2 output
  `0 ({'alice': 95, 'bob': 105}, 5)`, v3 output
  `({'alice': 75, 'bob': 125}, 25)`.
- `uv run pytest tests/dataflows/cdc/test_e01_replay.py -q`: 7 failed,
  1 passed. The fence-list check passed. Five live replay cases failed because
  `E01_DATABASE_URL` was unset; decoder and snapshot-cut tests failed because
  the dedicated PostgreSQL endpoint at 127.0.0.1:55450 refused connections.

External boundary: live E01 replay remains unverified in this environment.
It requires `infra/e01.compose.yaml`, its dedicated DSN, logical replication
and test_decoding; this documentation-only batch did not start services.
A02 checks use local files and subprocess exits, not power-loss simulation or
replicated checkpoint storage. No new code abstraction or temporary helper was
added; cleanup consisted of replacing ambiguous combined plan labels.
