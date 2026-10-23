# A01：Backup 与 PITR

本专题在专用 PostgreSQL 16.4 上重建 accounts 表并进行恢复。v0/v1 恢复到独立临时数据库；v2 创建物理 base backup 并检查归档；v3 启动恢复容器到达误删前；v4 只在归档副本中删除必要 WAL。连接地址必须指向本实验实例。

先安装 PostgreSQL 16 客户端 `pg_dump`、`pg_restore`、`psql`、`pg_basebackup` 并加入 PATH；例如 Debian 安装目录通常是 `/usr/lib/postgresql/16/bin`。用 `pg_dump --version` 确认主版本为 16。uv 管理 Python 依赖，不安装这些工具。

```bash
uv sync --locked
mkdir -p /tmp/a01-wal-archive
chmod 777 /tmp/a01-wal-archive
docker compose -f infra/e03.compose.yaml up -d --wait
export A01_DATABASE_URL='postgresql://a01:a01_local_only@127.0.0.1:55452/a01'
```

归档挂载目录只用于本机实验，容器内 PostgreSQL 需要写权限；归档按 PostgreSQL system_identifier 分子目录。若该路径或 55452 已被其他实验占用，先结束对应实验，不共享数据。v0/v1 不读归档；v2 才在 common.py 加入归档函数。

按 [v0](v0/tutorial.md) → [v1](v1/tutorial.md) → [v2](v2/tutorial.md) → [v3](v3/tutorial.md) → [v4](v4/tutorial.md) 创建文件并执行每页直接命令。每版逐步补充 common.py；不需要参考分支测试。

完成本专题后，在启动它的同一目录关闭服务：

```bash
docker compose -f infra/e03.compose.yaml down -v
```

脚本清理自己创建的恢复库、恢复容器和临时备份；原始归档保留供检查，不自动删除其他实验数据。检查归档目录归属后再手动清理本次集群的子目录。
