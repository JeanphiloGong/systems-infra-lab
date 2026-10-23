# S05 v3 计划

前置v2。任务1：从省略键导致旧值复活引出持久删除，规模S。任务2：用JSON结构化标签区分普通值与删除，规模M，不能保留任何特殊字符串。任务3：完整sstable.py与tombstones.py checkpoint，规模M；从正文提取两文件到独立目录、两个新进程create/reopen，验证删除/空串/原标记字符串/JSON形状字符串。各任务依次依赖前项，目标本目录tutorial.md对应章节，不提交Git。

值语义协议为["value", text]或["delete"]，载荷由冻结v1 SSTable保存；v3所有输入文件由TombstoneStore.create产生，不自动兼容v2原始字符串文件。调用者以新到旧列表定义优先级。测试检查更晚put覆盖旧删除、错误tag抛错和无效类型不发布文件。无合并/清单/WAL，独立review后验收。
