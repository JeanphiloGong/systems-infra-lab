# Q03 v2 计划

前版缺口是独立选择率相乘无法描述相关字段。Pressure：相关 predicate 的实际行数不随单列估算正确。Naive：只收集普通统计。Break：比较相关数据上的计划前后估算误差。Change：收集相关统计并重新规划。Check：运行 postgres.py 与 replay `--version 2`，断言结果不变且 post-statistics 误差更小。Freeze：v2 fence。Still-lacks：join 与内存成本。Next：v3。
