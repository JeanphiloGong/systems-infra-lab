# A01 v3 实施计划

v2 有物理基线与 WAL，但还没证明能找回误删记录。现在在 base backup 完成后记录服务器时间，然后删除 id=2、插入 id=3。恢复实例必须停在误删前，读出 1/2；源库同时仍是 1/3。

1. 明确输入和目标：目标时间必须晚于 base backup 可恢复的起点，又早于 DELETE 提交。用数据库 clock_timestamp 获取目标，1.1 秒间隔只用于把教学事件时间分开，不作为复制完成判据。再用 LSN 区间等待归档实际落地，而不是睡一会就假定成功。
2. 实施依赖文件 common.py：在 v2 上新增 docker 和 recover_at。recover_at 写 recovery.signal 与 recovery_target_time，启动只挂载该 base/归档的恢复容器，通过 docker exec 轮询暂停状态与查询结果；不需要加入其他 Compose 网络。完成后删除恢复容器。目标表结果与源库结果必须分别查询，防止误把源库当恢复库。
3. 创建 v3.py 串起调用并执行 `uv run python labs/recovery/backup/v3.py`。验收：恢复目标输出 1:100,2:100，当前源库为 1:100,3:300，且恢复已暂停在目标处。缺 WAL、权限或数据库启动错误都不能算成功。只测本机专用实例，不测跨主机恢复或应用重新接流量。

任务依次依赖；完整源码见 [正文](tutorial.md)，每版只增加本次实验所需函数。
