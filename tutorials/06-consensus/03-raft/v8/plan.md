# C03 v8 实施计划：保留全部回归并对照真实 etcd

确定性模型能安排精确故障，但还没有真实服务的独立进程和网络超时。本版保留 v7 全部本地回归，另以固定版本 etcd 启动三进程，观察 leader 退出、恢复与少数派写入。

依赖：v7 的 model.py/experiments.py。

1. 在 `labs/consensus/raft/model.py` 实施：model.py 与 experiments.py 的内容沿用 v7，run_all 运行每个已出现的检查函数，没有版本开关。etcd_demo.py 通过 v3 JSON gateway 发真实读写，finally 结束自己创建的进程。请求超时只说明未获成功确认，不能推断写永不提交。
2. `experiments.py` 保留已出现的检查并加入本版日程。验收：先执行模型 run_all，再运行 etcd_demo。etcd 应报告三个真实进程、恢复值 after、少数派未获写成功。固定成员模型仍不实现动态成员或线性一致读协议；真实 etcd 的完整行为不能从简化模型推导。
3. 安装 etcd 3.5.17 并设置 ETCD_BINARY；从仓库根先运行 `uv run python -m labs.consensus.raft.experiments`，再运行 `uv run python -m labs.consensus.raft.etcd_demo`；完整文件见 [正文](tutorial.md)。

范围：完整本地回归和真实 etcd 三进程对照；不新增模型协议或生产运维能力。
