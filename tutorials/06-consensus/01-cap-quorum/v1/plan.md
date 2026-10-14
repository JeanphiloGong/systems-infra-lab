# C01 v1：最后一条确认仍可丢失写作计划

跨机房请求遇到消息丢失时，客户端需要区分可知结果、旧读和不可用。模型压缩为消息投递记录、分区标志、读取策略以及三个成员的读写集合；前置 R02。 本版目标是让读者复现“最后一条确认仍可丢失”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/consensus/cap_quorum/v1.py` 为准。前置为 [v0 检查点](../v0/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 两个机房希望仅在双方都知道对方已知时执行协调动作。
   **Naive:** 再增加一条 ack，假设发送方由此获得共同确定性。
   **Break:** two_generals_trace() 的固定轨迹含 ack lost；接收方与发送方不能同时确定最终确认。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** 显式列出计划发送、接收、确认和确认丢失，conclude 根据末次确认是否成功给出结论。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 轨迹包含 ack lost，conclude 返回 coordination incomplete；正文打印轨迹和该字符串。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/consensus/cap_quorum/v1.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 消息轨迹不是异步共识实现，也不是 Raft 在其故障假设下不可能工作的证明。
   **Next:** v2 从确认问题转向分区期间可执行的读策略。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/consensus/cap_quorum/test_replay_c01.py::test_exact_checkpoint_executes[1]' -q
uv run pytest 'tests/consensus/cap_quorum/test_c01.py::test_v1_lost_final_ack_leaves_coordination_incomplete' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
