# Q03 v3 计划

前版缺口是单表估算没有展示 join 和临时 I/O。Pressure：相同结果可能选择不同 join，低 work_mem 会 spill。Naive：把总 cost 或耗时当唯一资源指标。Break：EXPLAIN 比较 Nested Loop/Hash Join 与 Disk/Memory sort。Change：读取 operator、buffer、temp block 指标。Check：postgres.py 与 replay `--version 3`，断言结果相等、join 节点和 spill 类型。Freeze：v3 fence。Still-lacks：生产 workload 回归。Next：计划回归监控。
