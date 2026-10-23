# T02 v3 计划

前置 v2，仍用真实 RR。目标让两人同时下班的调度留下至少1人；采用单排班组 guard 行更新作为共享冲突点，冲突事务必须回滚后重做整个读取/决策。不是切换 Serializable，也不是通用锁服务。

1. tutorial.md 第一步，规模 S，guard.sql checkpoint，解释不同行缺乏共同写冲突，新增唯一 guard 行，不改变医生 schema。
2. 第二步规模 M，protected_schedule 初始冲突片段 checkpoint；旧快照 second 先建立，first 更新 guard+下班提交，second 更新 guard 得40001。验收冲突明确抛出，不是依赖线程等待。
3. 第三步规模 M，patch 新事务完整重读并判定；返回 conflict1/allowed false/remaining1。仅本确定性实验重试一次，无泛化重试承诺。
4. 最后完整 protected.py checkpoint，依赖前三步，规模 M。真实 SQL 加最终行状态测试，独立正文重放。解释所有写者必须遵守协议、争用成本、重试责任，不断言任意跨行约束自动安全。无提交。
