# R01 v4：中断追平后重复投递写作计划

订单先写主节点，客服随后读副本。只保留 Entry(position,key,value)、Leader 日志和 Follower 应用位置；Python 3.12+，前置 S03/T01。 本版目标是让读者复现“中断追平后重复投递”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/replication/leader_follower/v4.py` 为准。前置为 [v3 检查点](../v3/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 副本只应用第一项就中断，重连时主节点重发整个日志。
   **Naive:** 沿用 v0 的严格下一位置检查，会把重复的第一项视为错误。
   **Break:** stop_after=1 后重新投递两项；必须跳过旧位置且不能跳过缺口。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** apply 忽略已应用位置，仍拒绝未来缺口；catch_up 接受停止边界并保留应用位置。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 三次 catch_up 后 position=2、order=paid；随后直接投递位置 4 抛 ValueError。正文使用 order-1，打印 {'order-1': 'paid'} 2。catch_up 切片跳过旧项；apply 本身也忽略已应用位置，两者不要混同为同一个测试。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/replication/leader_follower/v4.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 没有持久网络游标、领导者选举或真正重启后的恢复。
   **Next:** R02 用复制进度定义会话读取契约；真实 WAL 复制另见 R04。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/replication/leader_follower/test_replay_r01.py::test_exact_tutorial_checkpoint_executes[4]' -q
uv run pytest 'tests/replication/leader_follower/test_r01.py::test_v4_resume_and_duplicate_delivery_are_safe' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
