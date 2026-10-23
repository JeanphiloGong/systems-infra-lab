# S05 v7 实施计划

依赖 S05 v6 的完整恢复链与 v4.compact，保留同一个 v6.py/RecoveredStore 接口及标签文件格式。

1. compact('full') 用 v4 全量合并后 publish；compact('leveled') 用 L0/L1 两层规则，L0 达到两张时下推最老表，选择所有范围相交的 L1，保留较新值与 tombstone。
2. 用 l1- 文件名前缀持久记录层级，MANIFEST 保持活跃集合权威；断言 L1 范围不重叠，再原子发布。异常实例停写、旧文件不回收。
3. check_v7.py 从同一份四批数据复制两套目录；每次合并重开读回全部键，leveled 输入文件数量必须为 [1,1,2]，最终一张 L0/两张 L1。
4. 执行 `uv run python -m labs.storage.lsm.check_v7`，同时保留 v6 恢复检查。计数来自实际文件与查询；分别报告范围规划、合并读/写、活跃/保留字节。明确只有两层、无 L2/后台调度/安全回收，不外推生产性能。

完整代码与检查见 [正文](tutorial.md)。
