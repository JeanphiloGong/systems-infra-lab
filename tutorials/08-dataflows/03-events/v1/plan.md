# E03 v1 Tutorial Plan

v1：事件流成为事实来源.

Prerequisite: E03 v0. Scenario: trace order state changes and rebuild a query projection.

Pressure: 一个订单的事件按流版本追加，重放器从 new 开始应用有限状态转换。非法的 shipped -> paid 必须拒绝，否则历史损坏会被静默接受。

Implementation: complete source checkpoint. Acceptance: run the script, extract the fence and execute the assertions. Invariants: the same event sequence rebuilds the same state; duplicate projection delivery has no duplicate effect; replay does not send external side effects.

Next: EventStore 使用 SQLite PRIMARY KEY(stream,version)，read 按版本排序；replay 只改变内存状态，不发送副作用。

