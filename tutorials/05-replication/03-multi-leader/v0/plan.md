# R03 v0：远程单主确认延迟写作计划

## 场景与契约

B 地区修改由 A 主节点保存的展示名称。 读者需掌握 Python 与 R01/R02/C01 的复制、读取契约与分区。本版建立整个模块的观测基线。 模型只保留A/B 两地区、逻辑事件、版本元数据和确认轨迹；不变量是确认、冲突和收敛各自可追溯，合并丢失不得称为无损同步。

## 有序写作任务

1. **Pressure:** B 地区修改由 A 主节点保存的展示名称。
   **Naive:** 只计算本地处理耗时，忽略请求与回复各一次跨区传输。
   **Break:** 单程 40ms、本地 2ms 时，B 请求需 82ms，A 只需 2ms；分区请求到 100ms 仍未确认。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** Network 事件堆推进逻辑时钟，Request 记录调用/完成/确认时间；SingleLeader 在主节点提交后回复。
   依赖任务 1；目标为 `labs/replication/multi_leader/v0.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** check_v0 对 10/40/80ms 等不同延迟核对 remote=2*delay+2；超时 50ms 的迟到成功在 162ms 才确认，客户端耗时仍是 50。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v0.py 的完整 checkpoint 围栏及 check_v0.py 检查围栏。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 模拟时钟不是网络 benchmark；已超时不代表操作取消，未测排队或磁盘。
   **Next:** v1 让两地区本地确认，并保留并发冲突。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/multi_leader/test_r03_replay.py::test_full_tutorial_sources_and_checks[0]' -q
```

该 pytest 节点先校验全部围栏与源码一致，再把依赖与 check 文件提取到临时目录，分别运行本版入口和正文语义检查。一个节点同时承担提取重放与行为验证；检查输出应包含本版 vN 标记和 passed。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
