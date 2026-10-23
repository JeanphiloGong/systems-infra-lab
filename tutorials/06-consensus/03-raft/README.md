# C03 Raft

在 main 逐版创建 model.py/experiments.py，后一版修改同名文件，不预先复制完整最终实现。

v0 日志/状态机 → v1 持久选举 → v2 前缀复制 → v3 多数提交 → v4 日志新旧 → v5 发布故障 → v6 消息故障 → v7 快照 → v8 回归与 etcd。

阅读入口：[v0](v0/tutorial.md)、[v1](v1/tutorial.md)、[v2](v2/tutorial.md)、[v3](v3/tutorial.md)、[v4](v4/tutorial.md)、[v5](v5/tutorial.md)、[v6](v6/tutorial.md)、[v7](v7/tutorial.md)、[v8](v8/tutorial.md)。每版直接入口运行已引入的检查，后续机制只在需要时加入；不依赖 reference 的旧 replay 脚本。

边界：固定成员、顺序事件与本地文件持久化。v3 尚缺换主时日志完整性保护，v4 才补齐；最终也不实现动态成员或线性一致读协议。
