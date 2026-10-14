# A03 v2：由 Patroni 检测故障并切换

两个 PostgreSQL 16 节点由 Patroni 4.1.5 管理，独立 etcd 3.5.17 提供领导锁。容器只属于 systems-a03-patroni 实验。这里运行真实进程与 SQL，不依赖早期模型的 generation 字段。

先确认副本读到已确认写入，再断开当前领导者的 Docker 网络。客户端按 250ms 间隔查找新主并尝试写入。故障窗口用 monotonic 测量，从注入故障到新主首次成功写入；记录客户端尝试次数。异步复制下主动等待追平让样本 RPO 为 0，不代表所有故障都零丢失。

断网不停止 Patroni 容器。Patroni 失去 DCS 后自行停止 PostgreSQL，脚本通过 docker exec 在旧容器内访问 localhost，必须拒绝写入；仅证明外部端口断开是不够的。该行为依赖 Patroni 进程及时响应，不是硬件 STONITH，也不覆盖整个主机冻结。

恢复网络后旧主可能存在分叉 timeline。实验显式使用 Patroni reinitialize 克隆新主，再核对 recovery=true 和新提交内容。随后调用 REST switchover，并在回切后的主节点提交一笔写入。单 etcd 是实验控制节点，不能用此拓扑承诺 DCS 高可用。

v1 依赖人发现故障；本版关注谁决定切换以及多久才可确认恢复。共享 probe 中从 started=monotonic() 到新主 INSERT 成功的循环是本版核心，client_attempts 是客户端探测次数，不是数据库事务重试次数。代码也执行 v3/v4 的完整隔离与重建收尾，因此这是一份共享实验，不是本版独立实现了全部 HA。

patroni.yml 的 ttl=20 是 DCS 领导锁生存期，loop_wait=3 是控制循环间隔，retry_timeout=3 是重试窗口。它们不能简单相加当作确定 RTO；锁剩余时间、调度、提升和 SQL 成功共同决定实测。客户端每 0.25 秒探测也影响观测精度。

网络分区、CPU 长暂停、DCS 不可达都可能与主机宕机表现相同。检测器不能据超时证明旧主死亡。缩短阈值可能更快恢复，也更容易因延迟误判；失去领导锁时旧主停止服务牺牲局部可用性以避免双写。单 etcd 故障不在本次自动恢复证明范围。不要随意修改阈值后沿用已有数字，参数对照需独立重跑。

检查已记录输出的 rto_seconds、client_attempts 和 acknowledged_lost；RPO=0 仅限预先追平的样本。下一版检查网络隔离时旧容器仍活着是否能本地写入，这是检测成功尚未回答的问题。

## 运行和清理

准备 etcd 3.5.17 Linux amd64 可执行文件并设置 ETCD_BINARY。完整配置和脚本如下。配置中的公开密码仅用于绑定 localhost 的 disposable 实验。Docker Desktop 的 host.docker.internal 转发在本次环境中已验证。

```bash
ETCD_BINARY=/tmp/etcd-v3.5.17-linux-amd64/etcd bash infra/a03-patroni/lab.sh up
uv run python -m labs.recovery.ha.patroni_probe
bash infra/a03-patroni/lab.sh down
```

启动后等待两个 /patroni 返回 running 和 primary/replica，再执行 probe。清理命令删除本实验两节点卷和 etcd 容器。不要指向其他项目或现有业务实例。

<!-- checkpoint: labs/recovery/ha/patroni_probe.py -->

