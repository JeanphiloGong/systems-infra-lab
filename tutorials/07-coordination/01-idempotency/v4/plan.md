# D01 v4 计划

前版缺口是本地事务不能撤销邮件。Pressure：外部效果后丢响应会重复发送。Naive：服务只去重订单，不理解 receiver。Break：`response_lost=True` 后分别用支持/不支持 key 的 MailReceiver 重试。Change：接收方 key 去重并明确 exactly-once scope。Check：`uv run python labs/coordination/idempotency/v4.py` 和 replay 断言 aware deliveries 单次。Freeze：v4 fence。Still-lacks：无 outbox、跨服务事务。Next：durable dispatch。
