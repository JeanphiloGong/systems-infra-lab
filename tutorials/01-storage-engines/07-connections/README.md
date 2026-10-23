# F01：连接建立、复用与泄漏

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

路线：v0 PostgreSQL 直接连接 → v1 官方 psycopg_pool 有界复用 → v2 异常/超时泄漏边界 → v3 会话状态与事务池限制。真实数据库连接由 `SYSTEMS_LAB_DATABASE_URL` 提供；没有该变量时集成测试跳过。v3 的 PgBouncer 启动必须组合 `infra/postgres.compose.yaml` 与 `infra/pgbouncer.compose.yaml`，因为后者依赖前者的 `postgres` 服务。
