# E04 v2 计划

前版缺口是复制后才查询，无法观察传输成本。Pressure：west predicate 应只传 3 行而 full scan 传 200。Naive：无谓拉取两源全表。Break：postgres_fdw selective 与 full query 对比。Change：foreign servers 和 predicate pushdown。Check：运行 v2/replay，断言 C1-C3、每源 scanned 100/transferred 3、full transferred 200。Freeze：v2 fence。Still-lacks：源漂移与停机。Next：v3。
