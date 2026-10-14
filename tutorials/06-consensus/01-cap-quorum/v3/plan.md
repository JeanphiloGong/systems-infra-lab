# C01 v3：集合相交不足以建立线性一致协议写作计划

跨机房请求遇到消息丢失时，客户端需要区分可知结果、旧读和不可用。模型压缩为消息投递记录、分区标志、读取策略以及三个成员的读写集合；前置 R02。 本版目标是让读者复现“集合相交不足以建立线性一致协议”的确切结果。

## 外部契约与任务依赖

输入、状态变化和返回值以 [本版教程](tutorial.md) 的完整文件 `labs/consensus/cap_quorum/v3.py` 为准。前置为 [v2 检查点](../v2/tutorial.md)；先重放其观测，再修改本版边界。 不变量是观测与声明一致：未观察到的完成、未应用的日志或未证明的一致性均不得写成成功保证。

## 按顺序写作

1. **Pressure:** 三副本服务尝试用 R+W>N 作为所有读写正确性的唯一依据。
   **Naive:** 把读写集合有交集直接等同于并发历史可线性化。
   **Break:** N=3,R=W=2，写入仅到 A 时，先读 A/B 返回 new，再读 B/C 返回 old，最后 B 确认写成功。两个读按实时顺序完成却倒退，无法放置唯一写入的线性化位置。
   先把该输入及结果写入正文，作为本版的失败或不足证据；不要在介绍失败前隐藏加入解决机制。

2. **Change:** has_intersection 枚举组合；concurrent_history 固定写入投递和读取顺序，每次 quorum_read 只看指定两个响应，暴露未完成写入被读到后的新旧倒退。
   依赖任务 1，目标为本版 Python 文件的相关方法和正文对应调用。解释改变的状态字段及谁推进它。
   **Check:** 2/2 返回 True，1/1 返回 False；历史 reads 为 [(1,'new'),(0,'old')]，write_acks=2，read1 返回早于 read2 调用，最后才写成功。
   将该断言与下面版本专属测试一一对应；错误类型和位置变化也属于验收条件。

3. **Freeze:** 依赖任务 2，在正文保留一个完整 `labs/consensus/cap_quorum/v3.py` 围栏（仅标准库依赖），包含调用入口；提取为临时文件执行，再运行行为断言。完整文件是本版冻结产物，不能从后续版本补代码。
   **Still-lacks:** 反例是确定性消息交错，无真实网络、读写回或通用历史检查器；它反驳相交充分性，不实现修复协议。
   **Next:** C02 引入多数投票与领导权限，C03 研究日志提交规则。

## 重放与验收

从仓库根目录运行，Python 3.12+，先完成 `uv sync --group dev`；不需要数据库：

```bash
uv run pytest 'tests/consensus/cap_quorum/test_replay_c01.py::test_exact_checkpoint_executes[3]' -q
uv run pytest 'tests/consensus/cap_quorum/test_c01.py::test_v3_intersection_and_quorum_values' -q
uv run pytest 'tests/consensus/cap_quorum/test_c01.py::test_v3_pending_write_causes_new_then_old_read' -q
```

第一条读取正文围栏、核对源码一致性并在临时文件子进程中断言 JSON 观察；其余测试核对集合性质和完整八步历史。

反例实现、正文和测试已同步修订，不建立新的 checkpoint commit。需独立审核后才能关闭缺口。
