# T01 v1 写作计划

前置 v0。余额页面是否会显示随后回滚的扣款？模型只加一个连接，核心为写事务、读事务、回滚和语句顺序；不变量为未提交 70 不对另一连接可见。PG 的 READ UNCOMMITTED 按 READ COMMITTED 执行是数据库行为，不制造虚假脏读示例。

1. 在 tutorial.md 首段从 v0 的单连接缺口引出另一观察者；规模 S，prose-only，验收给出 W-update/R-select/W-rollback/R-select 轨迹。
2. 依赖任务 1，编写 dirty_read 函数 checkpoint 到 observations.py；规模 M。读事务设 RC，写事务更新但不提交，验收自己读 70、别人读 100、回滚后 100。force_rollback 仅控制教学故障，入口仍建立新 schema。
3. 依赖任务 2，只替换 reader 隔离级别为 RU，patch；规模 S，验收相同结果，解释 RU 名称不代表支持脏读。
4. 依赖任务 3，最后一步提供 observations.py 完整 checkpoint 与 CLI 运行，规模 M。schema.sql 沿用 v0；从正文代码独立重放两级别。函数输入仅接受两个已初始化空闲 autocommit 连接和允许级别；本版本观察函数是受控实验，不是通用事务 API。

文档目标均为本目录 tutorial.md，检查包括两级别结果与回滚后两行数据、非法级别拒绝。下一缺口是两次都读已提交值却不属于同一快照。无 checkpoint commit；独立 review 后才验收。


## Tutorial Increment

- **Pressure:** The a transfer and a concurrent balance report scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v0 保证失败转账回滚，但用户的余额页面由另一个连接查询。在扣款完成、回滚尚未发生的短暂窗口里，它会不会显示 70？我们保留 v0 的两行数据，只增加一个观察连接。目标不是实现隔离机制，而是建立可复现的证据。 前置为 [v0](../v0/tutorial.md)，沿用其 `schema.sql`、uv 环境及临时 PostgreSQL。两个连接都设置 autocommit=True，显式事务块控制边界。每次命令使用新 schema，避免上次实验影响结果。
- **Change:** # T01 v1：另一个连接能看到未提交的扣款吗？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/isolation -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T01 isolation teaching model for a transfer and a concurrent balance report; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of T01 isolation, carrying forward the state and invariant rather than restarting from a disconnected example.

