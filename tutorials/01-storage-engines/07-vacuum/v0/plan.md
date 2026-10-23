# S07 v0 计划

反复UPDATE固定集合，ANALYZE后读取n_live_tup/n_dead_tup/物理大小并查询COUNT(*)。逻辑行数保持1000，统计显示版本回收问题；不把统计瞬间值当精确事务历史。


前置：模块 README 的运行环境。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. 在 vacuum.py 创建唯一 s07_ schema、1000 行 items，并关闭该表 autovacuum 以便控制实验。churn 重复 UPDATE；用 COUNT 检查逻辑行数仍为 1000。
2. 执行 ANALYZE 与 stats，分别报告 n_live_tup/n_dead_tup 和关系大小；统计刷新有延迟，不能硬编码死元组精确数量。finally 只删除本次 schema；v1 才执行普通 VACUUM。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
