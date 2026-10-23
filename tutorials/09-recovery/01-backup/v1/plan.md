# A01 v1 实施计划

v0 证明了备份可以还原，却没说明它覆盖哪个时间范围。现在生成 custom dump，随后在源库插入第三条记录；目标库恢复后应只有备份时的两条。这个反例说明备份文件不会自动包含之后的提交。

1. 明确输入和目标：把 dump 的格式从 plain 改为 custom，恢复命令相应改为 pg_restore；它不是可直接交给 psql 的 SQL 文件。先 dump，再 INSERT，再 restore，三个动作顺序固定，因此“第三条不出现”是可重复的快照边界，不依赖随机时间。
2. 实施依赖文件 common.py：沿用 v0 的五个 helper，不增加 PITR 逻辑。dump 默认 custom，v0 仍可显式传 plain。independent_database 继续负责隔离目标，备份后源库的新增记录不会被恢复流程删除。
3. 创建 v1.py 串起调用并执行 `uv run python labs/recovery/backup/v1.py`。验收：目标为 [(1,100),(2,100)]，源为 [(1,100),(2,100),(3,50)]。post_backup_row_excluded=true 只说明这次备份的快照边界；不提供按任意时间恢复。下一版准备物理基线和归档。

任务依次依赖；完整源码见 [正文](tutorial.md)，每版只增加本次实验所需函数。
