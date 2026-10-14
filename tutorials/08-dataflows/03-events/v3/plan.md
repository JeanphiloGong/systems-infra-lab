# E03 v3 Tutorial Plan

v3：投影可以落后、重复、重建.

Prerequisite: E03 v2. Scenario: trace order state changes and rebuild a query projection.

Pressure: 读模型是查询优化，不是事实来源。消费位置 (stream,version) 放在同一 SQLite 事务里；重复事件只命中 processed，落后投影删除后从完整事件列表重建。

Implementation: complete source checkpoint. Acceptance: run the script, extract the fence and execute the assertions. Invariants: the same event sequence rebuilds the same state; duplicate projection delivery has no duplicate effect; replay does not send external side effects.

Next: 三条事件首次应用，第二条重复不产生写入；另一个投影只读前两条再完整 rebuild，得到 shipped。

