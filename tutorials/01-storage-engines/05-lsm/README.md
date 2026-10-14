# S05：LSM、Compaction 与写放大

当前可运行检查点：[v0](v0/tutorial.md) 内存映射、[v1](v1/tutorial.md) 单个不可变SSTable。代码在 `labs/storage/lsm/`；从仓库根目录 `uv sync --locked` 后运行。

后续v2-v7按[总路线](../../../docs/roadmap.md)增加多文件版本、删除标记、合并、清单、WAL与过滤器、放大指标，尚未在这两个检查点实现。S04可以使用本模块v1真实SSTable集成过滤，不要求提前实现完整LSM。
