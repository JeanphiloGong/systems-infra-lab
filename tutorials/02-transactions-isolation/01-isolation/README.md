# T01：事务边界与隔离异常

从两个账户开始，亲眼观察“提交了什么”和“读到了什么”。需要 Python 函数、异常和基础 SQL 知识，不需要先理解 MVCC。

依次阅读 [v0](v0/tutorial.md)、[v1](v1/tutorial.md)、[v2](v2/tutorial.md)、[v3](v3/tutorial.md)、[v4](v4/tutorial.md)。
代码创建于 `labs/transactions/isolation/`，测试创建于 `tests/transactions/isolation/`；所有命令在仓库根目录运行。首次学习时文件不存在，按各版正文逐步创建；已有练习则在核对前版内容后继续修改。

本模块使用真实 PostgreSQL，连接来自 `SYSTEMS_LAB_DATABASE_URL`。只指向仓库创建的临时测试实例，实验会创建并删除 `t01_` 前缀的独立 schema。
环境启动见 [环境准备](../../../docs/environment.md)；依赖由 `uv sync --locked` 安装。v0 给出 SQL、演示脚本、转账函数和首个测试文件，v1 创建双连接测试，v2-v4 在已有文件上追加。每版完整代码与明确的追加位置共同确定当前检查点；预先生成的最终答案只保存在本地 `reference` 分支。

最终能解释 ACID、Dirty Read、Read Skew、Phantom Read；不会把没有脏读等同于可串行化，也不会声称一次查询验证了断电持久性。
