# A01 v2 实施计划

v1 的逻辑备份只能恢复其快照。要研究之后的时间点，下一步需要整个集群的物理基线与连续 WAL。本版先实际破坏一份逻辑 dump，证明命令失败不能当恢复成功，再生成 base backup 并核查已知 LSN 区间的归档文件。

1. 明确输入和目标：截断 dump 后使用 pg_restore --exit-on-error --single-transaction 恢复到独立数据库；断言失败且 accounts 不存在，说明失败恢复没有被接纳，也没有污染源表。随后 pg_basebackup -Fp -Xs 复制物理数据目录并带上备份期间必要 WAL；它不是 pg_dump 的另一种输出格式。
2. 实施依赖文件 common.py：保留 v1 的 helper，新增 create_base_backup 与 wait_archived_segments。后者把起止 LSN 转成段名，等待区间内每段实际存在且大小为 16 MiB；区间枚举只支持本实验同 timeline、未跨 segment 编号回绕的小区间，不是通用 WAL 校验工具。文件存在与完整大小仍不等于内容可恢复，v3 会启动真正恢复实例。
3. 创建 v2.py 串起调用并执行 `uv run python labs/recovery/backup/v2.py`。验收：损坏 dump 的恢复应失败且目标没有 accounts；PG_VERSION 存在，required_wal_segments 非空且每段 16 MiB。此时仍不能宣称 PITR 成功，也没有校验每段内容；下一版由真实恢复进程解释它们。

任务依次依赖；完整源码见 [正文](tutorial.md)，每版只增加本次实验所需函数。
