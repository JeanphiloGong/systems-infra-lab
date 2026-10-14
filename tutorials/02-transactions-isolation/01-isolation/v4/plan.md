# T01 v4 写作计划

前置 v0-v3 全部实验。目标为审计转账证据，分清 ACID 属性。场景为代码评审者判断“使用事务所以业务安全”的论断；模型沿用两账户，只增加违反 CHECK 与合法单边扣款。

1. 依赖 v3，规模 S，tutorial.md 第一步 prose-only：把回滚、未提交读取、读偏斜、幻读轨迹对应 A/I，验收不宣称串行化或断电持久性。
2. 依赖任务 1，规模 M，acid.py 中 constraint_trace checkpoint：负余额被 CHECK 拒绝，而单边减一合法提交为 199。先验条件为 v0 初始数据；返回两次总额。验证 200/199，解释 C 依赖已编码规则。
3. 依赖任务 2，规模 M，完整 acid.py checkpoint：恢复初始余额，转账提交并关闭连接，新连接读取 70/130。重放完整脚本；明确此证据仅证明提交跨连接可见，不代表数据库重启或断电恢复。通过已有实验命令汇总 A/I。

所有任务不提交。独立 reviewer 检查 C 与 D 的表述；T01 最终具备四属性证据地图，缺口交给 T02 与 S03/A01。无数据库持久化模拟，无新运行时抽象。


## Tutorial Increment

- **Pressure:** The a transfer and a concurrent balance report scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 评审转账代码时，有人说“用了数据库事务，所以业务已经满足 ACID”。完成 [v0](../v0/tutorial.md) 到 [v3](../v3/tutorial.md) 后，你已经有足够的反例追问这句话。这里不再增加隔离级别，而是把观察结果对应到可以支持的结论。 v0 的扣款后失败留下 100/100，而两条独立提交留下 70/100。这支持本例的 Atomicity：明确事务边界中的两次更新共同成功或回滚。它没有解决外部邮件和数据库如何共同提交。
- **Change:** # T01 v4：我们究竟验证了 ACID 的哪一部分？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/isolation -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T01 isolation teaching model for a transfer and a concurrent balance report; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

