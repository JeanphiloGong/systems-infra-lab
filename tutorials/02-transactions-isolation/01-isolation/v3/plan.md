# T01 v3 写作计划

前置 v2。场景为重复查询余额至少 50 的账户数，压缩为一次插入，核心为谓词集合、事务快照、提交边界。不变量：输出精确对应其快照；插入新账户合法地把总额从 200 增为 250，不能要求转账不变量。

1. 依赖 v2，规模 M，tutorial.md 第一步新增 phantom_read checkpoint。R 首次 count=2，W 插入第三行并提交，R 再 count；RC 得 3。验收第三次在事务结束后读为 3。
2. 依赖任务 1，规模 S，配置 patch 改 RR，验收 2/2/3。解释快照始于第一条 SELECT，插入没有被阻塞；不将幻读消失等同串行化。
3. 依赖任务 2，规模 M，完整 observations.py checkpoint，给 CLI phantom 分支及双级别运行。独立正文回放与旧版本实验继续通过。无新 helper、无提交。

函数外部契约为两个已初始化 autocommit 连接与允许级别，返回 before/after/fresh。审查重点是读者事务必须跨越 writer 提交，最后读取必须在该事务之外。下一版整理 ACID，不引入新的隔离算法。
