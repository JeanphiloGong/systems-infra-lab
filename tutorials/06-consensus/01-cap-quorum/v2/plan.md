# C01 v2：分区期间拒读还是旧读写作计划

跨机房请求遇到消息丢失时，客户端需要区分可知结果、旧读和不可用。模型压缩为消息投递记录、分区标志、读取策略以及三个成员的读写集合；前置 R02。 本版目标是让读者复现“分区期间拒读还是旧读”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/consensus/cap_quorum/v2.py` 为准。前置为 [v1 检查点](../v1/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 用户更新资料后，从与写节点失联的机房发起读取。
   **Naive:** 无论网络状态如何，都称副本返回的旧值为最新结果。
   **Break:** 相同 partition 状态下，两种策略不能同时承诺新值和持续可读。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** PartitionedStore 使用 REJECT_ON_PARTITION 或 SERVE_OLD_READ；分区时前者返回 unavailable，后者返回保留的 value。实现只有单个值和分区标志，没有实际主副本进程。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** safe.read() 为 unavailable；available.read() 为 old。不能把 unavailable 当作最新业务值。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/consensus/cap_quorum/v2.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 两个分支展示策略取舍，不证明完整 CAP 定理或网络故障检测正确性。
   **Next:** v3 检查多数集合交集究竟能支持哪些结论。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/consensus/cap_quorum/test_replay_c01.py::test_exact_checkpoint_executes[2]' -q
uv run pytest 'tests/consensus/cap_quorum/test_c01.py::test_v2_partition_exposes_cap_policy_choice' -q
```

第一条读取正文围栏并用临时文件启动子进程，但现有测试只断言退出码，不能单独证明上面的预期输出；第二条针对实现断言本版行为。审阅须对照围栏与实现，并逐项核对 Check，不能把两种验证混为一谈。

本批次只修订计划，不改实现或重写教程，不建立新的 checkpoint commit。需独立审核后才能把缺口标为已解决。
