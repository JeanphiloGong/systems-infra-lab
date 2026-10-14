# T02 模块计划

读者完成 T01，能控制两连接事务顺序。值班系统允许医生下班，但至少一人必须在岗。压缩为两医生、两个事务和一个固定排班组；不含权限、班次时间、多医院、完整 PostgreSQL 版本结构。

核心不变量：每次读取符合其快照；受保护版本完成后至少一人在岗。v2 刻意打破后者作为反例。供应事实来自 roadmap；实施选择为 PostgreSQL RR、整数提交序号教学模型、v3 单个 guard 行把跨行规则变成写冲突。

1. v0：新旧快照对比，验证 BEGIN 不等于首次查询；源码 snapshots.py/schema.sql。
2. v1：解释只存当前值为何无法回答旧快照，引入 committed version list；model.py，明确不是 PostgreSQL 实现。
3. v2：两个事务都看见两人在岗，各自更新不同医生并提交；write_skew.py，真实结果零人在岗。
4. v3：增加 guard 行更新，第二个旧快照写者发生序列化失败，完整重试后拒绝下班；protected.py，比较业务不变量与争用成本。

每版先 plan，再逐步教程，最终代码块可独立重放。测试先出现缺少实现的 RED，然后真实 PG 或纯模型验证；reviewer 独立重放并提出修复。每版使用新 t02_ schema，只删除自己创建的资源。无 Git 提交。

审查风险：把 snapshot 时间说成连接时间；模型假装实现事务 ID 可见性；write skew 实际只有一个事务；guard 仅加锁却不改变行版本；serialization failure 后只重试 UPDATE 而不重做业务读取。
