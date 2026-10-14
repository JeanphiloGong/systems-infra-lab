# A01 v0 计划

Pressure / Naive / Break：逻辑 plain dump 必须导入独立临时数据库；旧实现原地 DROP/restore，无法证明灾难目标隔离。Break 是在源库保留两行时创建独立目标并导入备份。

Change：只增加独立 CREATE DATABASE 目标和恢复后约束验证。Check：A01_DATABASE_URL 指向专用 PostgreSQL 时运行 `uv run pytest 'tests/recovery/backup/test_a01_replay.py::test_real_postgres_backup_restore[0]' -q`；断言 rows=[(1,100),(2,100)]、columns 的 id/balance 均 NOT NULL、duplicate SQLSTATE=23505、NULL SQLSTATE=23502、source_preserved=True。

Freeze：`tutorials/09-recovery/01-backup/v0/tutorial.md` 的 common.py/v0.py 围栏必须逐字等于源文件；独立临时目录重放后交审核。

Still-lacks：custom archive、WAL/PITR、远程归档和生产 SLA 尚未覆盖。

Next：v1 将 custom dump 恢复到独立目标并验证备份时点边界。
