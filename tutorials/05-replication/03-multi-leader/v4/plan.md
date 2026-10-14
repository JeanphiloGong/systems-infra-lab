# R03 v4：同一请求负载比较拓扑写作计划

## 场景与契约

决策者要比较跨地区写入延迟、分区成功数和冲突损失。 读者需掌握 Python 与 R01/R02/C01 的复制、读取契约与分区。先重放 [v3](../v3/tutorial.md)，再扩展本篇行为。 模型只保留A/B 两地区、逻辑事件、版本元数据和确认轨迹；不变量是确认、冲突和收敛各自可追溯，合并丢失不得称为无损同步。

## 有序写作任务

1. **Pressure:** 决策者要比较跨地区写入延迟、分区成功数和冲突损失。
   **Naive:** 把不同调用节奏下的两次单独演示当成性能比较。
   **Break:** 分区使单主 B 请求超时，多主却确认两次但最终丢掉一个名称。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** experiment 对同一 A/B 调用节奏跑 single/multi 与分区开关；从 Request 统计成功/超时延迟、确认数、冲突候选和赢家。
   依赖任务 1；目标为 `labs/replication/multi_leader/v0.py`、`labs/replication/multi_leader/v2.py`、`labs/replication/multi_leader/v4.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** check_v4 验证联网 single 延迟 [2,2*delay+2]、multi [2,2]；分区 single 确认1/超时[100]，multi 确认2并丢 A-profile，winner=B-profile；恢复后均收敛。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v0.py、v2.py、v4.py 的完整 checkpoint 围栏及 check_v4.py 检查围栏。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 两次单键请求不代表吞吐压测，无存储成本或真实 WAN；多地区不必是多主。
   **Next:** 把观测迁移到真实服务前定义负载与持久性；R04 观察真实 PostgreSQL 复制。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/multi_leader/test_r03_replay.py::test_full_tutorial_sources_and_checks[4]' -q
```

该 pytest 节点先校验全部围栏与源码一致，再把依赖与 check 文件提取到临时目录，分别运行本版入口和正文语义检查。一个节点同时承担提取重放与行为验证；检查输出应包含本版 vN 标记和 passed。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
