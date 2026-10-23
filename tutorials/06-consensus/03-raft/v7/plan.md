# C03 v7 实施计划：用快照追赶被截断的日志

v6 的日志永远增长。若直接删除已提交前缀，离线 follower 的 nextIndex 会指向已经不存在的位置。本版保存已应用状态及其最后 index/term，并给落后的 follower 发送 snapshot，再发送剩余日志。

依赖：v6 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：Node 增加 base/base_term/snapshot_state：base 是已经压缩的绝对位置，last=base+len(log)，列表访问减 base+1。旧磁盘文件缺少这三项时按 0/0/{} 读取，v6 数据仍表示未压缩前缀；只新增字段，不另起另一套 model。compact 仅压缩到 commit；persist 同时发布快照元数据、状态和后缀。send_log 在 next<=base 时改发 snapshot；接收方先持久化快照再确认，再追赶后缀。只有边界 term 匹配才能保留本地后缀。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：c 离线时提交 x=1/2，将 leader 压缩到 base=2，再提交 x=3；恢复 c 后必须收到 snapshot，重启 c 仍有 base=2、last=commit=3、state x=3。九个发布故障扩充为十二个，包含快照的三个发布点；此前全部回归仍执行。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
