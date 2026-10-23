# R04 v0：真实 PostgreSQL 物理流复制

本章不模拟 WAL。固定 PostgreSQL 16 主节点写入 WAL，standby 用 pg_basebackup 和 primary_conninfo 从同一专用容器开始，然后由 walsender 发送。standby 的 pg_is_in_recovery() 必须为 true，写入应得到只读错误。

## 运行边界

这套服务只属于 R04：primary 55440、standby 55441、subscriber 55442。不要连接仓库共享 PostgreSQL 55432。等 primary healthy 和 standby 接受连接后运行 `D03_DATABASE_URL` 无关的 R04 脚本；脚本本身使用 common.py 的固定端口。编排文件、初始化 SQL、pg_hba 和 standby 启动脚本都在正文可打印路径中。

v0 在 primary 创建表并写一行，读取 pg_current_wal_lsn，等待 standby pg_last_wal_replay_lsn 达到该位置，再核对数据和 pg_stat_replication 的 streaming 状态。LSN 是进度证据；“脚本退出成功”不是复制证据。standby 写失败证明 hot standby 的只读边界，不证明所有物理复制配置都适合生产。

将下面的完整代码保存为 `infra/r04.compose.yaml`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: infra/r04.compose.yaml -->

```yaml
name: systems-r04
services:
  primary:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    environment:
      POSTGRES_USER: r04
      POSTGRES_PASSWORD: r04_local_only
      POSTGRES_DB: r04
    command: [postgres, -c, wal_level=logical, -c, max_replication_slots=8, -c, max_wal_senders=8, -c, min_wal_size=32MB, -c, max_wal_size=64MB]
    ports: ["127.0.0.1:55440:5432"]
    volumes:
      - primary-data:/var/lib/postgresql/data
      - ../labs/replication/postgres/init.sql:/docker-entrypoint-initdb.d/01-r04.sql:ro
      - ../labs/replication/postgres/replication.sh:/docker-entrypoint-initdb.d/02-r04.sh:ro
    healthcheck:
      test: [CMD-SHELL, "pg_isready -h 127.0.0.1 -U r04 -d r04"]
      interval: 1s
      timeout: 3s
      retries: 60
  standby:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    user: postgres
    environment:
      PGPASSWORD: r04_replica_only
    entrypoint: [bash, /r04/standby.sh]
    depends_on:
      primary:
        condition: service_healthy
    ports: ["127.0.0.1:55441:5432"]
    volumes:
      - standby-data:/var/lib/postgresql/data
      - ../labs/replication/postgres/standby.sh:/r04/standby.sh:ro
  subscriber:
    image: postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
    environment:
      POSTGRES_USER: r04
      POSTGRES_PASSWORD: r04_local_only
      POSTGRES_DB: r04
    ports: ["127.0.0.1:55442:5432"]
    volumes:
      - subscriber-data:/var/lib/postgresql/data
volumes:
  primary-data:
  standby-data:
  subscriber-data:
```

将下面的完整代码保存为 `labs/replication/postgres/init.sql`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/postgres/init.sql -->

```sql
CREATE ROLE r04_replica WITH LOGIN REPLICATION PASSWORD 'r04_replica_only';
```

将下面的完整代码保存为 `labs/replication/postgres/replication.sh`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/postgres/replication.sh -->

```bash
set -eu
printf '%s\n' 'host replication r04_replica all scram-sha-256' >> "$PGDATA/pg_hba.conf"
```

将下面的完整代码保存为 `labs/replication/postgres/standby.sh`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/postgres/standby.sh -->

```bash
set -eu
chmod 700 "$PGDATA"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    pg_basebackup -h primary -U r04_replica -D "$PGDATA" -Fp -Xs -P -R
fi
exec postgres -D "$PGDATA" -c hot_standby=on -c primary_conninfo='host=primary port=5432 user=r04_replica password=r04_replica_only application_name=r04_standby'
```

将下面的完整代码保存为 `labs/replication/postgres/common.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/postgres/common.py -->

```python
from __future__ import annotations

import time
from collections.abc import Callable

import psycopg


def connect(node: str) -> psycopg.Connection:
    ports = {"primary": 55440, "standby": 55441, "subscriber": 55442}
    return psycopg.connect(host="127.0.0.1", port=ports[node], dbname="r04", user="r04", password="r04_local_only", autocommit=True, connect_timeout=3)


def wait_for(check: Callable[[], bool], label: str, seconds: float = 60) -> None:
    expires = time.monotonic() + seconds
    while time.monotonic() < expires:
        if check():
            return
        time.sleep(0.05)
    raise TimeoutError(label)


def scalar(conn: psycopg.Connection, query: str) -> object:
    row = conn.execute(query).fetchone()
    return None if row is None else row[0]
```

将下面的完整代码保存为 `labs/replication/postgres/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/replication/postgres/v0.py -->

```python
from __future__ import annotations

import json
import psycopg

from common import connect, scalar, wait_for


def experiment() -> dict[str, object]:
    with connect("primary") as primary, connect("standby") as standby:
        assert str(scalar(primary, "SHOW server_version")).startswith("16.")
        assert scalar(standby, "SELECT pg_is_in_recovery()") is True
        primary.execute("DROP TABLE IF EXISTS physical_probe")
        primary.execute("CREATE TABLE physical_probe (id int PRIMARY KEY, value text)")
        primary.execute("INSERT INTO physical_probe VALUES (1,'streamed')")
        target = str(scalar(primary, "SELECT pg_current_wal_lsn()"))
        wait_for(lambda: standby.execute("SELECT pg_last_wal_replay_lsn() >= %s::pg_lsn", (target,)).fetchone()[0], "standby replay")
        assert standby.execute("SELECT * FROM physical_probe").fetchall() == [(1, "streamed")]
        try:
            standby.execute("INSERT INTO physical_probe VALUES (2,'forbidden')")
        except psycopg.errors.ReadOnlySqlTransaction:
            readonly = True
        else:
            raise AssertionError("standby accepted write")
        senders = primary.execute("SELECT application_name,state,sync_state FROM pg_stat_replication WHERE application_name='r04_standby'").fetchall()
        assert senders and senders[0][1] == "streaming"
        return {"rows": 1, "read_only": readonly, "target_lsn": target, "senders": senders}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## 运行和检查

```bash
docker compose -f infra/r04.compose.yaml up -d
uv run python labs/replication/postgres/v0.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/replication/postgres -q
```

</details>

测试从这些正文围栏写出临时副本，并通过专用端口执行真实 PostgreSQL 检查；不会用模拟响应代替服务。

