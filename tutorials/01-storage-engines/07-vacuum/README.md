# S07：PostgreSQL MVCC 版本回收与 Vacuum

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

本模块只针对仓库固定的 PostgreSQL 版本。按 v0-v4 观察逻辑行、死元组、普通 `VACUUM`、长事务、`VACUUM FULL` 和 autovacuum；统计是近似观测，不推广到其他数据库。
