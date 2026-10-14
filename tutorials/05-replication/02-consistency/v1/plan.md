# R02 v1：会话读自己的写入写作计划

## 场景与契约

同一用户需要看到刚写的 Ada，其他用户仍可能读旧副本。 读者需掌握 Python 与 R01 的复制进度。先重放 [v0](../v0/tutorial.md)，再扩展本篇行为。 模型只保留主副本字典、版本、调用顺序和读取结果；不变量是每个返回值对应已声明的读取条件。

## 有序写作任务

1. **Pressure:** 同一用户需要看到刚写的 Ada，其他用户仍可能读旧副本。
   **Naive:** v0 所有读都直接读副本。
   **Break:** 副本未应用时普通 read_replica 为 None，不能满足写入会话。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** write 返回单调版本；Session.written_version 保存门槛，read_your_writes 在副本缺失或落后时读主。
   依赖任务 1；目标为 `labs/replication/consistency/v1.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** session.read 返回 (1,'Ada')，同时普通副本读取仍为 None；入口输出 (1,'Ada') None。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v1.py 的完整 checkpoint 围栏与可执行入口。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 固定主节点可达的单进程模型；没有会话迁移、主故障或网络分区策略。
   **Next:** v2 把所有读放到固定写者并记录历史。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/consistency/test_replay_r02.py::test_exact_checkpoint_executes[1]' -q
uv run pytest 'tests/replication/consistency/test_r02.py::test_v1_session_reads_own_write_but_other_replica_read_is_old' -q
```

提取测试在临时文件运行正文，但只断言退出码；第二条针对实现核对具体行为。二者不能合称为已在提取代码中验证全部语义。正文与实现仍需人工对照。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
