# C03 v1 实施计划：把任期和投票接到同一节点

v0 只回答“哪条命令已应用”。三个节点还需要决定谁接收新命令，重启后也不能在同一任期重复投票。本版增加持久任期/投票和带逻辑时钟的消息队列；日志与 commit 仍属于同一 Node，尚不复制。

依赖：v0 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：构造从 Node(name) 改为 Node(name, members, directory)，实验调用一并更新；新增条目携带 term，原 key/value 不变。持久文件保存 term、vote、log、commit；role 和收到的票是易失状态，重启回 follower。写临时文件、fsync、原子 replace、fsync 目录之后才答复。Cluster 排队交付 vote/voted，deadline 使用错开的逻辑时刻；同刻竞选会平票，下一轮错开可收敛。本版尚无心跳，不能长时间维持 leader。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：保留本地状态机检查，再让三个节点同刻竞选而平票；错开下一次期限后 a 在 term2 当选。b 进程退出后仍保存投给 a 的票，拒绝同任期给 c 投票。下一版把日志加入消息路径。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
