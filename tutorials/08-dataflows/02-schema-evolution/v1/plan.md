# E02 v1：双客户端发布与独立事件契约 计划

Pressure / Naive / Break：旧、新客户端使用两个真实连接。先以 COALESCE 读取 full_name=NULL 的历史 Ada，然后检查旧 INSERT -> 新读、新双写 -> 旧读、新 INSERT -> 旧读。同一行被新客户端写 Ada Lovelace 后，旧客户端只写 name=Grace；COALESCE 仍读 Ada Lovelace，证明简单 fallback 不安全。迁移窗口 name 是权威字段：新客户端双写，但读取 name；旧写后新读因此得到 Grace。切换 full_name 之前必须排空旧写并最终同步，不能在仍有旧写时切换。事件是另一条契约：old/transition/new 三种 payload 对 old/new 两类 consumer 构成六格矩阵。旧 consumer 拒绝 new-only；新 consumer 暂时接受旧 name；缺两个字段明确拒绝。此函数可以完全不连接数据库运行，SQL 兼容不能替它背书。

Change：本版完整实现和依赖列在同目录 tutorial.md；事件契约与 SQL 分开检查。

Check：`E02_DATABASE_URL='postgresql://e02:e02_local_only@127.0.0.1:55451/e02' uv run pytest 'tests/dataflows/schema_evolution/test_e02_replay.py::test_real_postgres_schema_evolution[1]' -q` 提取本版全部围栏到临时目录执行，并逐项断言返回证据及数据库清理。

Freeze：本版 common.py 与 v1.py 围栏必须等于源文件，独立重放通过后交审核。

Still-lacks：受控专用数据库，不宣称无锁在线 DDL 或自动发布协调。

Next：排空旧写后修复不一致字段并可恢复回填。
