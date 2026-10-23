# P02 v3 计划

目标观察容量与尾部延迟边界。使用固定输入和确定路由；每分片计数、总量守恒、热点不因扩容消失，加盐显式分担。完整checkpoint及测试；不宣称真实数据库性能。


前置：本模块 v2。以下任务依次进行，目标文档为 [tutorial.md](tutorial.md)。

1. queues.py 导入 v2.route，对明确的到达时间与单片 service time 逐次计算排队完成时间，新增 shared_service 表示 dispatcher 串行瓶颈。
2. 同 1000 个 hot 请求扩 4→8 片时 p99 不变；加盐降低 p99，提高容量；shared_service=1 后容量又受限为 1。检查 32 组输出与断言，所有延迟仅属于离散队列模型。

按正文给出的直接运行命令检查当前代码；reference 中的旧测试仅供对照。
