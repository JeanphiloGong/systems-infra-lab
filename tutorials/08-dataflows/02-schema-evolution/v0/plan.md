# E02 v0：破坏性改名和必填字段 计划

Pressure / Naive / Break：旧客户端先成功写入 Ada。直接改名使旧 SELECT 抛 UndefinedColumn；这与新增必填字段是两种独立失败。重新建空表后增加无默认值的 NOT NULL full_name，旧形状 INSERT 抛 23502。最后用已有 Ada 行的表尝试相同 DDL，DDL 自身也抛 23502。每次检查真实异常，不把 DDL 失败当作旧写失败。

Change：本版完整实现和依赖列在同目录 tutorial.md；事件契约与 SQL 分开检查。

Check：`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[0]' -q` 提取本版全部围栏到临时目录执行，并逐项断言返回证据及数据库清理。

Freeze：本版 common.py 与 v0.py 围栏必须等于源文件，独立重放通过后交审核。

Still-lacks：受控专用数据库，不宣称无锁在线 DDL 或自动发布协调。

Next：新增可空字段并声明混合客户端读写策略。
