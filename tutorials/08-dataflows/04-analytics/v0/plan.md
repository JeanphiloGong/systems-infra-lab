# E04 v0 计划

Pressure：orders 与 customers 两源要生成带来源报表。Naive：直接合并而不记录 provenance。Break：加载 batch b1，报表应为 C1/C2/C3 金额 10/20/30。Change：每源独立事务和 source_batch 记录。Check：`E04_LIVE=1 uv run python -m labs.dataflows.analytics.v0`；replay，断言两源各 100 行和 provenance b1。Freeze：v0 fence。Still-lacks：重复批次与迟到修正。Next：v1。
