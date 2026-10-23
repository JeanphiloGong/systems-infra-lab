# P02：数据倾斜与热点

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

v0-v3从均匀/倾斜分布、单热键扩容、可拆分计数加盐到容量边界。实验代码在labs/partitioning/skew，所有命令从仓库根目录执行。
