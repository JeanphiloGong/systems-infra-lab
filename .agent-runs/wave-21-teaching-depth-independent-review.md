# Wave-21 independent teaching-depth review

## D02 distributed lock

**PASS.** The revised v0-v4 prose gives a concrete two-worker resource-claim
scenario and explains the specific pressure introduced at each checkpoint:
winner selection, lease overlap, fencing tokens, owner-bound renewal, and
unknown availability after a service failure. It correctly calls out that v3's
fence implements acquire/renew rather than release, and does not imply
concurrency atomicity, persistence, or TTL validation that the code lacks.

`uv run python tests/coordination/locks/replay_d02.py` independently passed all
five extracted checkpoints. The replay outputs match the prose, including
winner `b`, overlap risk, stale-token rejection, and the final `unknown /
do-not-write` safety action. The v0-v4 checkpoint fences remain executable;
the replay itself is the appropriate verification for D02's standalone
`checkpoint.py` fences.

## D04 Saga

**PASS.** The revised v0-v4 prose follows the observable Saga chain: partial
independent effects, durable step state, reverse compensation, bounded retry
to `manual`, and per-order/per-operation effect keys. It distinguishes
coordinator state from remote effects and explicitly names crash windows,
timeouts after an external effect, and the resulting idempotency boundary.
Those limits are consistent with the local SQLite implementation.

`uv run pytest tests/coordination/saga/test_d04.py tests/coordination/saga/test_replay_d04.py -q`
passed: **10 passed**. An independent fence/source comparison found all five
D04 tutorial Python checkpoints byte-equivalent to their `labs/coordination/saga`
sources. The tests and replay confirm the revised explanations without
requiring an external service.

## T04 serializability v0

**PASS with runtime limitation.** The revised v0 prose is specific about the
doctor on-call rule, initial `(True, True)` state, the two serial outcomes,
and why `(False, False)` is a concurrent anomaly rather than a serial result.
The Python reference assertion and command are runnable without PostgreSQL;
the prose correctly avoids claiming that this reference proves any database
isolation level and hands the database experiment to the next version.

The requested replay command was run:

```text
uv run pytest tests/transactions/serializable/test_t04_replay.py -q
3 failed before database execution: SYSTEMS_LAB_DATABASE_URL was unset
```

The failures occur when v1-v3 checkpoints read the required PostgreSQL DSN;
they do not indicate a v0 fence or prose error. T04 v0 itself is a local
Python checkpoint and is independent of that missing external service. No
database was started for this documentation review.

## Fence-hash and scope evidence

The author reports before/after SHA-256 fence hashes unchanged for all 11
documents. Independently, D04 fence extraction/source comparison passed for
all five code fences, while D02's five standalone fences passed its dedicated
replay. The edits are prose-only: no implementation, plan, progress, index,
or navigation file was changed, and no new abstraction was introduced.

## Verdict

| Module | Verdict |
| --- | --- |
| D02 | PASS |
| D04 | PASS |
| T04 v0 | PASS with external PostgreSQL limitation for v1-v3 replay |

The teaching revisions add concrete explanation without introducing a factual
claim that conflicts with the checked code or tests.
