# S06 v3 写作计划

场景压力：按金额范围查询仅一批可能匹配；min/max不相交才能跳过，等号必须读。前置上一版；不变量是查询/解码结果不变。

1. 从上版成本引出新要求，先解释合同和语义。正文第一节，规模S，验收读者能推导新结构必要性。
2. 解释具体编码/访问规则和边界，再给完整 rows.py + columns.py + batches.py 检查点，所有依赖在正文。正文第二节，规模M，依赖任务1，代码角色checkpoint。
3. 独立运行打印检查并隔离重放，验收 [20,30]读取40字节、全范围160、间隙0，遍历多边界与逐行参考一致。规模S，依赖任务2。

边界：统计由同一数据生成，仅内存，不可伪造或修改源文件；同长度变化检测不承诺。数字只计应用载荷/操作，不作硬件结论。每版写完独立审核修改，无提交。


## Tutorial Increment

- **Pressure:** The an order report that reads only region and amount scenario makes the current checkpoint insufficient for the v3 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 v2。八条金额为0、10、20、30、40、50、60、70的订单，每两行为一批。查询金额[20,30]时只有第二批可能匹配。如果仍打开所有批次，列投影虽减少字段，却没有减少被扫描的行组。 write_batches按原顺序切组，每组写v1的四个列文件，同时从同一组Order计算count、minimum、maximum。Batch是不可变描述对象，返回tuple；空输入没有批次，batch_size必须为正。每个batch目录只能新建，避免悄悄覆盖原统计对应文件。
- **Change:** # S06 v3：批次统计：不相交才允许跳过; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/columnar -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S06 columnar storage teaching model for an order report that reads only region and amount; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v4 of S06 columnar storage, carrying forward the state and invariant rather than restarting from a disconnected example.

