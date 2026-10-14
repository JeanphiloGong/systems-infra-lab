# C01 v0：超时后的结果未知写作计划

跨机房请求遇到消息丢失时，客户端需要区分可知结果、旧读和不可用。模型压缩为消息投递记录、分区标志、读取策略以及三个成员的读写集合；前置 R02。 本版目标是让读者复现“超时后的结果未知”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/consensus/cap_quorum/v0.py` 为准。这是模块起点，先用下面的调用轨迹定义基线，再引入数据结构。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 订单操作发出后收不到回复，调用者要判断是否可以重试。
   **Naive:** 把超时直接解释为远端从未执行。
   **Break:** 消息未投递时 timeout('op-1') 返回 unknown，不能返回失败已回滚。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** 用 Message/Partition 记录消息与 completed 集合；只有交付 done:op-1 才登记完成，交付 apply 请求本身不算完成确认。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 测试未交付为 unknown，交付后为 completed；正文入口打印 unknown。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/consensus/cap_quorum/v0.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 这是可观测投递状态模型，未运行真实网络或验证外部业务效果，重试幂等性需 D01。
   **Next:** v1 继续追问增加确认能否消除双方的不确定性。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/consensus/cap_quorum/test_replay_c01.py::test_exact_checkpoint_executes[0]' -q
uv run pytest 'tests/consensus/cap_quorum/test_c01.py::test_v0_timeout_cannot_classify_remote_operation' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
