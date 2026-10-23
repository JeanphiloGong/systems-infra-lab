# C02 选主

在 main 逐版创建 model.py/experiments.py，后一版修改同名文件，不预先复制完整最终实现。

v0 超时自封反例 → v1 多数投票 → v2 投票持久化 → v3 资源侧 lease/fence → v4 故障组合。

阅读入口：[v0](v0/tutorial.md)、[v1](v1/tutorial.md)、[v2](v2/tutorial.md)、[v3](v3/tutorial.md)、[v4](v4/tutorial.md)。每版直接入口运行已引入的检查，后续机制只在需要时加入；不依赖 reference 的旧 replay 脚本。

边界：固定三节点、确定性时钟、可信且不重启的资源；不含复制日志。
