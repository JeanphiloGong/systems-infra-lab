# R01 v0：顺序应用日志写作计划

订单先写主节点，客服随后读副本。只保留 Entry(position,key,value)、Leader 日志和 Follower 应用位置；Python 3.12+，前置 S03/T01。 本版目标是让读者复现“顺序应用日志”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/replication/leader_follower/v0.py` 为准。这是模块起点，先用下面的调用轨迹定义基线，再引入数据结构。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 副本收到 created、paid 两次订单更新，最终不能倒退到 created。
   **Naive:** 把每个收到的值直接覆盖字典，不核对顺序。
   **Break:** 应用位置到 2 后再投递位置 1，应拒绝，不能覆盖 paid。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** Leader.write 分配连续位置；Follower.apply 只接受 applied_position+1。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 应用后 data={'order':'paid'}、applied_position=2；再投递首项抛 ValueError。正文入口打印 {'order-1': 'paid'} 2。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/replication/leader_follower/v0.py` 围栏（仅标准库依赖），包含默认调用入口和 `--writer`/`--reader` 两个进程入口。writer 写入 JSON checkpoint 后退出，独立 reader 进程重新打开它并打印相同的位置和数据；完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** checkpoint 是教学用 JSON 写入，尚未提供原子替换、校验和或多副本故障恢复。
   **Next:** v1 将收到日志与应用日志分开。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/replication/leader_follower/test_replay_r01.py::test_exact_tutorial_checkpoint_executes[0]' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v0_applies_order_and_keeps_progress_after_restart' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v0_writer_and_receiver_are_separate_processes' -q
```

第一条读取正文围栏并用临时文件启动子进程；第三条明确启动两个不同的 Python 进程，断言 reader 从 writer 留下的 checkpoint 恢复位置 2 和 paid 数据。第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把三种验证混为一谈。

本版实现使用本地 JSON checkpoint，不建立外部服务或永久进程。需独立审核后才能把缺口标为已解决。
