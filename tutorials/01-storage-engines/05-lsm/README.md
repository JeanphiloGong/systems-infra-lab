# S05：LSM、Compaction 与写放大

在 main 逐版创建 `labs/storage/lsm/` 文件，完整代码写在正文中。参考分支是可选对照；不要把它复制回练习目录。

学习顺序：[v0](v0/tutorial.md) 内存映射 → [v1](v1/tutorial.md) 单个 SSTable → [v2](v2/tutorial.md) 多表查询 → [v3](v3/tutorial.md) 删除标记 → [v4](v4/tutorial.md) 合并 → [v5](v5/tutorial.md) MANIFEST → [v6](v6/tutorial.md) 接入 WAL/Bloom → [v7](v7/tutorial.md) 全量与两层合并。

v6 依赖 S03 v1 的帧格式与 S04 v3 的过滤表；v7 继续修改同一个 RecoveredStore，所有版本保留 JSONL 和删除语义。最终验证包含重启、损坏拒绝、发布故障和真实文件字节计数。两层模型没有 L2、后台合并或安全回收，边界见正文。
