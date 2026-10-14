# A01 v3 计划

前版缺口是逻辑备份无法恢复删除前任意时点。Pressure：base backup 后写 WAL，再恢复删除前目标。Naive：只 restore 当前 dump。Break：目标行恢复且后续行不存在。Change：physical base backup + WAL replay。Check：v3 与 replay，断言 target `1:100,2:100`、current `1:100,3:300`。Freeze：v3 fence。Still-lacks：缺失 WAL。Next：v4。
