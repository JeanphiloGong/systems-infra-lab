# A01 v2 计划

前版缺口是归档损坏可能被当作成功。Pressure：坏备份必须明确失败。Naive：接受 partial restore。Break：确定性修改 archive 后 restore。Change：损坏检测与拒绝部分结果。Check：v2 与 replay，断言 `corruption_detected=True`、`partial_restore_accepted=False`。Freeze：v2 fence。Still-lacks：物理备份/WAL。Next：v3。
