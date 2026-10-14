# S02 v6 写作计划

删除必须保持查找、范围和根收缩不变量。叶欠载从兄弟借位，否则合并并更新父分隔键；内部欠载沿相同规则向祖先传播，根单子节点时收缩。完整 checkpoint 必须是可复制的 tree.py，不能是 import 或链接。验收逐步删除、叶/内部借位、叶/内部合并、缺失键无副作用、结构验证和根回到叶。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v6 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 v5。删除最后一个键时，根不应留下空的内部节点。本版在叶页欠载时从左/右兄弟借一条记录，无法借出时合并叶页并更新父分隔键；父内部节点也沿同一规则借位或合并，根只保留一个子节点时收缩。它仍不处理并发删除或持久化写回。 本版本的最终 checkpoint 包含完整的 `tree.py`，包括 v4 的插入/扫描、叶页借位与合并、内部节点借位与合并、祖先分隔键刷新和根收缩；读者不需要从 v4 拼接片段。
- **Change:** # S02 v6：删除先保证结果和根收缩; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v7 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

