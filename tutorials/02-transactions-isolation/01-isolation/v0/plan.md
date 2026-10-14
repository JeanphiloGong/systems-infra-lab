# T01 v0 写作计划

目标：让转账调用者在扣款后异常时仍看到 100/100。模型为两账户、整数金额、两 UPDATE；本版不处理并发或外部支付。来源目标必须存在且不同，金额正整数，扣款余额足够。

## 任务 1：运行直接更新

在 tutorial.md 的起点提供 schema.sql 与 autocommit=True 的两 UPDATE。依赖只有环境；规模 S；checkpoint。验收成功为 70/130。必须解释参数化 SQL 与整数单位；先不引入事务封装。

## 任务 2：扣款后失败

依赖任务 1；规模 S；patch，目标当前脚本。把确定性异常放在两 UPDATE 之间，查询 70/100；错误后不再运行入账。冻结可重复错误，缺口为部分提交。不用 sleep。

## 任务 3：事务边界

依赖任务 2；规模 M；patch，目标 transfer.py。加入 with conn.transaction()，异常离开触发回滚；校验请求和条件 UPDATE 守住余额。验收正常、零负数、缺失账户、余额不足和故障后的实际表数据。

## 任务 4：完整检查点

依赖任务 3；规模 M；checkpoint，目标 transfer.py/schema.sql 和教程最后一步。解释入口 schema 创建清理，给出完整代码与命令。重放原故障仍为 100/100；成功为 70/130，错误进程非零。测试连接失败不得误报成功。冻结 v0 后才研究第二连接读取。

所有任务不提交 Git。验证命令 `uv run python -m pytest tests/transactions/isolation/test_t01_transfer.py -q`，还要在独立临时目录重放正文最终代码。独立审查前状态为 draft。需重点检查异常在事务外传播，以及非法目标导致扣款被回滚。


## Tutorial Increment

- **Pressure:** The a transfer and a concurrent balance report scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 账户 A 和 B 都有 100 个整数单位。用户让 A 转 30 给 B，成功后应该是 70/130；如果程序只完成扣款就失败，两边应该仍为 100/100。我们只保留两个账户和一次程序异常，不讨论支付网关、手续费或并发转账。这个模型已经足以暴露“多条 SQL 是否共同完成”的问题。 先按仓库环境文档启动临时 PostgreSQL，设置 `SYSTEMS_LAB_DATABASE_URL`，执行 `uv sync --locked`。以下命令均从仓库根目录运行。数据库必须是可丢弃的实验实例；程序会创建并清理独立 s
- **Change:** # T01 v0：转账失败后，钱去了哪里？; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/transactions/isolation -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a T01 isolation teaching model for a transfer and a concurrent balance report; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of T01 isolation, carrying forward the state and invariant rather than restarting from a disconnected example.

