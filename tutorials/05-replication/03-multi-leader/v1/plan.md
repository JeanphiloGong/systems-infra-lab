# R03 v1：分区时的双主冲突写作计划

## 场景与契约

A/B 在失联时分别修改同一展示名称，双方都需本地成功。 读者需掌握 Python 与 R01/R02/C01 的复制、读取契约与分区。先重放 [v0](../v0/tutorial.md)，再扩展本篇行为。 模型只保留A/B 两地区、逻辑事件、版本元数据和确认轨迹；不变量是确认、冲突和收敛各自可追溯，合并丢失不得称为无损同步。

## 有序写作任务

1. **Pressure:** A/B 在失联时分别修改同一展示名称，双方都需本地成功。
   **Naive:** 仍把一方副本当作不可写，或传播时静默覆盖另一方名称。
   **Break:** 分区中双方本地确认各 2ms；同步后不能无条件只保留一个候选。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** 使用向量版本与 dominates；merge 移除因果过期候选，保留并发候选。
   依赖任务 1；目标为 `labs/replication/multi_leader/v0.py`、`labs/replication/multi_leader/v1.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** check_v1 验证两候选集合交换顺序/重复合并不变；恢复同步后双方含两个版本；后续观察全部历史的写入因果覆盖它们。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v0.py、v1.py 的完整 checkpoint 围栏及 check_v1.py 检查围栏。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 冲突被保留但没有业务选择规则；停止写入并最终交付才可收敛。
   **Next:** v2 为必须显示单值的字段选择确定性 LWW，并展示损失。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/multi_leader/test_r03_replay.py::test_full_tutorial_sources_and_checks[1]' -q
```

该 pytest 节点先校验全部围栏与源码一致，再把依赖与 check 文件提取到临时目录，分别运行本版入口和正文语义检查。一个节点同时承担提取重放与行为验证；检查输出应包含本版 vN 标记和 passed。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
