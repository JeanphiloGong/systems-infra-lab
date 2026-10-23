# T01 v2 写作计划

前置 v1 的双连接入口与 v0 transfer。报表把分开查询的 A/B 相加；模型保留两 SELECT 之间的一次已提交转账。读取事件必须标明各自快照，真实已提交状态总额始终 200。

1. 文档 tutorial.md 第一步，规模 S，checkpoint：新增 read_skew，RC 读 A=100，调用 transfer 提交，再读 B=130。依赖 v1，验收组合总额 230 但 SQL sum=200。
2. 第二步规模 S，patch：仅改隔离参数 RR，依赖任务 1。验收 A/B=100/100，说明首条读取建立快照；单语句 sum 与事务快照是不同修复范围。
3. 最后一步规模 M，checkpoint：完整 observations.py 包含旧行为和新 CLI 分支；依赖任务 2。独立提取 v0 transfer/schema 与本版代码重放 RC/RR。非法级别、写入最终 70/130、旧 dirty 实验继续检查。

外部契约：read_skew 返回 first,second,single_statement 三个整数，接收两个空闲 autocommit 连接与允许级别，不重置数据。无新增 helper；不声称 RR 可串行化；下一版转向谓词集合变化。所有任务不提交，独立审核后才完成。
