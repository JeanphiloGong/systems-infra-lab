# S07 v3 计划

前置v2；目标比较普通VACUUM与VACUUM FULL，后者需更强锁并重写关系。完整full.py作为checkpoint，真实PostgreSQL测试与独立重放；只创建并清理s07_ schema。不提交Git。


前置：本模块 v2。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. full.py 先 churn、普通 VACUUM 并记录 relation size；reader 持有读事务，worker 线程执行 VACUUM FULL，observer 通过 pg_blocking_pids 确认被 reader 阻塞。
2. 释放 reader 后等待 worker 完成，读取重写后大小并检查逻辑行仍为 1000。设置等待/SQL 超时防止无限挂住；不能用 sleep 代替锁已产生的证据。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
