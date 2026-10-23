# T03 v2 写作计划

前置v1。目标读取期间持有行锁，场景和模型见正文开头。任务1：从前版缺口建立输入和机制，规模M。任务2：解释调度/失败/资源边界，依赖任务1，规模M。任务3：完整row_lock.py checkpoint及真实运行（v4纯模型），依赖任务2，规模M。每步目标为同目录tutorial.md对应章节。测试检查具体返回与最终状态，完整代码从Markdown提取独立重放；不提交Git，独立review后验收。


前置：本模块 v1。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. row_lock.py 将 SELECT FOR UPDATE 与扣减放进同一显式事务，另一连接尝试更新该行；observer 通过 pg_blocking_pids 确认 owner 正在阻塞 waiter，不用 sleep 猜测。
2. 持锁连接提交后 waiter 的等待结束并读取新值继续扣减，验证库存实际结果和事务释放。异常路径回滚，避免连接留在 aborted 状态；使用当前 schema 初始化并在 finally 清理。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
