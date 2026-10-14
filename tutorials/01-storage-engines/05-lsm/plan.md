# S05 模块计划

场景是频繁覆盖写入事件属性，模型逐步由内存字符串映射演变成文件集合。总路线不变量是最新版本可见、删除不能复活、未完成文件不能发布；本次仅完成v0/v1。

v0建立put/get及排序快照，覆盖同键只留最新值；v1将快照写成不可变UTF8 JSONL，支持新进程单文件读取。没有多文件查询、删除、清单、WAL或合并，不能宣称完整LSM或崩溃持久性。

API冻结：MemTable.put(str,str)、get(str)->str|None、items()->list[tuple[str,str]]；SSTable.create(Path,Mapping[str,str])->SSTable、SSTable(Path)、items()->Iterator[tuple[str,str]]、get(str)->str|None。空字符串有效，缺失为None；排序为Python字符串顺序，创建拒绝覆盖。

每版按正文任务顺序实现，测试先RED后GREEN，正文代码独立提取重放；独立review后验收，不提交Git。S04v3只依赖SSTable公开items/get，不访问内部文件格式。未来索引/过滤不得改变读取结果。
