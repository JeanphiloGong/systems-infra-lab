# D01 v2 计划

前版缺口是内存锁和业务写入无法跨崩溃持久化。Pressure：订单与 request record 同成败。Naive：`before_commit` 崩溃留下不一致，提交后丢响应应可安全重试。Break：`crash_at="after_commit"` 后重试。Change：同一事务模型原子保存 Record 和订单。Check：`uv run python labs/coordination/idempotency/v2.py` 返回 `order-1` 且 store 长度为 1；运行 replay。Freeze：v2 fence。Still-lacks：无 payload 绑定、状态和 retention。Next：v3。
