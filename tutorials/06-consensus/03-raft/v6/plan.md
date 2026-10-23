# C03 v6 实施计划：控制消息丢失、重复和倒序

v5 的持久化检查不覆盖迟到响应。旧 leader 被隔离后产生未提交后缀，剩下多数提交不同后缀，再恢复通信并重复、倒序、丢弃消息。目标是所有节点最后保留已提交前缀并接受新 leader 的后缀。

依赖：v5 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：核心 Node 不变。Cluster.deliver 新增 position/drop，drain 新增 reverse；原来的 term、pending 和 committed-prefix 规则要承受新日程。丢包后必须再显式 broadcast 才保证有新尝试；模型不承诺无限丢包下仍可用。故障 trace 记录每条投递是否被丢弃，计数来自实际队列。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：先提交 stable=yes，隔离 a 后它的 orphan 不能提交。b/c 提交 successor；网络恢复后即使消息重复/倒序/丢失，最终三节点 commit=2、stable=yes、mode=successor，a 已退位。输出的 dropped 是真实故障数量。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
