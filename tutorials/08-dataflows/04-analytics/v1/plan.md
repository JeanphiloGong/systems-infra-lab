# E04 v1 计划

前版缺口是 batch 重跑会重复计数。Pressure：同 batch 幂等且 revision 101 可修正。Naive：每次复制全部源行。Break：b1 重跑返回 0，再写 orders/customers b2，报告含 C2-corrected 55。Change：source,batch_id 主键、水位和 revision upsert。Check：运行 v1/replay，断言四条 provenance、重跑为 0、总行仍 100。Freeze：v1 fence。Still-lacks：远程联邦查询。Next：v2。
