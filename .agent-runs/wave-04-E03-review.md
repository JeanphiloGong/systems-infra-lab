# E03 independent review: revise

The five isolated fence replays pass, but two semantic gaps remain against the
original E03 scope.

## Blocking findings

1. v2 calls `append` twice on one `EventStore` in one process. The second stale
   expected version is useful, but it is not a concurrent-writer experiment.
   Use two file-backed SQLite connections (or child processes) that both read
   expected version 1, then append; one must commit and the other must receive
   `Conflict` after the database lock/transaction boundary. Preserve the event
   sequence and prove the losing writer did not overwrite it.

2. v3 accepts out-of-order projection delivery and regresses state. Independent
   probe:

   ```text
   apply(version=3, OrderShipped) -> ('shipped', 3)
   apply(version=2, OrderPaid)    -> ('paid', 2)
   ```

   A stream position must not move backwards. Add an explicit contiguous-version
   check (or a documented pending buffer with a bounded contract), test duplicate
   and stale delivery, and keep rebuild applying the ordered event stream.

The current 5-test green result and exact fence extraction are useful but do not
cover these invariants. No progress acceptance or commit performed.
