# A03 v1：人工提升与旧主隔离

依赖 v0 的 HA 模型和 R04 v0 的 Compose、init.sql、replication.sh、standby.sh。目标在真实 PostgreSQL 中保留已回放行并让备库接受新写。

1. 保留模型实验并解释客户端目标与可写角色是两件事。
2. 正文新增完整 postgres_probe.py：prepare 确认主备角色，写 before-promotion，等待备库 replay LSN 并读回该行。
3. 用 R04 Compose 停止旧主后执行 promote；pg_promote 完成后确认不再 recovery，写 after-promotion 并读回两条记录。
4. 使用全新专用卷执行 prepare→stop primary→promote，结束 down -v。不在仍被其他实验使用的 R04 卷上执行，也不尝试把已提升节点作为旧备库直接重用。

验收：两行都存在，promoted=true；本版不实现自动路由、生产 fencing 或自动故障检测。调用与完整代码见 [正文](tutorial.md)。
