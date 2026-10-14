# T01 v2 写作计划

前置 v1 的双连接入口与 v0 transfer。报表把分开查询的 A/B 相加；模型保留两 SELECT 之间的一次已提交转账。读取事件必须标明各自快照，真实已提交状态总额始终 200。

1. 文档 tutorial.md 第一步，规模 S，checkpoint：新增 read_skew，RC 读 A=100，调用 transfer 提交，再读 B=130。依赖 v1，验收组合总额 230 但 SQL sum=200。
2. 第二步规模 S，patch：仅改隔离参数 RR，依赖任务 1。验收 A/B=100/100，说明首条读取建立快照；单语句 sum 与事务快照是不同修复范围。
3. 最后一步规模 M，checkpoint：完整 observations.py 包含旧行为和新 CLI 分支；依赖任务 2。独立提取 v0 transfer/schema 与本版代码重放 RC/RR。非法级别、写入最终 70/130、旧 dirty 实验继续检查。

外部契约：read_skew 返回 first,second,single_statement 三个整数，接收两个空闲 autocommit 连接与允许级别，不重置数据。无新增 helper；不声称 RR 可串行化；下一版转向谓词集合变化。所有任务不提交，独立审核后才完成。


## Tutorial Increment

- **Pressure:** The a transfer and a concurrent balance report scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 余额报表为了复用两个查询，先读取 A，再读取 B，最后在 Python 相加。v1 已证明未提交扣款不会泄漏，但如果转账恰好在两次读取之间提交，会发生什么？本版沿用两账户和两个连接；新增的只有一个明确的提交位置。 完成 [v1](../v1/tutorial.md)，保留 v0 的 `transfer.py` 与 `schema.sql`。总额不变量仍为 200。实验函数要求初始 100/100，CLI 每次重新初始化；不要在同一组已经转账的数据上重复调用后仍期待相同结果。
- **Change:** # T01 v2：每次都读已提交数据，为什么总额还是错？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/isolation -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T01 isolation teaching model for a transfer and a concurrent balance report; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of T01 isolation, carrying forward the state and invariant rather than restarting from a disconnected example.

