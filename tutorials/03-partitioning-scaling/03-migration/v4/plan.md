# P03 v4：重开切换后的快照并拒绝旧 owner

依赖 v3 的 Migration 与路由切换；整数键、覆盖值和 None 删除语义不变。此版只保存完成 cutover 的本地 JSON 快照，不恢复复制过程，也不提供任意崩溃原子性。

1. 用原 write 接口建立 0..4，包含旧键覆盖为 10/22 和删除键 3；完成 copy/delta/barrier/cutover 后保存 owners/version/fence/sequence/log/shards。
2. 子进程 JSON 解码时一次性把分片键转回整数；不修改 read 兼容字符串。通过原 read 读回 [10,1,22,None,4]，捕获旧 token 写入的 ValueError，再用当前 owner 写 key9=99。
3. 再次读全部旧键确认不变，父进程检查子进程成功和快照新值。运行 `uv run python checkpoint.py`；不能只打印 restarted=True。

完整代码见 [正文](tutorial.md)。JSON 写入没有 fsync/原子发布，状态重建成功不能外推成生产迁移恢复保证。
