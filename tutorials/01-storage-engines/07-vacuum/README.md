# S07：PostgreSQL MVCC 版本回收与 Vacuum

本模块只针对仓库固定的 PostgreSQL 版本。按 v0-v4 观察逻辑行、死元组、普通 `VACUUM`、长事务、`VACUUM FULL` 和 autovacuum；统计是近似观测，不推广到其他数据库。
