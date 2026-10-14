# T01 v3 写作计划

前置 v2。场景为重复查询余额至少 50 的账户数，压缩为一次插入，核心为谓词集合、事务快照、提交边界。不变量：输出精确对应其快照；插入新账户合法地把总额从 200 增为 250，不能要求转账不变量。

1. 依赖 v2，规模 M，tutorial.md 第一步新增 phantom_read checkpoint。R 首次 count=2，W 插入第三行并提交，R 再 count；RC 得 3。验收第三次在事务结束后读为 3。
2. 依赖任务 1，规模 S，配置 patch 改 RR，验收 2/2/3。解释快照始于第一条 SELECT，插入没有被阻塞；不将幻读消失等同串行化。
3. 依赖任务 2，规模 M，完整 observations.py checkpoint，给 CLI phantom 分支及双级别运行。独立正文回放与旧版本实验继续通过。无新 helper、无提交。

函数外部契约为两个已初始化 autocommit 连接与允许级别，返回 before/after/fresh。审查重点是读者事务必须跨越 writer 提交，最后读取必须在该事务之外。下一版整理 ACID，不引入新的隔离算法。


## Tutorial Increment

- **Pressure:** The a transfer and a concurrent balance report scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 运营页面先统计余额至少 50 的账户数，稍后重复同一查询。如果另一事务在两次查询之间创建新账户，第二次是否会多一行？v2 观察已有行的新版本，本版观察匹配谓词的集合变化。 前置 [v2](../v2/tutorial.md)。仍用相同临时数据库和初始化 SQL。本次第三个账户存入 50，所以真实总额变成 250 是输入带来的正确变化，不是转账丢钱。我们检查的是集合可见性。
- **Change:** # T01 v3：相同范围查询为什么多了一行？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/isolation -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T01 isolation teaching model for a transfer and a concurrent balance report; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of T01 isolation, carrying forward the state and invariant rather than restarting from a disconnected example.

