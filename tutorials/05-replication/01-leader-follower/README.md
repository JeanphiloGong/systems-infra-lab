# R01: Leader-follower replication

This tutorial uses a deterministic local model of a leader, an append-only log, and a follower. It teaches replication positions and read contracts without pretending to implement PostgreSQL streaming replication.

- v0 applies ordered log entries and preserves progress across restart.
- v1 delays follower application to expose stale reads.
- v2 returns a write position as a read-after-write barrier, with wait, timeout, and leader-read choices.
- v3 compares asynchronous acknowledgment with follower acknowledgment and shows the different failure-loss boundaries.
- v4 interrupts catch-up, resumes from the applied position, and safely accepts duplicate delivery.

Each version has one complete checkpoint fence. The replay tests extract and execute that fence in isolation.

