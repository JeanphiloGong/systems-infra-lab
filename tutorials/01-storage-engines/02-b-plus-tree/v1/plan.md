# S02 v1 写作计划

v0 数组没有页容量。固定容量叶页保留升序与覆盖语义；插入新键超过容量直接抛出，分裂留给 v2。

1. 用容量3插入第4个键展示边界，建立 `LeafPage`；验收满页拒绝、重复键覆盖、移动数、非法容量。依赖 v0，完整 checkpoint `leaf.py`。
2. 独立重放并冻结单叶页，留下溢出处理问题。本轮不提交。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** v0 的数组可以无限增长，但真实页有固定容量。先把容量设为 3：前三个键可查，第四个新键必须拒绝；重复键覆盖不需要新槽位。分裂是下一版的压力，不在本版偷偷加入。 v0 用两个平行列表保存键和值。页分裂时若只切分其中一个列表，关联就会错位；因此本版把它们组成 `(key, value)` 对，放进同一个 items 列表。后续切片移动的是完整记录。为了使用 bisect，临时提取键列表，这一步是 O(n)，所以本版不是整体 O(log n) 查找；这里页内容量很小，先保持表示直观。
- **Change:** # S02 v1：把有序数组装进一个叶页; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

