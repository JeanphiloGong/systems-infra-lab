# T02 v0 计划

目标为值班页面观察历史状态，模型两行两连接；事务提交后新查询见 false，已建立 RR 快照仍见 true。前置 T01，函数接收两个空闲 autocommit 连接和 early_read 布尔值，返回 first/second/fresh。

1. tutorial.md 第一步，规模 S，checkpoint schema.sql；初始化两位医生均在岗，读到 true。不先引入版本链。
2. 第二步规模 M，checkpoint snapshot_timing 函数，早读建立快照后另事务更新，验收 true/true/false；明确同一事务内第二次读。
3. 第三步规模 S，patch 把首读移到 writer 提交之后，验收 false/false/false；BEGIN 已发生但尚无读取快照。
4. 最后一步规模 M，checkpoint snapshots.py，组装 CLI 和独立 schema；与 T01 相同的资源生命周期，无新 runtime helper。重放两命令及测试，冻结后下一版解释多版本模型。

任务按上述顺序依赖，不提交 Git。文档每步须有可运行检查，最后提供完整源。边界：只观察本调度，不检查 PostgreSQL tuple 内部字段或 vacuum。独立审查后验收。
