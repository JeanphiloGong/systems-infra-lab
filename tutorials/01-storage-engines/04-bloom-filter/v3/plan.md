# S04 v3 写作计划

压力：S05 v1 每次 get 都扫描文件，即使键不存在。前置 v2 与冻结的 S05 v1 SSTable。

1. 复现独立 keys 列表漏键会导致假阴性，改为从真实 SSTable.items 构建。正文第一节，规模 S，验收文件所有键都进入过滤器。
2. 完整 checkpoint SSTable依赖、filter.py、table.py，True 继续 get、False 跳过；build_reads 和 query_reads 分开。正文第二节，规模 M，验收 bits=1 强制误报仍读取返回 None，空字符串不当缺失。
3. 用真实表和过滤表对相同 302 查询比较结果，单独输出构建扫描和查询扫描；复开仍保留全部键。正文第三节，规模 S。外部测试监测 Path.open，核对实际应用文件打开次数与统计。

不支持可变文件、持久化位数组或 tombstone 新旧优先级；未来 tombstone 键也必须进入过滤器。教程复制完整冻结依赖，不用源文件链接替代。检查点提交：本轮不提交。
