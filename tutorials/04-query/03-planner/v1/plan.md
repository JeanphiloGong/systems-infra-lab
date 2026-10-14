# Q03 v1 计划

前版缺口是 planner 只能依赖旧统计。Pressure：90,000 行改成 user_id=7 后估算过时。Naive：不 ANALYZE 仍相信索引计划。Break：更新后比较 stale 与 fresh。Change：显式 ANALYZE。Check：`uv run python postgres.py`；replay `--version 1`，断言 stale 为 Index、analyzed 为 Seq Scan 且估算误差缩小。Freeze：v1 fence。Still-lacks：相关列。Next：v2。
