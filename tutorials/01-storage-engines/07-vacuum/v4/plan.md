# S07 v4 计划

前置v3；目标autovacuum触发依赖阈值与后台调度，观测必须设置超时并报告未观察到。完整automatic.py作为checkpoint，真实PostgreSQL测试与独立重放；只创建并清理s07_ schema。不提交Git。


前置：本模块 v3。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. automatic.py 只修改本次 items 的 autovacuum 阈值并删除 800 行；保存 autovacuum_count 起点，强制提交统计。
2. 用 monotonic deadline 轮询统计，返回实际 elapsed 与 observed/count；超时 observed=False 是合法结果。运行短 timeout 验证边界，再用默认窗口观察后台任务，不能把超时当成功。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
