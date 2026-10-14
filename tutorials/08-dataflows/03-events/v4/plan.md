# E03 v4 Tutorial Plan

v4：旧事件升级，重放不发信.

Prerequisite: E03 v3. Scenario: trace order state changes and rebuild a query projection.

Pressure: 事件格式会演进，旧 OrderPlaced 没有 currency 时由 upcast 补 USD。rebuild 只计算状态；只有显式 dispatch_new 的新事件才交给发送函数，避免重建再次扣款或发邮件。

Implementation: complete source checkpoint. Acceptance: run the script, extract the fence and execute the assertions. Invariants: the same event sequence rebuilds the same state; duplicate projection delivery has no duplicate effect; replay does not send external side effects.

Next: 旧三条事件重放为 shipped，发送列表仍为空；显式新事件发送一次。跨版本事件契约和外部幂等仍是生产边界。

