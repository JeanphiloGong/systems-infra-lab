# C03 v2 实施计划：给 AppendEntries 增加前缀检查

v1 选出了 leader，但它本地追加的 mode=old 不会到达 follower。直接把新列表拼到 follower 后面会接受不相符的历史。AppendEntries 必须携带前一条的 index/term；前缀不匹配时拒绝，匹配时才修复未提交后缀。

依赖：v1 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：继续修改同一个 Node.receive：增加 append/ack 分支，并让成为 leader 后初始化 next/match。send_log 用 next 构造前缀与后缀；拒绝时 next 后退再试，成功时记下持久确认位置。请求序号 pending 只接受当前请求的响应，避免过期回复让 next 倒退。接收方先 persist 再 ack；冲突位置不得越过 commit。合法 AppendEntries 同时充当心跳，重置逻辑选举期限。本版仍没有自动多数提交，测试中的 commit 是人工输入。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：先运行状态机和选举检查。再拒绝 previous=1 的空 follower；接受并重复接收 term1 条目不重复追加；term3 覆盖未提交旧后缀并应用；试图覆盖已提交位置报错。下一版从 ack 推导 commit。
3. 从仓库根运行 `uv run python -m labs.consensus.raft.experiments`；完整文件见 [正文](tutorial.md)。

范围：一个协议规则或验证能力的增量；不会提前放入后续快照与故障机制。
