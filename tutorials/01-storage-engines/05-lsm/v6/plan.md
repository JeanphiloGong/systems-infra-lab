# S05 v6 实施计划

依赖 S05 v5 的 SSTable/标签/MANIFEST，S03 v1 的 framing 和 S04 v3 的 ImmutableTable。

1. 新建 wal.py：append 同步成功才返回，replay 先验证全部帧与业务字段，只对不完整尾部 truncate+fsync。长度/反码或 CRC 损坏必须报错且不改原文件。
2. 新建 v6.py/RecoveredStore：初始化只读取 MANIFEST 指定文件，再 WAL 回放；put 先日志后内存，get 先内存再 Bloom/SSTable，删除直接终止搜索。
3. flush 先创建 SSTable，再 publish，最后清 WAL；失败实例停写。check_v6.py 在三个边界 os._exit，重开验证删除不复活、新值和旧稳定键都保留。
4. 执行 `uv run python -m labs.storage.lsm.check_v6`。验收包含任意字符串/空值的新进程读取、三类损坏不截断、真正尾帧截断与 100 个负查询扫描数低于全查。冻结集成恢复链，合并策略留 v7。

完整代码与检查见 [正文](tutorial.md)。
