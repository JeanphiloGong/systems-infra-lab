# D04 v1：新进程继续已保存的 Saga

依赖 v0 的 reserve/charge 顺序；本版将 step 状态写入 SQLite 文件，但不承诺外部副作用与 done 原子提交。

1. v1.py 的 Saga 在执行 effect 前保存 running，成功后保存 done；再次遇到 done 则跳过。
2. 父进程在 TemporaryDirectory 的文件数据库完成 reserve 并关闭连接，子进程使用同一路径继续 reserve/charge。
3. 运行 `uv run python labs/coordination/saga/v1.py`；子进程 calls 只能为 ['charge']，数据库两步均 done，父进程检查退出成功。不是使用 :memory: 假装重启。

effect 成功但 done 未写的窗口仍可重做，v2 引入补偿，外部幂等依赖接收方契约。完整实现见 [正文](tutorial.md)。
