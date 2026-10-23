# Systems Infra Lab

数据库与分布式系统学习仓库：10 个知识领域、40 个学习模块，覆盖 80 个核心概念。
每个模块按自己的 v0–vn 演进，通过可重复实验理解原理、权衡与故障行为。

## 学习规划

完整的模块目录、版本目标、依赖关系和验收实验见 [学习总计划](docs/roadmap.md)。
概念速查见 [80 个概念索引](glossary/README.md)，协作规则见 [编写与审核流程](docs/course-workflow.md)。

建议从 [T01 v0：转账执行到一半报错](tutorials/02-transactions-isolation/01-isolation/v0/tutorial.md) 开始。先读 [从零学习约定](docs/learning-workspace.md)，再按正文创建文件、观察故障并修复。
其他专题见 [教程入口](tutorials/README.md)。

## 当前状态

`main` 用于从零学习：保留教程、规划和环境配置，`labs/` 与 `tests/` 中的文件由你按教程逐步创建。教程中的“新建”是实际操作，不需要另建练习目录。

预先生成的完整实验和测试已保存在本地 `reference` 分支。它是参考答案快照，不是你的学习进度，也不代表每个旧版本的实现。查看单个参考文件而不覆盖当前练习：

```bash
git show reference:labs/transactions/isolation/schema.sql
```

只有需要对照时才查看参考答案。[参考检查说明](docs/reference-checks.md) 给出独立工作区的运行办法。教程里的历史验证结果见 [实施进度](docs/progress.md)，不表示当前学习工作区已有对应代码或已通过测试。

Python 实验使用 uv 管理依赖，数据库实验使用隔离的 PostgreSQL 实例。
安装与启动命令见 [实验环境](docs/environment.md)。

教程和实验代码保存在本仓库，与 `agent-infra-lab` 的 Coding Agent 主线独立演进。
