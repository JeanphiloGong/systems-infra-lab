# S07 v2 计划

前置v1；目标长REPEATABLE READ快照仍读旧值，VACUUM不能回收它所需版本。完整snapshot.py作为checkpoint，真实PostgreSQL测试与独立重放；只创建并清理s07_ schema。不提交Git。


前置：本模块 v1。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. snapshot.py 使用两个连接且都设置到同一临时 schema；reader 在 RR 事务第一次 SELECT 建立快照，writer 更新全部行并 VACUUM。
2. 断言 reader 旧快照总和=0、writer 当前总和=1000，结束 reader 事务后重读=1000。再次 VACUUM 说明快照释放边界；不从统计近似值推断具体 tuple 被回收。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
