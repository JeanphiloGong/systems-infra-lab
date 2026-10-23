# A01 v0 实施计划

你准备修改账户表，想先备份，以便出错后恢复。仅生成 SQL 文件还不算成功：它可能不能导入，或者导入后约束丢失。本版把两条账户记录导出，再恢复到另一个临时数据库，验证数据、主键与 NOT NULL，源库保持原样。

1. 明确输入和目标：`pg_dump --format=plain --table=accounts` 读取源库快照，产物是 SQL；`psql --set=ON_ERROR_STOP=1 --file=...` 在独立目标执行这些 SQL。开启 ON_ERROR_STOP 避免中间语句失败却继续到最后。成功退出后仍需查询目标，不能只检查文件存在。
2. 实施依赖文件 common.py：common.py 只放当前调用需要的操作：connect 连接 A01 源库；seed 建立两条输入；dump/command 调用真实客户端并检查退出码；independent_database 创建随机目标库，在 finally 删除它。后者拥有目标库生命周期，脚本拥有临时 dump 文件。seed 会重建实验源表，因此 DSN 必须指向 A01 专用实例。当前没有 WAL 或物理恢复 helper。
3. 创建 v0.py 串起调用并执行 `uv run python labs/recovery/backup/v0.py`。验收：输出 rows_restored=2、source_preserved=true，列约束为 NO/NO；重复主键与 NULL 写入分别返回 SQLSTATE 23505/23502。异常后调用 rollback，才能继续下一次约束检查。成功后临时目标库和 dump 文件被清理。下一版比较备份后的新提交。

任务依次依赖；完整源码见 [正文](tutorial.md)，每版只增加本次实验所需函数。
