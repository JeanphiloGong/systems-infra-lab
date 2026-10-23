# D04 v4：同时处理重复订单效果键

这是按订单隔离的效果登记切片，接续 v3 对 Saga 隔离不足的讨论，不声称已整合完整补偿工作流。

1. Orders 使用 (order_id,name) 主键；同一个实例的查询/插入/commit 由 Lock 保护。
2. 八线程用 Barrier(8) 同时起步，两个订单各调用四次 reserve；汇总返回值恰好两次 True，数据库每单一条 done。
3. 执行 `uv run python labs/coordination/saga/v4.py`，线程池退出后再 snapshot 并关闭连接。检查只证明同实例多线程竞争，不能推出跨进程或真实库存只扣一次。

文件与断言见 [正文](tutorial.md)。
