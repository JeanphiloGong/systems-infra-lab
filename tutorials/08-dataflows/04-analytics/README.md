# E04：Data Warehouse 与 Federation

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

本专题用三个独立 PostgreSQL 实例建立订单、客户两种来源与分析仓库。v0 记录批次来源，v1 处理迟到更新，v2 用 `postgres_fdw` 联邦查询并观察远程 SQL，v3 对比复制快照与实时联邦在源变化和源不可用时的边界。按各版正文创建 `labs/dataflows/analytics/` 下的代码和 compose 配置，再启动该专题专用环境。

FDW 不自动提供跨源一致快照。所有结果都包含截止位置或来源状态，不能把仓库快照冒充实时数据。
