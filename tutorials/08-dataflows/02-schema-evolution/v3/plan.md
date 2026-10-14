# E02 v3：退休门槛、必填约束和最终协议 计划

Pressure / Naive / Break：contract 在同一事务内锁表并检查 migration_clients 中旧协议全部 retired，以及 full_name 无 NULL。实验先证明活跃旧客户端阻止 contraction，再证明退休后仍有 NULL 也阻止；补齐后才设置 NOT NULL、删 name、删 checkpoint 和 client registry。注册表代表受控发布状态，实际环境还需防止退休客户端重新上线。NULL INSERT、省略字段 INSERT、NULL UPDATE 分别必须得到 23502；新协议 Linus 写读成功，旧 SELECT 失败。information_schema 和 to_regclass 检查实际列、约束及过渡表消失。最终 event consumer 只读取 full_name，旧 name-only、缺字段、NULL、空字符串都拒绝；v1 的旧字段 fallback 留在历史版本，不由最终版导入。

Change：本版完整实现和依赖列在同目录 tutorial.md；事件契约与 SQL 分开检查。

Check：`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[3]' -q` 提取本版全部围栏到临时目录执行，并逐项断言返回证据及数据库清理。

Freeze：本版 common.py 与 v3.py 围栏必须等于源文件，独立重放通过后交审核。

Still-lacks：受控专用数据库，不宣称无锁在线 DDL 或自动发布协调。

Next：用独立环境验证发布协调和业务客户端退役，不把本实验当作自动部署平台。
