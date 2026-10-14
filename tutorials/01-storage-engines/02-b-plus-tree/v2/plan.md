# S02 v2 写作计划

容量 3 的叶页放入第四个新键时，单页已经不能保持容量。把有序项从中间切成左右两页，用右页最小键作为父分隔键；根叶变为两子节点。等号必须走右子树，因为分隔键属于右叶。

目标是完整重放 tree.py，测试覆盖边界和结构不变量。依赖上一版本；本版不引入磁盘或 WAL。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v1](../v1/tutorial.md)。容量为 3 的叶中已有 10、20、30，再插入 40 被拒绝。我们要保留全部四条，同时让每页容量仍不超过 3。本版只允许两层树：一个内部根和若干叶。内部根满后的递归分裂留给下一篇。 先把新记录按顺序插入，四条按中点分成 [10,20] 和 [30,40]。父节点的分隔键使用右页最小键 30，30 的值仍留在右叶；这体现 B+Tree 的值在叶中的选择。
- **Change:** # S02 v2：叶页分裂，根开始指路; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