```python
"""Run against the dedicated infra/a03-patroni stack; mutate only its two nodes."""
import json
import subprocess
import time
import urllib.request

import psycopg

NETWORK = 'systems-a03-patroni_default'
PORTS = {'p1': 55461, 'p2': 55462}
REST = {'p1': 18081, 'p2': 18082}


def docker(*args):
    return subprocess.run(['docker', *args], text=True, capture_output=True, timeout=30)


def api(node, path='/patroni', payload=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f'http://127.0.0.1:{REST[node]}' + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=5) as response:
        body = response.read().decode()
    return json.loads(body) if path == '/patroni' else body


def wait(check, seconds=90):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (OSError, psycopg.Error) as exc:
            last = exc
        time.sleep(0.25)
    raise TimeoutError(str(last))


def sql(node, query, params=None):
    with psycopg.connect(host='127.0.0.1', port=PORTS[node], user='postgres',
                         password='postgres', dbname='postgres',
                         autocommit=True, connect_timeout=2) as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchall() if cursor.description else []


def run():
    old = next(node for node in PORTS if api(node)['role'] == 'primary')
    new = next(node for node in PORTS if node != old)
    sql(old, 'CREATE TABLE IF NOT EXISTS a03_live(id text PRIMARY KEY, value text)')
    key = str(time.time_ns())
    sql(old, 'INSERT INTO a03_live VALUES (%s,%s)', (key, 'acknowledged'))
    wait(lambda: sql(new, 'SELECT value FROM a03_live WHERE id=%s', (key,)) == [('acknowledged',)])
    # Async replication is deliberately caught up before failure; RPO zero is observed, not guaranteed.
    identifier = f'systems-a03-patroni-{old}-1'
    started = time.monotonic()
    disconnected = False
    retries = 0
    try:
        result = docker('network', 'disconnect', NETWORK, identifier)
        result.check_returncode()
        disconnected = True
        while True:
            retries += 1
            try:
                if api(new)['role'] == 'primary':
                    sql(new, 'INSERT INTO a03_live VALUES (%s,%s)', (key + '-new', 'after'))
                    break
            except (OSError, psycopg.Error):
                pass
            if time.monotonic() - started > 90:
                raise TimeoutError('automatic promotion')
            time.sleep(0.25)
        rto = time.monotonic() - started
        probe = docker('exec', '-e', 'PGPASSWORD=postgres', identifier,
                       'psql', '-h', '127.0.0.1', '-U', 'postgres', '-c',
                       "CREATE TABLE a03_forbidden(id int)")
        assert probe.returncode != 0, 'isolated old primary remains writable'
        assert docker('inspect', '-f', '{{.State.Running}}', identifier).stdout.strip() == 'true'
        retained = sql(new, 'SELECT value FROM a03_live WHERE id=%s', (key,))
        assert retained == [('acknowledged',)]
        docker('network', 'connect', '--alias', old, NETWORK, identifier).check_returncode()
        disconnected = False
        docker('restart', '-t', '5', identifier).check_returncode()
        wait(lambda: api(old))
        # Explicit rebuild is used instead of assuming divergent timelines can follow directly.
        api(old, '/reinitialize', {'force': True})
        wait(lambda: sql(old, 'SELECT pg_is_in_recovery()') == [(True,)])
        wait(lambda: sql(old, 'SELECT value FROM a03_live WHERE id=%s', (key + '-new',)) == [('after',)])
        switched = time.monotonic()
        api(new, '/switchover', {'leader': new, 'candidate': old})
        wait(lambda: api(old)['role'] == 'primary')
        sql(old, 'INSERT INTO a03_live VALUES (%s,%s)', (key + '-return', 'returned'))
        return dict(old=old, new=new, rto_seconds=round(rto, 3), acknowledged_lost=0,
                    client_attempts=retries, old_process_alive=True, old_write_rejected=True,
                    rejoin='basebackup via Patroni reinitialize',
                    cutback_seconds=round(time.monotonic() - switched, 3))
    finally:
        if disconnected:
            docker('network', 'connect', '--alias', old, NETWORK, identifier)


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
```

<!-- checkpoint: infra/a03-patroni/Dockerfile -->

```dockerfile
FROM postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages 'patroni[etcd3]==4.1.5' 'psycopg[binary]==3.3.6'
```

<!-- checkpoint: infra/a03-patroni/compose.yaml -->

