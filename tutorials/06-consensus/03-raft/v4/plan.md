# C03 v4 实施计划：拒绝日志落后的候选人

v3 的多数提交还不够：a/b 已提交的记录可能没有到 c。若只按 term/vote 选举，空日志的 c 仍能当选，接下来会碰到 committed prefix conflict。本版增加 RequestVote 的日志新旧比较，使这个候选人拿不到多数票。

依赖：v3 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：campaign 在投票请求中增加 last/last_term；receive 先比较 (last_term,last)，通过后才执行原先的一任期一票规则。比较是字典序，最后一条的任期优先于长度。term 高只说明选举较新，不说明日志更新。其余复制、commit 和磁盘格式保持 v3 的规则。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：c 错过已提交记录后竞选，只得到自己的票；拥有该记录的 b 可以赢得下一任期并继续提交，最终三节点都保留 mode=committed 与 next=kept。这也检查 v3 规则在合法换主后继续成立。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
