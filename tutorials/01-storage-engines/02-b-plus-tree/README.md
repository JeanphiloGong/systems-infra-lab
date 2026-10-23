# S02：B+Tree 索引

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

场景是商品主键点查与范围分页。路线：[v0 有序数组](v0/tutorial.md) → v1 单叶页 → v2 叶分裂 → v3 内部递归分裂 → v4 叶链扫描 → v5 页编码 → v6 删除合并 → v7 总结。按正文逐版在此路径创建代码：`labs/storage/bplus_tree/`，历史代码只在教程 checkpoint 中；v5 前不涉及磁盘。
