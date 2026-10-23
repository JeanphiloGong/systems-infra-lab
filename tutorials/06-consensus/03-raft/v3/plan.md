# C03 v3 实施计划：由多数持久确认推进 commit

v2 能复制并修复日志，却还靠实验直接指定 commit。本版把提交决定接到真实确认消息：只有多数节点已持久保存同一位置，且该位置来自 leader 当前任期，才推进 commit 并通知 follower。

依赖：v2 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：只在 ack 成功分支增加提交规则。match 存每个成员已确认的最大位置，leader 自己落盘后也算一份；取满足多数且 term_at(index)==当前任期的位置。apply 保存 commit 再更新状态机，随后 broadcast 让 follower 应用同一前缀。旧任期条目不能单独靠本轮多数计数提交；当前任期新条目提交后会一起提交前面的连续前缀。选举尚未检查候选日志，v4 前不能称作完整 Raft 安全实现。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：隔离 leader 后追加旧任期记录，commit 保持 0；恢复并提高任期使三份磁盘日志相同，也仍不提交旧条目。追加当前任期记录后三个节点 commit=2，mode=current-term。未知 peer 的 ack 被拒绝。v4 再保护换主时的日志完整性。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
