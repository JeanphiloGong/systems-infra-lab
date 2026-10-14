# 教程入口

这里列出已经建立正文的模块。版本是否已验收，以 [实施进度](../docs/progress.md) 为准。
完整的 40 模块路线见 [总规划](../docs/roadmap.md)，未列出的模块仍属于待完成范围。

## 已验收模块

- [S01：页与访问局部性，v0–v4](01-storage-engines/01-pages-and-locality/README.md)
- [T01：事务与隔离现象，v0–v4](02-transactions-isolation/01-isolation/README.md)
- [P01：分区路由，v0–v3](03-partitioning-scaling/01-routing/README.md)
- [P02：数据倾斜，v0–v3](03-partitioning-scaling/02-skew/README.md)
- [P03：在线迁移与重分片，v0–v4](03-partitioning-scaling/03-migration/README.md)
- [Q01：数据建模，v0–v3](04-query/01-modeling/README.md)
- [Q02：PostgreSQL 索引与 Index-Only Scan，v0–v3](04-query/02-indexes/README.md)
- [Q03：PostgreSQL 统计信息与执行计划，v0–v3](04-query/03-planner/README.md)
- [Q04：物化视图与缓存，v0–v4](04-query/04-derived/README.md)
- [F03：重试、断路器与 I/O 截止时间，v0–v4](02-traffic/03-retry/README.md)
- [D01：幂等与 Exactly-Once 边界，v0–v4](07-coordination/01-idempotency/README.md)
- [C02：选主、租约与 Split-Brain，v0–v4](06-consensus/02-leader-election/README.md)
- [C03：Raft 日志共识，v0–v8 已验收](06-consensus/03-raft/README.md)
- [D02：分布式锁与 Fencing，v0–v4](07-coordination/02-distributed-lock/README.md)
- [D03：分布式提交、2PC 与 3PC，v0–v4](07-coordination/03-distributed-commit/README.md)
- [D04：Saga 与补偿，v0–v4](07-coordination/04-saga/README.md)
- [R03：多主与地理复制，v0–v4](05-replication/03-multi-leader/README.md)
- [R04：物理复制与逻辑复制，v0–v3](05-replication/04-postgres/README.md)
- [S03：WAL 与恢复，v0–v5](01-storage-engines/03-wal-and-recovery/README.md)
- [S04：Bloom Filter，v0–v3](01-storage-engines/04-bloom-filter/README.md)
- [S05：LSM，v0–v7](01-storage-engines/05-lsm/README.md)
- [S06：列存与扫描，v0–v4](01-storage-engines/06-columnar-storage/README.md)
- [S07：Vacuum，v0–v4](01-storage-engines/07-vacuum/README.md)
- [T02：MVCC 与快照，v0–v3](02-transactions-isolation/02-mvcc/README.md)
- [S02：B+Tree，v0–v7](01-storage-engines/02-b-plus-tree/README.md)
- [T03：锁与并发控制，v0–v4](02-transactions-isolation/03-locking/README.md)
- [T04：可串行化与事务重试，v0–v3](02-transactions-isolation/04-serializability/README.md)

- [F01：连接池与事务池代理，v0–v3](01-storage-engines/07-connections/README.md)
- [F02：流量控制与背压，v0–v4](02-traffic/02-admission/README.md)
- [F04：惊群、请求合并与 stale-while-revalidate，v0–v3](02-traffic/04-herd/README.md)
- [E01：CDC 与投影同步，v0–v4](08-dataflows/01-cdc/README.md)
- [E02：Schema Evolution，v0–v3](08-dataflows/02-schema-evolution/README.md)
- [A02：检查点与有界恢复，v0–v3](09-recovery/02-checkpoint/README.md)
- [A03：High Availability 与 Failover，v0–v4](09-recovery/03-failover/README.md)
- [E03：Event Sourcing 与读模型，v0–v4](08-dataflows/03-events/README.md)
- [E04：联邦分析与数据仓库，v0–v3](08-dataflows/04-analytics/README.md)

路线图中的模块和版本均已完成当前验收闭环；进度表与对应复审证据记录验证边界。

## 当前状态

- [R01：主从复制，v0–v4 已验收](05-replication/01-leader-follower/README.md)：包含独立 writer/reader 进程恢复和确认策略边界。


路线图中的模块均已有教程入口；各版本是否已验收，以 [实施进度](../docs/progress.md) 和对应复审证据为准。


数据库教程先完成 [环境准备](../docs/environment.md)，纯文件及路由实验只需 Python 与 uv。
旧版本的完整代码保存在各版正文中，最新实验文件按模块演进。
- [A01：Backup 与 PITR，v0–v4 已验收](09-recovery/01-backup/README.md)：包含独立恢复、连续 WAL 区间、缺段失败和窗口测量。
