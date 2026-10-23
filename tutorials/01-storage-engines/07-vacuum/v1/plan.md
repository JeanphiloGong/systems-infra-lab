# S07 v1 计划

前置v0；目标普通VACUUM后删除空间可复用而文件通常不缩小。完整reuse.py作为checkpoint，真实PostgreSQL测试与独立重放；只创建并清理s07_ schema。不提交Git。


前置：本模块 v0。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. reuse.py 复用 v0.create_schema，记录 before，删除 800 行后执行 VACUUM (TRUNCATE FALSE)，再插回相同 800 个 ID。
2. 比较 before/cleaned/after 与最终 count=1000；解释空间可重用不等于返回操作系统。使用 autocommit 执行 VACUUM，保留唯一 schema 清理边界。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
