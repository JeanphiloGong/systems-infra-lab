# T01 v1 写作计划

前置 v0。余额页面是否会显示随后回滚的扣款？模型只加一个连接，核心为写事务、读事务、回滚和语句顺序；不变量为未提交 70 不对另一连接可见。PG 的 READ UNCOMMITTED 按 READ COMMITTED 执行是数据库行为，不制造虚假脏读示例。

1. 在 tutorial.md 首段从 v0 的单连接缺口引出另一观察者；规模 S，prose-only，验收给出 W-update/R-select/W-rollback/R-select 轨迹。
2. 依赖任务 1，编写 dirty_read 函数 checkpoint 到 observations.py；规模 M。读事务设 RC，写事务更新但不提交，验收自己读 70、别人读 100、回滚后 100。force_rollback 仅控制教学故障，入口仍建立新 schema。
3. 依赖任务 2，只替换 reader 隔离级别为 RU，patch；规模 S，验收相同结果，解释 RU 名称不代表支持脏读。
4. 依赖任务 3，最后一步提供 observations.py 完整 checkpoint 与 CLI 运行，规模 M。schema.sql 沿用 v0；从正文代码独立重放两级别。函数输入仅接受两个已初始化空闲 autocommit 连接和允许级别；本版本观察函数是受控实验，不是通用事务 API。

文档目标均为本目录 tutorial.md，检查包括两级别结果与回滚后两行数据、非法级别拒绝。下一缺口是两次都读已提交值却不属于同一快照。无 checkpoint commit；独立 review 后才验收。
