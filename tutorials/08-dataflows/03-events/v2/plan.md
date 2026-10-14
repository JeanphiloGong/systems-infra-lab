# E03 v2 Tutorial Plan

v2：并发追加需要 expected version.

Prerequisite: E03 v1. Scenario: trace order state changes and rebuild a query projection.

Pressure: 两个命令都读到版本1时，只有一个能把事件写成版本2。BEGIN IMMEDIATE 加实际查询版本，旧命令返回 Conflict，不能用最后写入者覆盖。

Implementation: complete source checkpoint. Acceptance: run the script, extract the fence and execute the assertions. Invariants: the same event sequence rebuilds the same state; duplicate projection delivery has no duplicate effect; replay does not send external side effects.

Next: 测试先追加 placed，再让 paid 与 cancelled 都使用 expected=1；两个并发 writer 中一个成功、另一个冲突，版本为 `[1,2]`。胜者可能是 paid 或 cancelled；重放保留实际获胜者，不承诺提交顺序决定胜者。

