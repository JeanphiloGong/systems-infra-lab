# R01 v1：收到不等于可读写作计划

订单先写主节点，客服随后读副本。只保留 Entry(position,key,value)、Leader 日志和 Follower 应用位置；Python 3.12+，前置 S03/T01。 本版目标是让读者复现“收到不等于可读”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/replication/leader_follower/v1.py` 为准。前置为 [v0 检查点](../v0/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 订单已写成功，但副本尚未处理接收到的更新。
   **Naive:** v0 的同步 apply 把网络接收和可见状态变化视为同一步。
   **Break:** receive 后立即检查 follower.data，结果仍为 {}。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** 引入 pending 列表及 apply_one；接收只入队，显式应用才推进数据和位置。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** receive 后 {}；apply_one 后 {'order':'paid'}。正文输出 {} 然后 {'order-1': 'paid'}。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/replication/leader_follower/v1.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 没有后台线程或真实延迟测量；调用顺序模拟滞后。
   **Next:** v2 用写入位置约束后续读取。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/replication/leader_follower/test_replay_r01.py::test_exact_tutorial_checkpoint_executes[1]' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v1_exposes_stale_read_until_apply_step' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
