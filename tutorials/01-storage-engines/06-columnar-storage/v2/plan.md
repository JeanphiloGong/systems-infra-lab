# S06 v2 写作计划

场景压力：地区重复占用12字节，字典只存不同值并以uint16代码保留行位置；code0是None。前置上一版；不变量是查询/解码结果不变。

1. 从上版成本引出新要求，先解释合同和语义。正文第一节，规模S，验收读者能推导新结构必要性。
2. 解释具体编码/访问规则和边界，再给完整 dictionary.py 检查点，所有依赖在正文。正文第二节，规模M，依赖任务1，代码角色checkpoint。
3. 独立运行打印检查并隔离重放，验收 600字节代码+22字节字典，相比3600字节；缺失/空输入/Unicode/坏码。规模S，依赖任务2。

边界：字典开销可能抵消收益，不把索引当排序值。数字只计应用载荷/操作，不作硬件结论。每版写完独立审核修改，无提交。


## Tutorial Increment

- **Pressure:** The an order report that reads only region and amount scenario makes the current checkpoint insufficient for the v2 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 v1。300 行的地区列只有 east、west 和缺失值，却按每行12字节占3600字节。列布局让相同值相邻于同一文件；我们现在单独压缩地区，不改变金额的语义。 字典保存每个不同地区一次，每行只存一个16位无符号代码。code0专门表示None，east和west按首次出现顺序获得1和2。代码是位置，不是地区值本身，必须和对应字典一起保存。
- **Change:** # S06 v2：地区字典：把重复字符串换成短代码; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/columnar -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S06 columnar storage teaching model for an order report that reads only region and amount; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v3 of S06 columnar storage, carrying forward the state and invariant rather than restarting from a disconnected example.

