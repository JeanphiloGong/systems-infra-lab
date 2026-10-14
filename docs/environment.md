# 实验环境

所有命令从 `systems-infra-lab` 仓库根目录执行。使用 Python 3.12 或更新版本、
uv 和 Docker Compose。Python 依赖由 `uv.lock` 锁定；PostgreSQL 16 镜像按摘要固定。
数据库绑定到本机回环地址，以下固定口令仅用于本实验实例。

```bash
uv sync --locked
docker compose -f infra/postgres.compose.yaml up -d --wait
export SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab'
```

`SYSTEMS_LAB_DATABASE_URL` 只能指向本实验创建的数据库。各数据库实验使用自己的
临时 schema；不要提供业务数据库地址。无需配置模型 API。

若 55432 已被占用，启动前设置 `SYSTEMS_LAB_POSTGRES_PORT=55433`，并将连接 URL
中的端口一并改为 55433。`uv` 不负责启动数据库，启动成功后才能运行数据库实验。

检查运行环境：

```bash
uv run python --version
docker compose -f infra/postgres.compose.yaml exec -T postgres \
  psql -U systems_lab -d systems_lab -c 'select version();'
```

F01 的事务池代理实验还需要 PgBouncer：

```bash
docker compose -f infra/postgres.compose.yaml -f infra/pgbouncer.compose.yaml up -d --wait
export SYSTEMS_LAB_POOL_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:56432/systems_lab'
```

D03 使用独立实例开启 prepared transactions。先按
[D03 环境与清理说明](../tutorials/07-coordination/03-distributed-commit/README.md)
启动专用实例并检查就绪，再设置：

```bash
export D03_DATABASE_URL='postgresql://d03:d03_local_only@127.0.0.1:55434/d03'
```

准备这三个端点后，运行已实现的实验测试：

```bash
uv run --locked pytest
```

测试通过只证明当前实现及所运行的检查，不代表规划中的所有教程完成。
每版教程的旧代码重放和独立审核结果另见 [进度记录](progress.md)。

结束实验时停止容器，保留实验数据卷：

```bash
docker compose -f infra/postgres.compose.yaml down
```

需要完全重新初始化本实验数据库时，才使用 `down --volumes` 删除该 Compose
项目的实验数据卷。该操作会丢弃实验数据，不用于普通停止。
