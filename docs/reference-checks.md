# 可选的参考答案检查

这是供对照答案与维护旧教程使用的检查，不是从零学习的必经步骤。各页折叠区内的旧 pytest/replay 命令依赖 reference 分支中的测试或提取脚本；直接在尚未创建这些文件的 main 执行会报文件不存在。

不要在学习工作区切换或覆盖文件。需要运行参考答案时，在另一个临时工作区检出 reference：

```bash
reference_dir=$(mktemp -d /tmp/systems-reference.XXXXXX)
git worktree add --detach "$reference_dir" reference
cd "$reference_dir"
uv sync --locked
```

在这个终端按对应专题配置隔离的外部服务、连接变量，然后运行该页折叠区中的命令。不要照抄别的专题数据库地址。像 D03、R04、CDC、PITR 和 HA 都有自己的环境要求；基础 PostgreSQL 服务不能替代它们。

这些旧测试可能检查 reference 的最终接口，或提取 reference 里的旧版正文；它们没有自动改为读取 main 的新版教程或你的代码。因此结果只能归于所检出的参考版本，不证明当前学习版本通过。T01 的 main 教程直接给出逐版测试创建步骤；C02/C03 的新主线使用同名 model.py/experiments.py，S05 v6/v7 也已改为集成实现，旧 replay 的 advanced.py、版本开关或独立脚本假设不再适用。使用当前正文里的直接命令和断言验证自己的代码。

结束时回到原来的仓库。只有临时工作区没有个人改动时，才移除它：

```bash
cd /home/gong/date/2026/oct/systems-infra-lab
git worktree remove "$reference_dir"
```

如果命令报告工作区有改动，先查看和保存这些改动，不使用 force 清理。不在这里运行全量测试；按当前专题范围逐项检查并记录实际结果。