```yaml
name: systems-a03-patroni
services:
  p1:
    build: .
    user: postgres
    hostname: p1
    extra_hosts: ["host.docker.internal:host-gateway"]
    environment:
      PATRONI_NAME: p1
      PATRONI_SCOPE: a03
      PATRONI_ETCD3_HOSTS: host.docker.internal:22379
      PATRONI_RESTAPI_CONNECT_ADDRESS: p1:8008
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: p1:5432
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data/pgdata
      PGDATA: /var/lib/postgresql/data/pgdata
      PATRONI_POSTGRESQL_PGPASS: /tmp/pgpass
      PATRONI_SUPERUSER_USERNAME: postgres
      PATRONI_SUPERUSER_PASSWORD: postgres
      PATRONI_REPLICATION_USERNAME: replicator
      PATRONI_REPLICATION_PASSWORD: replicator
    ports: ["127.0.0.1:55461:5432", "127.0.0.1:18081:8008"]
    command: ["patroni", "/etc/patroni.yml"]
    volumes: ["p1-data:/var/lib/postgresql/data", "./patroni.yml:/etc/patroni.yml:ro"]
  p2:
    build: .
    user: postgres
    hostname: p2
    extra_hosts: ["host.docker.internal:host-gateway"]
    environment:
      PATRONI_NAME: p2
      PATRONI_SCOPE: a03
      PATRONI_ETCD3_HOSTS: host.docker.internal:22379
      PATRONI_RESTAPI_CONNECT_ADDRESS: p2:8008
      PATRONI_POSTGRESQL_CONNECT_ADDRESS: p2:5432
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data/pgdata
      PGDATA: /var/lib/postgresql/data/pgdata
      PATRONI_SUPERUSER_USERNAME: postgres
      PATRONI_SUPERUSER_PASSWORD: postgres
      PATRONI_REPLICATION_USERNAME: replicator
      PATRONI_REPLICATION_PASSWORD: replicator
    ports: ["127.0.0.1:55462:5432", "127.0.0.1:18082:8008"]
    command: ["patroni", "/etc/patroni.yml"]
    volumes: ["p2-data:/var/lib/postgresql/data", "./patroni.yml:/etc/patroni.yml:ro"]
volumes:
  p1-data:
  p2-data:
```

<!-- checkpoint: infra/a03-patroni/patroni.yml -->

```yaml
scope: a03
namespace: /service/
restapi:
  listen: 0.0.0.0:8008
bootstrap:
  dcs:
    ttl: 20
    loop_wait: 3
    retry_timeout: 3
    postgresql:
      use_pg_rewind: false
      use_slots: true
      pg_hba:
        - host replication replicator 0.0.0.0/0 md5
        - host all all 0.0.0.0/0 md5
      parameters:
        wal_level: replica
        hot_standby: 'on'
        wal_keep_size: 64MB
  initdb:
    - encoding: UTF8
    - locale: C
postgresql:
  listen: 0.0.0.0:5432
tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

<!-- checkpoint: infra/a03-patroni/lab.sh -->

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  up)
    : "${ETCD_BINARY:?Set ETCD_BINARY to etcd 3.5.17 absolute executable path}"
    docker run -d --name a03-etcd-local -p 127.0.0.1:22379:2379 \
      -v "$ETCD_BINARY:/usr/local/bin/etcd:ro" \
      alpine:latest /usr/local/bin/etcd --name a03 --data-dir /tmp/etcd-data \
      --listen-client-urls http://0.0.0.0:2379 \
      --advertise-client-urls http://host.docker.internal:22379
    docker compose -f compose.yaml up -d --build
    ;;
  down)
    # Only this disposable A03 stack is removed; its data is intentionally reset.
    docker compose -f compose.yaml down --volumes
    docker rm -f a03-etcd-local
    ;;
  *) echo 'usage: bash lab.sh up|down' >&2; exit 2 ;;
esac
```

## 检查点

必须观察 old_process_alive=true、old_write_rejected=true、acknowledged_lost=0、正的 rto_seconds/cutback_seconds，并检查客户端尝试次数。机器负载与 lease/重试间隔会影响具体时长，不要求固定秒数。一次演练不能推算年度可用性。v0 单实例基线与 v1 手动切换仍独立验证；本篇证明成熟组件的自动切换、网络分区拒写及重新加入。


<!-- checkpoint: labs/recovery/ha/model.py -->

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Replica:
    name: str
    role: str = "standby"
    generation: int = 0
    rows: dict[str, str] = field(default_factory=dict)
    alive: bool = True
    isolated: bool = False
    last_heartbeat: int = 0


