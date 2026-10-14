# R02 v0：停止写入后收敛写作计划

## 场景与契约

用户保存 name=Ada 后立即刷新副本。 读者需掌握 Python 与 R01 的复制进度。本版建立整个模块的观测基线。 模型只保留主副本字典、版本、调用顺序和读取结果；不变量是每个返回值对应已声明的读取条件。

## 有序写作任务

1. **Pressure:** 用户保存 name=Ada 后立即刷新副本。
   **Naive:** 同步修改两份字典，掩盖副本滞后。
   **Break:** write 后 read_replica 返回 None。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** pending 保存写入顺序，apply_one 弹出一项；converge 排空队列。
   依赖任务 1；目标为 `labs/replication/consistency/v0.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** 正文输出 None、Ada；测试验证 converge 后副本为 Ada。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v0.py 的完整 checkpoint 围栏与可执行入口。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 只有显式调用 converge 才推进，未建模传输失败或后台进度。
   **Next:** v1 让写入者携带会话版本避免自己的旧读。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/consistency/test_replay_r02.py::test_exact_checkpoint_executes[0]' -q
uv run pytest 'tests/replication/consistency/test_r02.py::test_v0_stale_read_then_eventual_convergence' -q
```

提取测试在临时文件运行正文，但只断言退出码；第二条针对实现核对具体行为。二者不能合称为已在提取代码中验证全部语义。正文与实现仍需人工对照。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
