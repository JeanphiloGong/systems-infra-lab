# C03 v0 实施计划：日志追加与状态机提交分开

客户端设置 mode=safe，节点收到了命令，但还没决定它是否生效。如果 append 直接改 state，未提交内容会暴露给调用者。先压缩成一个节点、一条有序日志和一个字典状态机，不引入网络或选举。

依赖：Python 3.12；空练习目录。

1. 在 `labs/consensus/raft/model.py` 实施：`log` 按追加顺序保存命令，`commit` 表示已应用的连续前缀长度；`state` 只由 `apply` 更新。重复 apply 同一位置不重复应用，越过日志末尾被拒绝。append 返回的位置从 1 开始，与 Python 列表下标相差 1。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：追加后 state={}、commit=0；apply(1) 后 mode=safe，重复应用不变，apply(2) 拒绝。此检查点尚无持久化，下一版加入选举。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
