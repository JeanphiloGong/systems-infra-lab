# R01: Leader-follower replication

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

This tutorial uses a deterministic local model of a leader, an append-only log, and a follower. It teaches replication positions and read contracts without pretending to implement PostgreSQL streaming replication.

- v0 applies ordered log entries and preserves progress across restart.
- v1 delays follower application to expose stale reads.
- v2 returns a write position as a read-after-write barrier, with wait, timeout, and leader-read choices.
- v3 compares asynchronous acknowledgment with follower acknowledgment and shows the different failure-loss boundaries.
- v4 interrupts catch-up, resumes from the applied position, and safely accepts duplicate delivery.

Each version has one complete checkpoint fence. The replay tests extract and execute that fence in isolation.
