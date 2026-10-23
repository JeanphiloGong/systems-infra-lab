# C02 v3 实施计划：由资源拒绝旧 leader 写入

v2 保存了投票，却不能阻止暂停的旧 leader 恢复后继续写。现在让被写资源检查 owner、term 和到期时刻。这个资源是实验中可信且不重启的授权入口；选举成功后由模拟器注册新 owner，真实服务还需要验证授权证据并持久化 fence。

1. 新增 `Resource.activate/write`，Election 只有赢得多数票才调用 activate。write 把当前节点身份交给资源；判断基于资源自己的逻辑时钟，等于 expires 就拒绝。这里没有租约续期，也不声称各机器时钟同步；资源换了 owner 后，即使旧节点后来获知新 term，也因 owner 不匹配被拒绝。
2. 在 `experiments.py` 加入本版日程，保留前版已成立的检查。
3. 执行 `uv run python -m labs.consensus.leader_election.experiments`。验收：先保留 v1/v2 检查，再检查期限恰好到 5 时写入失败、term2 的 b 可写 successor、a 仍自认 leader 但写入失败且值不变。没有日志复制，所以这只保护资源写权限。v4 扩充故障组合。

文件与完整代码见 [正文](tutorial.md)。范围为一个模型变化和一个可直接运行的检查组；不需要参考分支。
