# R02 v3：只修复本次读到的键写作计划

## 场景与契约

一个副本的 name 与 city 都过期，但这次只读取 name。 读者需掌握 Python 与 R01 的复制进度。先重放 [v2](../v2/tutorial.md)，再扩展本篇行为。 模型只保留主副本字典、版本、调用顺序和读取结果；不变量是每个返回值对应已声明的读取条件。

## 有序写作任务

1. **Pressure:** 一个副本的 name 与 city 都过期，但这次只读取 name。
   **Naive:** 返回主节点新值却保留被读取副本的旧值。
   **Break:** 副本 name=(1,'A.')，主节点为 (2,'Ada')；忽略修复会重复遇到旧值。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** read_with_repair 比较指定副本/键版本，缺失或落后才把主值写回该副本。
   依赖任务 1；目标为 `labs/replication/consistency/v3.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** 返回并保存 (2,'Ada')，city 仍是 (1,'London')；入口打印 name 返回值与修复后值。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v3.py 的完整 checkpoint 围栏与可执行入口。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 调用者必须提供单写者有序版本，write 不强制版本递增；未读键不会因此收敛。
   **Next:** v4 在同一入口比较几类读契约与分区边界。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/consistency/test_replay_r02.py::test_exact_checkpoint_executes[3]' -q
uv run pytest 'tests/replication/consistency/test_r02.py::test_v3_repairs_only_the_replica_key_that_was_read' -q
```

提取测试在临时文件运行正文，但只断言退出码；第二条针对实现核对具体行为。二者不能合称为已在提取代码中验证全部语义。正文与实现仍需人工对照。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
