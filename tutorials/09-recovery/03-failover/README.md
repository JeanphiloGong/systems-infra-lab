# A03：High Availability 与 Failover

当前状态：v0-v4 的确定性教学模型、v1 的真实 PostgreSQL promotion probe，以及 v2-v4 的 Patroni 实验均已完成作者验证。教程中的代码和配置可以从各版本的完整 checkpoint fences 复现；普通测试不会自动启动 Docker。

真实实验使用已有 disposable `infra/r04.compose.yaml`：primary `55440`、standby `55441`、subscriber `55442`。`labs/recovery/ha/postgres_probe.py` 会写入 primary、等待物理复制、调用 `pg_promote(wait => true)`，再在 promoted standby 上写入。旧 primary 的 fencing 由停止 disposable 容器完成；普通 PostgreSQL streaming replication 本身不会自动隔离旧主。

```bash
docker compose -f infra/r04.compose.yaml up -d --wait
A03_POSTGRES_LIVE=1 uv run python -m labs.recovery.ha.postgres_probe
docker compose -f infra/r04.compose.yaml stop primary
```

不要把这个手动 promotion 演练描述成自动 HA。v2-v4 使用独立的 Patroni 4.1.5、PostgreSQL 16 和 etcd 3.5.17 disposable 集群，运行真实进程和 SQL：断开当前主节点的 Docker 网络后，副本自动提升；旧主进程仍存活但本地 SQL 写入被拒绝；已确认的写入保留；旧主通过 `reinitialize` 重建为副本，并完成计划回切。

```bash
ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
uv run python -m labs.recovery.ha.patroni_probe
uv run python tests/recovery/ha/replay_patroni.py --version 2 --live
uv run python tests/recovery/ha/replay_patroni.py --version 3 --live
uv run python tests/recovery/ha/replay_patroni.py --version 4 --live
bash infra/a03-patroni/lab.sh down
```

这仍是单 etcd 的教学实验，不是生产 HA 拓扑。RPO=0 只适用于故障注入前明确等待副本追平的样本；它不代表异步复制的普遍保证。网络隔离 fencing 依赖 Patroni 停止旧主 PostgreSQL，不是硬件 STONITH，也不覆盖整个主机冻结。
