# D01 v1 计划

前版缺口是无键重试双创建。Pressure：重复 key 必须共用一个效果。Naive：把 key 检查和创建分开仍会竞态。Break：连续两次 `request-1`。Change：锁内验证 key、检查响应、创建订单并保存响应。Check：`uv run python labs/coordination/idempotency/v1.py` 输出 `order-1` 两次，并运行 D01 replay。Freeze：v1 fence 与输出。Still-lacks：进程锁不可恢复。Next：v2 事务化业务和去重记录。
