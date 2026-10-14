# A01 v1 计划

前版缺口是 plain SQL 不表达自包含归档。Pressure：恢复必须只得到备份时点。Naive：恢复后误把备份后的行也算入。Break：备份后插入一行再恢复。Change：custom-format dump。Check：运行 v1 与 replay，断言 `rows_at_backup=2`、`post_backup_row_excluded=True`。Freeze：v1 fence。Still-lacks：归档损坏。Next：v2。
