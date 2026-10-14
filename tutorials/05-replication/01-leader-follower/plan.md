# R01 tutorial plan

Scenario: an order is written to the leader and then read through a replica. The invariant is that a follower applies accepted log positions in order, and every read states which applied position it relies on.

1. v0: ordered entries and restartable applied position.
2. v1: delayed application and reproducible stale reads.
3. v2: write position barriers with bounded waiting, timeout, or leader reads.
4. v3: asynchronous versus follower acknowledgment, including data that can be lost after leader failure.
5. v4: interrupted catch-up, duplicate delivery, and resume without a gap.

This is an in-memory teaching protocol. It does not provide leader election, automatic failover, PostgreSQL WAL shipping, or a durability guarantee beyond the modeled state.

