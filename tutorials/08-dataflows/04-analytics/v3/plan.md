# E04 v3 计划

前版缺口是两源独立提交和 source outage。Pressure：新 customer 尚未到达时出现 orphan，停源时 federated read 失败而 copied warehouse 仍可读。Naive：把联邦查询当稳定报表。Break：orders 引用 101、随后 customer 101 到达，再 stop customers。Change：provenance 水位和本地 copied read model。Check：运行 v3/replay，断言 orphan `[(1,)]`、收敛 C1new、停源错误、最终 copied report 正常。Freeze：v3 fence。Still-lacks：CDC/多仓库协调。Next：生产一致性控制。
