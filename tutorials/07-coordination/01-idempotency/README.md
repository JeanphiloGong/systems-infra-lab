# D01: idempotency and the exactly-once boundary

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

This tutorial follows an order request whose response can be lost after the server acts.

- v0 reproduces duplicate orders.
- v1 adds a request key and serialized deduplication.
- v2 stores the business record and deduplication result in one modeled transaction.
- v3 binds a key to a payload fingerprint, exposes processing state, replays completed responses, and expires records.
- v4 adds an external mail receiver to show the scope of local exactly-once behavior.

Exactly-once is scoped to a durable key, payload, effect store, and retention window. It never means the network delivers a request only once.
