# S02 v4 写作计划

点查只需一路向下，但范围翻页需要从起始叶顺着 next 访问后续叶。扫描采用闭区间，空范围和超过最大键返回空或已有结果。

目标是完整重放 tree.py，测试覆盖边界和结构不变量。依赖上一版本；本版不引入磁盘或 WAL。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v3](../v3/tutorial.md)。现在可以查询任意主键，但页面请求 [17,24] 若逐个 get，需要重复走根到叶的路径；而真实键可能稀疏，不能枚举所有整数。我们需要从第一片叶开始，按已有记录访问下一叶。 新增 Leaf.next 指向右侧相邻叶。原叶 A 分成 A、B，原来的后继 C 不能丢失：先让 B.next=A.next，再令 A.next=B。内部节点不需要链，B+Tree 的全量值在叶中。链接只在叶分裂处修改，因此重复键覆盖不影响它。
- **Change:** # S02 v4：一次下降，沿叶子完成闭区间扫描; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v5 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