class HACluster:
    """A two-replica failover model with explicit fencing and logical time."""

    def __init__(self) -> None:
        self.nodes = {"a": Replica("a", role="primary"), "b": Replica("b")}
        self.primary = "a"
        self.generation = 1
        self.nodes["a"].generation = self.generation
        self.now = 0
        self.events: list[dict[str, object]] = []

    def write(self, node: str, key: str, value: str) -> None:
        replica = self.nodes[node]
        if not replica.alive or replica.isolated or replica.role != "primary" or replica.generation != self.generation:
            raise RuntimeError("write fenced")
        replica.rows[key] = value
        for peer in self.nodes.values():
            if peer.name != node and peer.alive and not peer.isolated:
                peer.rows = dict(replica.rows)
                peer.generation = self.generation
        self.events.append({"at": self.now, "kind": "write", "node": node, "key": key})

    def isolate(self, node: str) -> None:
        self.nodes[node].isolated = True
        self.events.append({"at": self.now, "kind": "isolate", "node": node})

    def stop(self, node: str) -> None:
        self.nodes[node].alive = False
        self.events.append({"at": self.now, "kind": "stop", "node": node})

    def promote(self, node: str) -> None:
        candidate = self.nodes[node]
        if not candidate.alive or candidate.isolated:
            raise RuntimeError("candidate unavailable")
        old = self.primary
        self.generation += 1
        candidate.role, candidate.generation = "primary", self.generation
        self.primary = node
        self.nodes[old].role = "standby"
        self.events.append({"at": self.now, "kind": "promote", "old": old, "new": node, "generation": self.generation})

    def tick(self, seconds: int, timeout: int = 5) -> None:
        if seconds < 0:
            raise ValueError("logical time cannot go backwards")
        self.now += seconds
        current = self.nodes[self.primary]
        if current.alive and not current.isolated:
            for peer in self.nodes.values():
                if peer.name != self.primary and peer.alive and not peer.isolated:
                    peer.last_heartbeat = self.now
        if not current.alive or current.isolated:
            candidates = [node for node in self.nodes.values() if node.name != self.primary and node.alive and not node.isolated]
            if candidates and self.now - candidates[0].last_heartbeat >= timeout:
                self.promote(candidates[0].name)

    def rejoin(self, node: str) -> None:
        replica = self.nodes[node]
        if replica.alive and not replica.isolated:
            replica.rows = dict(self.nodes[self.primary].rows)
            replica.generation = self.generation
            replica.role = "standby"
            self.events.append({"at": self.now, "kind": "rejoin", "node": node, "generation": self.generation})
```

<!-- checkpoint: labs/recovery/ha/experiment.py -->

```python
import json
import sys

from model import HACluster


def run(version: int):
    cluster = HACluster()
    cluster.write("a", "order", "one")
    if version == 0:
        cluster.stop("a"); cluster.tick(3)
        return {"rto_window": cluster.now, "rpo_rows": cluster.nodes["b"].rows}
    if version == 1:
        cluster.stop("a"); cluster.promote("b"); cluster.write("b", "order", "two")
        return {"primary": cluster.primary, "confirmed": cluster.nodes["b"].rows}
    if version == 2:
        cluster.stop("a"); cluster.tick(6)
        return {"automatic_primary": cluster.primary, "generation": cluster.generation}
    if version == 3:
        cluster.isolate("a"); cluster.promote("b")
        try:
            cluster.write("a", "order", "stale")
        except RuntimeError:
            fenced = True
        else:
            fenced = False
        cluster.write("b", "order", "two")
        return {"old_primary_fenced": fenced, "new_value": cluster.nodes["b"].rows["order"]}
    if version == 4:
        cluster.stop("a"); cluster.promote("b"); cluster.write("b", "order", "two")
        cluster.nodes["a"].alive = True; cluster.rejoin("a"); cluster.promote("a"); cluster.write("a", "order", "three")
        return {"cutover_primary": cluster.primary, "rows": cluster.nodes["a"].rows}
    raise ValueError("version must be 0..4")


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])), sort_keys=True))
```
