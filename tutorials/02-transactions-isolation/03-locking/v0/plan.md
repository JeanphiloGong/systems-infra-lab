# T03 v0 计划

先展示两个 autocommit 连接同时读取 10，随后各自写回 9；最终 9 证明一次扣减丢失。只保留两连接、单库存行和整数数量；下一版增加 version 条件。检查 `test_t03_locking.py` 使用真实数据库读取最终状态。


前置：模块 README 的运行环境。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. 建立 inventory(id=1,quantity=10)，两个 autocommit 连接先各 SELECT 再按读值写回 quantity-1；locking.py 入口只操作自己的 schema。
2. 最终 9 而非 8 是预期失败，直接读库核对，不能以线程完成或命令退出表示正确。下一版在同一个库存语义上增加 version 条件。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
