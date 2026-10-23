# S05 v1 计划

前置v0。目标把排序快照保存为不可变单文件并在新进程重读。模型UTF8 JSONL行记录[key,value]；不含多文件、删除、索引或WAL。公共create接受Mapping，调用者用dict(memtable.items())刷写覆盖后最终值。

1. 第一节解释字典退出丢失，引入结构化JSON编码；规模S，示例含换行和非ASCII，验收解析不靠手工split字段。
2. 第二节定义严格排序及重复键拒绝、完整扫描读取；规模M，get不提前返回是为了检查文件尾部排序损坏。缺失None，不与空串混淆。
3. 第三节文件不可变创建；规模M，同目录临时文件完成写入flush后hard-link到目标，已有目标拒绝，finally清理临时名。解释仅POSIX本地原子命名可见性，不声称fsync崩溃持久性；文件清单仍属v5。
4. 最后完整sstable.py checkpoint与新进程create/read命令，规模M。测试排序、覆盖拒绝、无效键值、损坏形状/顺序、空表、UTF8、新进程重开。正文隔离回放不得导入当前源码。

所有任务依次依赖前项，目标同目录tutorial.md各节；不提交Git。S04集成仅依赖items/get。
