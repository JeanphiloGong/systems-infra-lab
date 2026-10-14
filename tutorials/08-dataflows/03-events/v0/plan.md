# E03 v0 Tutorial Plan

v0：当前状态没有来路.

Prerequisite: D01, Q04 and E02. Scenario: trace order state changes and rebuild a query projection.

Pressure: 仪表盘只保留 order_id -> paid。这个值能回答当前状态，却不能解释何时下单、何时付款，也不能重建审计轨迹。先把限制写成可运行基线。

Implementation: complete source checkpoint. Acceptance: run the script, extract the fence and execute the assertions. Invariants: the same event sequence rebuilds the same state; duplicate projection delivery has no duplicate effect; replay does not send external side effects.

Next: 运行 current_state() 并断言没有历史；下一版把变化写成事实事件。

