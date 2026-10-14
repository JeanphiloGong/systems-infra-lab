# Wave-20 teaching-depth author evidence

## Scope

Repaired the teaching prose in these 11 existing tutorial bodies only:

- `tutorials/07-coordination/02-distributed-lock/v0-v4/tutorial.md`
- `tutorials/07-coordination/04-saga/v0-v4/tutorial.md`
- `tutorials/02-transactions-isolation/04-serializability/v0/tutorial.md`

The printed Python checkpoints were preserved byte-for-byte. No implementation,
plan, progress, index, or navigation file was changed.

## Teaching changes

D02 now gives a concrete two-worker order-claim scenario, explains the atomic
winner, lease overlap, fencing token, ownership-bound renewal, and the unknown
state on service failure. Each version names the runnable command, expected
observation, and the boundary that the next version addresses. It explicitly
notes that v3's checkpoint implements renewal, not release.

D04 now compresses the Saga into observable service sets and persisted step
state. The prose walks from partial effects to restart-safe state, reverse
compensation, retry/manual state, and per-order effect keys. It distinguishes
coordinator state from external effects and records crash windows where
exactly-once is not established.

T04 v0 now states the doctor on-call rule, enumerates the two serial outcomes,
shows a runnable reference check, and explains why concurrent reads can break
the reference without claiming a database isolation result.

## Verification

- D02 replay: `uv run python tests/coordination/locks/replay_d02.py` -> v0-v4
  replay ok.
- D04: `uv run pytest tests/coordination/saga/test_d04.py tests/coordination/saga/test_replay_d04.py -q` -> 10 passed.
- Fence hashes before and after edits were unchanged for all 11 documents.
- T04 replay command was run: `uv run pytest tests/transactions/serializable/test_t04_replay.py -q` -> 3 failures before execution because the required `SYSTEMS_LAB_DATABASE_URL` environment variable was unset. This is an external PostgreSQL dependency, not a tutorial-fence failure.

No new abstraction was added. Cleanup was limited to replacing thin prose with
scenario-driven explanation, checks, and explicit limitations; existing code
and version scope remain unchanged.
