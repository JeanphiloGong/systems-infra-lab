# T03 v1 计划

在 v0 丢失更新后保存同一 `(quantity, version)` 读取结果。第一次条件 UPDATE 成功并递增 version；第二次使用旧 version 得到 rowcount 0。测试必须检查最终 quantity=9、version=1 及冲突明确返回。下一版用行锁保护读取。


前置：本模块 v0。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. schema.sql 增加 version 默认 0；两次读取同一个 (quantity=10,version=0)，UPDATE 同时检查 id/version，并使 quantity 减少且 version 增加。
2. 第一条 rowcount=1，第二条=0；检查最终 quantity=9/version=1。零行更新表示需要重读决策，不能盲目当成功。下一版对比持锁读取。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
