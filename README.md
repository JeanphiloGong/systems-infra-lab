# Systems Infra Lab

数据库与分布式系统学习仓库：10 个知识领域、40 个学习模块，覆盖 80 个核心概念。
每个模块按自己的 v0–vn 演进，通过可重复实验理解原理、权衡与故障行为。

## 学习规划

完整的模块目录、版本目标、依赖关系和验收实验见 [学习总计划](docs/roadmap.md)。
概念速查见 [80 个概念索引](glossary/README.md)，协作规则见 [编写与审核流程](docs/course-workflow.md)。

建议第一篇从 **T01 v0：转账失败与事务回滚** 开始，其详细写作任务已列在规划中。
已实现正文见 [教程入口](tutorials/README.md)。

## 当前状态

已开始按模块编写教程与实验，使用独立审核、修订和重放验证闭环。
规划中的 196 个能力检查点不是已完成教程；实际状态见 [实施进度](docs/progress.md)。

Python 实验使用 uv 管理依赖，数据库实验使用隔离的 PostgreSQL 实例。
安装与启动命令见 [实验环境](docs/environment.md)。

教程和实验代码保存在本仓库，与 `agent-infra-lab` 的 Coding Agent 主线独立演进。
