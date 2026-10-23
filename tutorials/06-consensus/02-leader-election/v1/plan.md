# C02 v1 实施计划：把超时改成多数派投票

v0 的三个节点都把超时当成授权。现在超时只能发起竞选：固定成员 a/b/c 中至少两票才当选。任期区分选举轮次，同一节点在同一任期只投一名候选人。多数派相交因此排除同任期两个胜者；不同任期的旧 leader 仍可能相信自己有效。

1. 保留 v0 的 `timed_out`，增加 `request_vote` 和 `campaign`。`campaign` 要求候选人提出比自己已知任期更大的编号；失败也不能在同一任期改投。`heartbeat` 更新最近联系时间，并在更高任期退位。`blocked` 只决定消息能否到达，不等于授权状态。
2. 在 `experiments.py` 加入本版日程，保留前版已成立的检查。
3. 执行 `uv run python -m labs.consensus.leader_election.experiments`。验收：断言检查 a 赢 term1、b 不能在 term1 再获胜；时间到 6 且 a 被隔离后，b/c 可以选出 term2 的 b。a 与 b 的 leader 判断同时为真是预期暴露的缺口。当前投票尚不持久；v2 修复重启遗忘。

文件与完整代码见 [正文](tutorial.md)。范围为一个模型变化和一个可直接运行的检查组；不需要参考分支。
