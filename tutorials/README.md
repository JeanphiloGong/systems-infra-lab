# 教程入口

从 [T01 v0：转账执行到一半报错](02-transactions-isolation/01-isolation/v0/tutorial.md) 开始。
先完成 [环境准备](../docs/environment.md)，阅读 [从零学习约定](../docs/learning-workspace.md)。

`main` 中的实验和测试由你按正文创建。T01 v0-v4 给出连续的文件与测试步骤；其他专题使用各页的直接运行命令和断言。折叠区中的旧 pytest/replay 命令只用于 [参考分支检查](../docs/reference-checks.md)。

下面列出 40 个模块、196 篇版本正文。目录存在和历史审核都不等于你已完成学习；过去的作者验证记录见 [历史进度](../docs/progress.md)，完整依赖见 [总规划](../docs/roadmap.md)。

- [S01：页、记录与访问局部性](01-storage-engines/01-pages-and-locality/README.md)：v0–v4。
- [S02：B+Tree 索引](01-storage-engines/02-b-plus-tree/README.md)：v0–v7。
- [S03：WAL 与崩溃恢复](01-storage-engines/03-wal-and-recovery/README.md)：v0–v5。
- [S04：Bloom Filter 与负查询](01-storage-engines/04-bloom-filter/README.md)：v0–v3。
- [S05：LSM、Compaction 与写放大](01-storage-engines/05-lsm/README.md)：v0–v7。
- [S06：行存、列存与扫描](01-storage-engines/06-columnar-storage/README.md)：v0–v4。
- [F01：连接建立、复用与泄漏](01-storage-engines/07-connections/README.md)：v0–v3。
- [S07：PostgreSQL MVCC 版本回收与 Vacuum](01-storage-engines/07-vacuum/README.md)：v0–v4。
- [F02：负载均衡、限流与背压](02-traffic/02-admission/README.md)：v0–v4。
- [F03: Retry Storm and Circuit Breaker](02-traffic/03-retry/README.md)：v0–v4。
- [F04：惊群、同键合并与受限旧读](02-traffic/04-herd/README.md)：v0–v3。
- [T01：事务边界与隔离异常](02-transactions-isolation/01-isolation/README.md)：v0–v4。
- [T02：MVCC 与 Snapshot Isolation](02-transactions-isolation/02-mvcc/README.md)：v0–v3。
- [T03：锁与并发更新](02-transactions-isolation/03-locking/README.md)：v0–v4。
- [T04：可串行化与事务重试](02-transactions-isolation/04-serializability/README.md)：v0–v3。
- [P01：分区路由](03-partitioning-scaling/01-routing/README.md)：v0–v3。
- [P02：数据倾斜与热点](03-partitioning-scaling/02-skew/README.md)：v0–v3。
- [P03：在线迁移与重分片](03-partitioning-scaling/03-migration/README.md)：v0–v4。
- [Q01：规范化与反规范化](04-query/01-modeling/README.md)：v0–v3。
- [Q02：二级索引与覆盖读取](04-query/02-indexes/README.md)：v0–v3。
- [Q03：查询计划与成本估计](04-query/03-planner/README.md)：v0–v3。
- [Q04 物化视图与缓存](04-query/04-derived/README.md)：v0–v4。
- [R01: Leader-follower replication](05-replication/01-leader-follower/README.md)：v0–v4。
- [R02: consistency models and read contracts](05-replication/02-consistency/README.md)：v0–v4。
- [R03：多主与地理复制](05-replication/03-multi-leader/README.md)：v0–v4。
- [R04: PostgreSQL physical and logical replication](05-replication/04-postgres/README.md)：v0–v3。
- [C01: CAP, quorum, and indistinguishable failure](06-consensus/01-cap-quorum/README.md)：v0–v3。
- [C02: Leader Election](06-consensus/02-leader-election/README.md)：v0–v4。
- [C03 Raft 日志共识](06-consensus/03-raft/README.md)：v0–v8。
- [D01: idempotency and the exactly-once boundary](07-coordination/01-idempotency/README.md)：v0–v4。
- [D02：分布式锁与 Fencing](07-coordination/02-distributed-lock/README.md)：v0–v4。
- [D03: Distributed Transactions, 2PC and 3PC](07-coordination/03-distributed-commit/README.md)：v0–v4。
- [D04：Saga 与补偿](07-coordination/04-saga/README.md)：v0–v4。
- [E01：CDC 与投影同步](08-dataflows/01-cdc/README.md)：v0–v4。
- [E02：Schema Evolution](08-dataflows/02-schema-evolution/README.md)：v0–v3。
- [E03：事件溯源与反规范化读模型](08-dataflows/03-events/README.md)：v0–v4。
- [E04：Data Warehouse 与 Federation](08-dataflows/04-analytics/README.md)：v0–v3。
- [A01：Backup 与 PITR 边界](09-recovery/01-backup/README.md)：v0–v4。
- [A02：Checkpoint 与有界恢复](09-recovery/02-checkpoint/README.md)：v0–v3。
- [A03：High Availability 与 Failover](09-recovery/03-failover/README.md)：v0–v4。
