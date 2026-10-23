# C01: CAP, quorum, and indistinguishable failure

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

This tutorial models a two-site partition without implementing Raft or automatic leader election.

- v0 shows that a timeout cannot tell whether a remote operation failed or completed.
- v1 uses a lost acknowledgment trace to explain the Two Generals boundary.
- v2 makes the CAP choice explicit: reject requests for linearizable safety or serve an old read for availability.
- v3 computes read/write quorum intersections and demonstrates why arithmetic alone does not prove linearizability.

The model names safety and liveness separately. A partition is a communication failure, not proof that the remote node is dead.
