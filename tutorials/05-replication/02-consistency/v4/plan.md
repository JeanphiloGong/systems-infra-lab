# R02 v4：不同读契约的分区边界写作计划

## 场景与契约

资料读取接口需要表明在分区时是拒绝还是接受旧值。 读者需掌握 Python 与 R01 的复制进度。先重放 [v3](../v3/tutorial.md)，再扩展本篇行为。 模型只保留主副本字典、版本、调用顺序和读取结果；不变量是每个返回值对应已声明的读取条件。

## 有序写作任务

1. **Pressure:** 资料读取接口需要表明在分区时是拒绝还是接受旧值。
   **Naive:** 给所有读取标上 strong，却不说明写者不可达时行为。
   **Break:** partitioned=True 后 LINEARIZABLE 读取抛 ConnectionError，EVENTUAL 仍返回已有 Ada。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** Contract 显式选择 EVENTUAL/SESSION/SNAPSHOT/LINEARIZABLE；Read 携带值和版本。
   依赖任务 1；目标为 `labs/replication/consistency/v4.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** 入口输出 Read(value='Ada',version=1) 和 ConnectionError；测试检查正常的三种返回及分区拒绝。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v4.py 的完整 checkpoint 围栏与可执行入口。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** SNAPSHOT 只保留每个键的有限内存版本，不能跨进程持久化；分区时 SESSION 对落后或缺失副本明确失败，客户端重试/恢复策略仍未建模。不能声称生产级快照或会话路由。
   **Next:** 补齐历史版本与分区会话测试再声称完整契约比较；R03 转向多写者冲突。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/consistency/test_replay_r02.py::test_exact_checkpoint_executes[4]' -q
uv run pytest 'tests/replication/consistency/test_r02.py::test_v4_contracts_and_partition_boundary' -q
```

提取测试在临时文件运行正文，但只断言退出码；第二条针对实现核对具体行为。二者不能合称为已在提取代码中验证全部语义。正文与实现仍需人工对照。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
