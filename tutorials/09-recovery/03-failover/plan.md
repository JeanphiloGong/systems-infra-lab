# A03：High Availability 与 Failover 计划

前置：R02 一致性、C02 选主、A01 备份。版本共享一个完整模型和一个真实 Patroni probe，但每版只把一个失败压力作为教学主线；共享代码中其他分支是后续版本依赖，不计为当前版新增能力。

## 核心场景与不变量

主库故障时，已确认写入的 RPO、客户端重新成功写入的 RTO、旧主 fencing、重建 rejoin 与计划回切必须分别观测。RPO=0 只对故障前明确等待副本追平的样本成立。旧主进程存活不等于可继续提供写入；网络分区不能单独证明节点死亡。

## 版本任务

- v0：用双节点逻辑模型停止主库，记录故障注入、客户端不可写窗口和副本已有数据；分别定义 RTO 起止与 RPO 集合，明确模型不测真实 PostgreSQL。
- v1：手动 promotion；确认副本成为写入目标，说明旧主隔离由操作者负责，验证旧主未 fencing 时存在双主窗口；连接真实 promotion probe。
- v2：Patroni/etcd 自动检测与 promotion；记录 ttl、loop_wait、retry_timeout、客户端探测间隔、RTO 与尝试次数，分析网络延迟/DCS 不可达/长暂停误判，以及停服务避免双写的取舍。
- v3：网络隔离但保持旧容器存活；验证旧主本地写入被拒绝、旧进程状态与新主写入同时成立，明确 Patroni fencing 不等于硬件 STONITH。
- v4：恢复网络后用 Patroni reinitialize/basebackup 重建旧主，确认新记录追平，再执行 switchover 回切并测量 cutback；说明重建期间不可用和客户端幂等边界。

每版冻结：完整正文、完整当前 fences、运行/清理命令和失败限制。v2-v4 live probe 是同一完整故障轨迹的不同观察重点，必须标注共享实现，不把一次 probe 重复命名为五个独立实现。
