# S06 v4 写作计划

场景压力：同一订单换成完整行点查和完整行更新，投影优势不能泛化。前置上一版；不变量是查询/解码结果不变。

1. 从上版成本引出新要求，先解释合同和语义。正文第一节，规模S，验收读者能推导新结构必要性。
2. 解释具体编码/访问规则和边界，再给完整 rows.py + columns.py + workloads.py 检查点，所有依赖在正文。正文第二节，规模M，依赖任务1，代码角色checkpoint。
3. 独立运行打印检查并隔离重放，验收 扫描112/40字节；点查56字节1/4读；全行更新56字节1/4写，更新后结果相同。规模S，依赖任务2。

边界：按slot非主键；新副本更新不与旧batch统计混用；多列非原子。数字只计应用载荷/操作，不作硬件结论。每版写完独立审核修改，无提交。


## Tutorial Increment

- **Pressure:** The an order report that reads only region and amount scenario makes the current checkpoint insufficient for the v4 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** 前置 v3。地区报表只读两列节省字节，但客服点开一条订单需要全部四列，修改整条订单也必须更新全部字段。这时列存是否仍然更合适，需要换成相同数据、相同结果的实验。 本版用slot定位，不构建主键索引；slot不是Order.id，不要求两者相等。行文件一次seek后读56字节；列布局在四个文件的slot*width处分别读取，总量也是56字节，却有四次文件读取。函数返回(Order,bytes,reads)，都不扫描之前的行。
- **Change:** # S06 v4：同一布局换负载：扫描、点查与更新; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/columnar -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S06 columnar storage teaching model for an order report that reads only region and amount; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

