# S02：B+Tree 索引

场景是商品主键点查与范围分页。路线：[v0 有序数组](v0/tutorial.md) → v1 单叶页 → v2 叶分裂 → v3 内部递归分裂 → v4 叶链扫描 → v5 页编码 → v6 删除合并 → v7 总结。代码演进保留在 `labs/storage/bplus_tree/`，历史代码只在教程 checkpoint 中；v5 前不涉及磁盘。
