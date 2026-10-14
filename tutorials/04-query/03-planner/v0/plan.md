# Q03 v0 计划

Pressure：表从 20 增长到 100000 行，最佳访问路径变化。Naive：凭直觉假定同一 predicate 永远同一扫描。Break：PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` 对两种规模：small 含 Seq Scan，large 含 Index 节点。Change：只引入真实 planner 测量。Check：`uv run python postgres.py`；`uv run python tests/query/planner/replay_q03.py --version 0`，断言返回行与节点。Freeze：postgres.py fence。Still-lacks：统计信息漂移。Next：v1。
