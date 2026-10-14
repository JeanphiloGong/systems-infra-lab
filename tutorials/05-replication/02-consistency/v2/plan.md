# R02 v2：固定写者与历史检查写作计划

## 场景与契约

已完成 name=Ada 写入之后的读取不能返回之前的值。 读者需掌握 Python 与 R01 的复制进度。先重放 [v1](../v1/tutorial.md)，再扩展本篇行为。 模型只保留主副本字典、版本、调用顺序和读取结果；不变量是每个返回值对应已声明的读取条件。

## 有序写作任务

1. **Pressure:** 已完成 name=Ada 写入之后的读取不能返回之前的值。
   **Naive:** 把各自可读的副本称为统一实时状态。
   **Break:** v0 的写后 None 不符合完成写入先于读取的约束。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** LinearizableStore 直接读 data；write/read 追加 operation/version/value，check_history 检查写版本递增及读版本不落后。
   依赖任务 1；目标为 `labs/replication/consistency/v2.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** 入口输出 Ada True；test_single_writer_history 验证读取 Ada 和 check_history 为 True。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v2.py 的完整 checkpoint 围栏与可执行入口。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** check_history 只在固定单写者的小历史上检查 key、value、version 和调用/返回区间；它不是通用线性一致性判定器，也不模拟真实并发调度。
   **Next:** v3 回到允许旧副本的系统，检查读取时修复的效果。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/consistency/test_replay_r02.py::test_exact_checkpoint_executes[2]' -q
uv run pytest 'tests/replication/consistency/test_r02.py::test_v2_single_writer_history_is_checkable' -q
```

提取测试在临时文件运行正文，但只断言退出码；第二条针对实现核对具体行为。二者不能合称为已在提取代码中验证全部语义。正文与实现仍需人工对照。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
