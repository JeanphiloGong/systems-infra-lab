# C03 v5 实施计划：在持久化边界杀死进程

v4 重新构造 Node 能读回数据，但正常退出不能暴露落盘中间窗口。本版保持协议规则不变，只在文件发布前、replace 后和目录 fsync 后注入进程退出，分别检查 vote、append、commit。

依赖：v4 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：persist 增加 fault 注入位置，默认 None；真正退出使用 os._exit，跳过 Python 清理。父进程事先保存旧状态，子进程执行一个更新，第三次构造从文件恢复。before_replace 应读旧版本；后两点在本次进程故障实验中读新版本。replace 后但目录 fsync 前不保证断电恢复，这里不能把进程退出外推成电源故障。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：本版新增九个独立子进程故障：三类更新乘三个发布点。退出码为 71/72/73，重开文件后的 term/vote/log/commit/state 必须与断言一致；所有早期检查也运行。快照尚不存在，其故障检查等 v7 再加入。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
