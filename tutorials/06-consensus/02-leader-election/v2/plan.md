# C02 v2 实施计划：投过的票必须跨进程保存

v1 的 vote 只在内存里。b 在任期 7 投给 a，进程退出后再次启动会忘掉这张票，并可能投给 c；两个多数派相交的安全前提因此失效。现在只增加一项能力：回复投票成功前，持久化 term/vote。

1. Node 的构造参数从 `(name, now)` 改为 `(name, directory, now)`，Election 同时接收目录。两处调用一起更新；节点状态文件只保存 term/vote，重启总是 follower。写临时文件、fsync 文件、replace、fsync 目录之后才回复。保留 v1 的投票与心跳流程，并在每次更新 term/vote 后调用 persist。此模型单进程顺序处理每个节点事件，没有并发文件写者。
2. 在 `experiments.py` 加入本版日程，保留前版已成立的检查。
3. 执行 `uv run python -m labs.consensus.leader_election.experiments`。验收：先重跑 v1。再由独立子进程投票并以 71 强制退出，新进程读回 term=7/vote=b，拒绝同任期给 c 投票，也拒绝旧任期。允许重复给原候选人返回成功。它证明进程重启；断电语义仍依赖 POSIX 文件系统的 fsync 契约。下一版保护实际写入口。

文件与完整代码见 [正文](tutorial.md)。范围为一个模型变化和一个可直接运行的检查组；不需要参考分支。
