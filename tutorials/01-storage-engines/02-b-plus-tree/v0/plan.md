# S02 v0 写作计划

数组是之后所有树实现的行为参考。整数键和值共享位置，重复键覆盖，插入返回右移数量。

1. `[20, 40]` 插入 30 先展示 append 破坏排序，使用 `bisect_left` 并计数右移；完整目标 `array_index.py`，验收点查、缺失、覆盖和移动数。
2. 独立运行正文检查并冻结升序与覆盖语义，留下固定页容量问题。

代码角色是完整 checkpoint；不实现页、删除、范围扫描或持久化；本轮不提交。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v0 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 商品按主键查询，还需要按主键范围翻页。B-Tree 把键和值放在多个节点，B+Tree 通常把值集中在叶子并连接叶子；本系列选择 B+Tree。先从最小的有序数组开始，因为它是之后每次树结构改造都必须保持的参考行为。 数组模型包含整数主键与泛型值，例子使用字符串值；重复键覆盖旧值。插入新键时后方元素需要移动，`insert` 返回移动数量；这不是硬件 I/O 计数，只是让插入成本可见。暂不支持删除、范围扫描和持久化。
- **Change:** # S02 v0：先用有序数组建立参考答案; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v1 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

