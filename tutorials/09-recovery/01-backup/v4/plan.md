# A01 v4 计划

前版缺口是无法证明任意 recovery target 已到达。Pressure：缺失 WAL 必须阻止假成功。Naive：在目标前停止也返回可用。Break：删除 archive segment 并请求更晚 target。Change：target 校验与明确失败。Check：v4 与 replay，断言 `missing_archive_detected=True`、`recovery_failed=True`。Freeze：v4 fence。Still-lacks：远端归档耐久性和真实 RPO。Next：与 failover 结合。
