# D01 v0 计划

场景：支付请求在创建订单后丢失响应，客户端重试。Pressure：一个逻辑请求应只有一个持久效果。Naive：接口没有 request key。Break：两次 `create_order("ada")` 确定性输出 `order-1`、`order-2`。Change：冻结无去重基线。Check：`uv run python labs/coordination/idempotency/v0.py`；`uv run pytest tests/coordination/idempotency/test_replay_d01.py -q`，断言两个 ID。Freeze：v0 完整 fence 与输出。Still-lacks：无 key、原子领取、持久化。Next：v1 领取 request key。
