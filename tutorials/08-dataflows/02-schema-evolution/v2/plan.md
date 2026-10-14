# E02 v2：最终同步与真实进程回填 计划

Pressure / Naive / Break：本版运行前已排空旧写；实验没有实现部署协调器。新写仍双写，ID 5 的两个字段都是 Protected by new client。为重现 v1 留下的过期 full_name，ID 1 先放 stale old value；迁移准备将不一致值置空，随后按权威 name 回填。主键游标前不得再出现旧写或新增 NULL，否则只扫尾部会漏行。第一批两行数据与游标同事务提交后进程退出 17；第二批提交前退出 19，验证行 3/4 和游标均回滚。恢复 worker 通过 stdout 返回实际处理数 2，重复 worker 返回 0；不使用预填常量。seed/reset 清理实验表和 checkpoint，worker 不 reset。整个实验在同一数据库运行两次，和一个实验内恢复是两项不同检查。

Change：本版完整实现和依赖列在同目录 tutorial.md；事件契约与 SQL 分开检查。

Check：`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[2]' -q` 提取本版全部围栏到临时目录执行，并逐项断言返回证据及数据库清理。

Freeze：本版 common.py 与 v2.py 围栏必须等于源文件，独立重放通过后交审核。

Still-lacks：受控专用数据库，不宣称无锁在线 DDL 或自动发布协调。

Next：在旧协议退出和无 NULL 的双重门槛通过后收紧 schema。
