# Wave-21 independent review: semantic plan fixes

## Findings

No remaining issue found in the five repaired plans. Each prior finding is
closed by a concrete wording change that matches the tutorial fence and test
contract.

## Finding closure

| Plan | Closure evidence | Verdict |
| --- | --- | --- |
| D04 v1 | The plan now distinguishes the `:memory:` tutorial output from the focused file-backed close/reopen test, and explicitly keeps the effect-before-done-marker crash window. This matches `test_v1_restart_does_not_repeat_done_step`, which expects one `reserve` call after reopening. | PASS |
| D04 v2 | The plan now states caller-supplied reverse order: refund position 2, then release position 1. Its expected effects `reserved, charged, refunded, released` and idempotent repeat match the tutorial and `test_v2_reverse_compensation_is_idempotent`. | PASS |
| P03 v0 | The impossible dependency on a previous migration version is removed. The plan now names P01 routing concepts and its own complete initial `Migration`/checkpoint model, matching the standalone v0 fence. | PASS |
| P03 v2 | Pressure is limited to append-ordered duplicate/tombstone replay. The plan explicitly defers sorting, rejection, or version checking for out-of-order delivery, matching `apply_delta` and the idempotence test. | PASS |
| E03 v2 | The plan now states exactly one concurrent append succeeds and one conflicts, while either `OrderPaid` or `OrderCancelled` may win. It preserves versions `[1,2]` without submission-order claims, matching the concurrent fence and replay assertion. | PASS |

## Independent verification

```text
$ uv run pytest tests/coordination/saga/test_d04.py \
    tests/coordination/saga/test_replay_d04.py \
    tests/partitioning/migration -q
13 passed in 0.31s

$ uv run pytest tests/dataflows/events/test_e03_replay.py -q
5 passed in 0.40s
```

The targeted Saga tests cover the repaired v1 restart marker and v2 reverse
compensation behavior. The migration suite covers pause/copy and idempotent
delta replay among its five tests. E03 replay extracts each tutorial fence;
its v2 case passed with the race winner treated as nondeterministic.

## Verdict

**PASS.** All five wave-20 semantic findings are closed. The changes remain
documentation-only: no implementation, tutorial body, index, progress, or
new abstraction was added by this review.
