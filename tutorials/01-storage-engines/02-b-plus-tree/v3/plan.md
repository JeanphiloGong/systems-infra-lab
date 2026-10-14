# S02 v3 写作计划

叶页增多后，根的分隔键也有容量。内部节点满时提升中间分隔键，左右两组继续保持子树范围；随机插入后逐步验证父子边界和叶深度。

目标是完整重放 tree.py，测试覆盖边界和结构不变量。依赖上一版本；本版不引入磁盘或 WAL。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v2](../v2/tutorial.md)。容量 3 的根已有三个叶子，继续插入 80 会遇到 internal split belongs to v3。叶分裂本身已经正确，缺少的是父节点也可能溢出的处理。 上一版直接把叶分裂插入唯一根，多一层后就不能假设叶的父亲是根。改成递归 _insert(node,key,value)：没有分裂返回 None；发生分裂返回 (分隔键,新右节点)。调用栈天然知道父节点，避免为了每次分裂遍历整棵树寻找父亲。
- **Change:** # S02 v3：让分裂沿插入路径向上传播; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

