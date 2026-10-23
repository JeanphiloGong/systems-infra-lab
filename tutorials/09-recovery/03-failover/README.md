# A03：High Availability 与 Failover

在 `main` 按各版正文逐步创建实验文件，先完成前置版本再运行命令。路径是创建目标；旧测试和 replay 脚本仅供 `reference` 对照。参见 [从零学习约定](../../../docs/learning-workspace.md)。

历史参考内容包括 v0-v4 的确定性教学模型、v1 的 PostgreSQL promotion probe，以及 v2-v4 的 Patroni 实验。先按各版正文创建模型、入口与配置，再运行本版命令；历史验证不代表你的当前实现通过检查，普通测试不会自动启动 Docker。

v1 真实实验使用 `infra/r04.compose.yaml`：primary `55440`、standby `55441`、subscriber `55442`。先完成 R04 v0 的三个挂载文件，再创建 [v1 正文](v1/tutorial.md) 的 `labs/recovery/ha/postgres_probe.py`。prepare 等待已确认记录到达 standby；旧 primary 停止后才能 promote 并向新主写入。

```bash
docker compose -f infra/r04.compose.yaml up -d --wait
uv run python -m labs.recovery.ha.postgres_probe prepare
docker compose -f infra/r04.compose.yaml stop primary
uv run python -m labs.recovery.ha.postgres_probe promote
```

演练结束执行 `docker compose -f infra/r04.compose.yaml down -v`。这只清理 R04 专用实验卷；普通 streaming replication 不会自动隔离旧主。

不要把这个手动 promotion 演练描述成自动 HA。v2-v4 使用独立的 Patroni 4.1.5、PostgreSQL 16 和 etcd 3.5.17 disposable 集群，运行真实进程和 SQL：断开当前主节点的 Docker 网络后，副本自动提升；旧主进程仍存活但本地 SQL 写入被拒绝；已确认的写入保留；旧主通过 `reinitialize` 重建为副本，并完成计划回切。

```bash
ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
uv run python -m labs.recovery.ha.patroni_probe
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python tests/recovery/ha/replay_patroni.py --version 2 --live
uv run python tests/recovery/ha/replay_patroni.py --version 3 --live
uv run python tests/recovery/ha/replay_patroni.py --version 4 --live
```

</details>

```bash
bash infra/a03-patroni/lab.sh down
```

这仍是单 etcd 的教学实验，不是生产 HA 拓扑。RPO=0 只适用于故障注入前明确等待副本追平的样本；它不代表异步复制的普遍保证。网络隔离 fencing 依赖 Patroni 停止旧主 PostgreSQL，不是硬件 STONITH，也不覆盖整个主机冻结。
