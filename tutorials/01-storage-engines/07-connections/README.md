# F01：连接建立、复用与泄漏

路线：v0 PostgreSQL 直接连接 → v1 官方 psycopg_pool 有界复用 → v2 异常/超时泄漏边界 → v3 会话状态与事务池限制。真实数据库连接由 `SYSTEMS_LAB_DATABASE_URL` 提供；没有该变量时集成测试跳过。
