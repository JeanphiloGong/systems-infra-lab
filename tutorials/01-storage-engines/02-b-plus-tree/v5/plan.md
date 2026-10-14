# S02 v5 写作计划

内存结构必须变成可验证的页文件。每页固定 256 字节，元页记录 magic、版本、容量、根页号、页数和高度；叶页记录键值与 next 页号，内部页记录子页号与分隔键；每页尾部 CRC32。打开时按页号重建对象图，不重新插入键。依赖 v4；不提供崩溃原子性，不提前引入 WAL。

验收关闭/重开后拓扑、根元数据和叶链相同；截断、额外字节、CRC 错误、不可编码值均拒绝且不覆盖已有文件。完整代码目标 `labs/storage/bplus_tree/page_file.py`，测试 `test_s02_persist.py`。


## Tutorial Increment

- **Pressure:** The ordered product keys and range reads scenario makes the current checkpoint insufficient for the v5 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 v4。保存全部键值后再逐项插回会丢失页拓扑，也不能验证页损坏。这里定义固定 256 字节页：第 0 页是元页，之后是节点页；每页尾部保存 CRC32。叶页保存 `(key,value)` 与 next 页号，内部页保存 child page IDs 和分隔键。打开时按页号连接对象，绝不重新插入键。 本版只保证完整写入文件的编码和读取；`path.open("wb")` 中途退出可能留下截断文件。WAL 与崩溃恢复仍属于 S03，不能从本版 `save` 推导出来。
- **Change:** # S02 v5：把页号和根元数据写进固定页; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/bplus_tree -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S02 B+Tree teaching model for ordered product keys and range reads; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v6 of S02 B+Tree, carrying forward the state and invariant rather than restarting from a disconnected example.

