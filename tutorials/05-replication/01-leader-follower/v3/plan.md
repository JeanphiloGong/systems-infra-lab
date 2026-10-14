# R01 v3：确认策略决定可能丢失范围写作计划

订单先写主节点，客服随后读副本。只保留 Entry(position,key,value)、Leader 日志和 Follower 应用位置；Python 3.12+，前置 S03/T01。 本版目标是让读者复现“确认策略决定可能丢失范围”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/replication/leader_follower/v3.py` 为准。前置为 [v2 检查点](../v2/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 主节点返回成功后故障，客服要知道哪笔更新尚未被副本接受。
   **Naive:** 异步 write 仅更新主日志和主数据就返回。
   **Break:** 异步条目位置为 1，但 confirmed_position=0，fail_before_replication 返回该条目。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** AckMode.FOLLOWER 在副本顺序 apply 后推进 confirmed_position；ASYNC 保留原返回路径。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 首条处于可能丢失列表；手动补齐首条后写 paid 并等待副本，确认位置等于新条目位置，副本为 paid。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/replication/leader_follower/v3.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** fail_before_replication 只列出风险后缀，不杀进程；没有实际等待延迟、fsync 或故障后恢复测量。
   **Next:** v4 重发日志时去重并从应用位置继续追平。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/replication/leader_follower/test_replay_r01.py::test_exact_tutorial_checkpoint_executes[3]' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v3_ack_modes_have_different_loss_boundaries' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
