# S06 v1 写作计划

v0查询不需id/note却读整行，按列分文件只读取region/amount。保持原行号、不单独排序列。

1. 压力112字节里36/56属于不需要字段；说明相同行号连接。第一节，规模S，依赖v0。
2. 完整rows.py+columns.py，预校验再写四文件，只扫描两列。第二节，规模M，检查结果相同、40字节/4槽位、删除未用列仍能查询。
3. 破坏长度确认拒绝，不把同长度一致性当可自动验证；冻结列投影。规模S，无提交。


## Tutorial Increment

- **Pressure:** The an order report that reads only region and amount scenario makes the current checkpoint insufficient for the v1 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 [v0](../v0/tutorial.md)。两行只需要地区和金额，却读了 112 字节。编号和备注占每行 36 字节，报表完全不用。若把字段放进独立文件，读取 region.bin 和 amount.bin 就能完成同一查询。 第 i 个地区必须对应第 i 个金额，不能分别排序两列。写入时先用 v0 的 encode 验证全部订单，解包后按原顺序分别写四个文件。每个字段的宽度不变；完整列文件总字节量仍与行文件相同，这里没有压缩。
- **Change:** # S06 v1：只打开地区与金额列; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/columnar -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S06 columnar storage teaching model for an order report that reads only region and amount; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v2 of S06 columnar storage, carrying forward the state and invariant rather than restarting from a disconnected example.

