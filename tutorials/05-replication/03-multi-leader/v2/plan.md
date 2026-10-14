# R03 v2：LWW 的时钟偏移代价写作计划

## 场景与契约

产品必须返回一个展示名称，不能始终显示冲突集合。 读者需掌握 Python 与 R01/R02/C01 的复制、读取契约与分区。先重放 [v1](../v1/tutorial.md)，再扩展本篇行为。 模型只保留A/B 两地区、逻辑事件、版本元数据和确认轨迹；不变量是确认、冲突和收敛各自可追溯，合并丢失不得称为无损同步。

## 有序写作任务

1. **Pressure:** 产品必须返回一个展示名称，不能始终显示冲突集合。
   **Naive:** 以物理时间较大者为赢家并把赢家称为真实最后修改。
   **Break:** A 提前 1000ms 的早写 timestamp=1002，B 实际后写 timestamp=4；同步后早写获胜。
   先在正文给出该调用轨迹，标明观测时刻及已发生的状态变化，作为后续修改的比较基线。

2. **Change:** Version 用 timestamp_ms/region/sequence 作确定性全序；merge 取最大项，维持本地确认网络流程。
   依赖任务 1；目标为 `labs/replication/multi_leader/v0.py`、`labs/replication/multi_leader/v2.py` 的相关方法及 [本版正文](tutorial.md) 的调用说明。解释谁修改状态、读者从何处取得输出。
   **Check:** check_v2 验证交换/重复/同时间戳裁决；确认时刻 2<4，但后写从两副本消失；旧消息不能逆转赢家。
   验收不能只检查“运行成功”，要逐项核对结果、错误或进度。

3. **Freeze:** 依赖任务 2；正文必须保留 v0.py、v2.py 的完整 checkpoint 围栏及 check_v2.py 检查围栏。从正文提取所有文件后重放，不借用更新后的仓库模块。
   **Still-lacks:** 收敛丢弃了成功更新；时间排序不证明真实先后，不能用此寄存器无损累计计数。
   **Next:** v3 换成只增计数，按作者分量合并。

## 执行与证据边界

仓库根目录执行；Python 3.12+、`uv sync --group dev`，不需数据库或 Docker：

```bash
uv run pytest 'tests/replication/multi_leader/test_r03_replay.py::test_full_tutorial_sources_and_checks[2]' -q
```

该 pytest 节点先校验全部围栏与源码一致，再把依赖与 check 文件提取到临时目录，分别运行本版入口和正文语义检查。一个节点同时承担提取重放与行为验证；检查输出应包含本版 vN 标记和 passed。

本次仅修订计划，不提交 checkpoint。缺失的路线图行为另列在 wave-08-r02-r03-plans.md，不能通过缩小目标消除；实现与教程变更需另行验证。
