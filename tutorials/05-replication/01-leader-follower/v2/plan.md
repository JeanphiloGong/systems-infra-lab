# R01 v2：读取必须越过写位置写作计划

订单先写主节点，客服随后读副本。只保留 Entry(position,key,value)、Leader 日志和 Follower 应用位置；Python 3.12+，前置 S03/T01。 本版目标是让读者复现“读取必须越过写位置”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/replication/leader_follower/v2.py` 为准。前置为 [v1 检查点](../v1/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 客户写 paid 后刷新页面，不能接受自己刚写之前的状态。
   **Naive:** v1 直接读 follower.data，不携带读者需要的最低进度。
   **Break:** 在已接收但未应用的副本调用 read_after(...,timeout_steps=0)，应超时。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** write 返回日志位置；read_after 按逻辑步等待该位置，read_from_leader 提供读主路径。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 读主得到 paid；0 步抛 TimeoutError；允许 1 步后副本得到 paid。正文两次打印 paid。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/replication/leader_follower/v2.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 步数不是墙钟 timeout，固定主节点，没有失效转移。
   **Next:** v3 比较写成功的确认位置，而不只比较读取位置。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/replication/leader_follower/test_replay_r01.py::test_exact_tutorial_checkpoint_executes[2]' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v2_barrier_wait_timeout_and_leader_read' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
