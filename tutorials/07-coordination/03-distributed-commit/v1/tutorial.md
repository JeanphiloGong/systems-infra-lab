# D03 v1: prepare both resources before deciding

v0 lost 30 units because Alice committed before Bob was ready. PostgreSQL prepared transactions add a durable intermediate state: both resources first promise they can commit, without making their updates visible to ordinary readers. Only then does the coordinator tell both to commit.

## Enable prepared transactions on a disposable server

PostgreSQL commonly starts with max_prepared_transactions=0. Restart the isolated tutorial server with at least 2; these examples use 20. A real deployment must size this setting and coordinate standby configuration. Never enable or experiment on a production instance for this lesson.

The setup helper fails early if the capacity is below 2. PREPARE TRANSACTION and COMMIT PREPARED use quoted global identifiers, and COMMIT PREPARED runs outside an ordinary transaction block. The connected role owns the prepared transactions. Keep the server available until cleanup finishes.

## Separate readiness from visibility

Both connections BEGIN and update their account. Each PREPARE releases the client transaction while PostgreSQL retains the prepared state and locks. Separate read connections still see [100, 100]; pg_prepared_xacts reports two prepared transactions. The coordinator then commits both and the readers see [70, 130].

This version deliberately covers only the normal coordinator path. There is no durable coordinator decision yet: killing it mid-commit is unsafe. v2 adds that missing obligation. The cleanup helper rolls back leftovers only to dismantle isolated experiments; it is not a production recovery policy.

将下面的完整代码保存为 `labs/coordination/commit/pg.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/commit/pg.py -->

```python
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def resources(prepared: bool = False) -> Iterator[list[str]]:
    """Create two disposable databases on the configured lab server."""
    dsn = os.environ["D03_DATABASE_URL"]
    names: list[str] = []
    with psycopg.connect(dsn, autocommit=True) as admin:
        if prepared and int(admin.execute("SHOW max_prepared_transactions").fetchone()[0]) < 2:
            raise RuntimeError("D03 requires max_prepared_transactions >= 2; restart a disposable server")
        try:
            participants = []
            for _ in range(2):
                name = "d03_" + uuid4().hex
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                names.append(name)
                participant = make_conninfo(dsn, dbname=name)
                participants.append(participant)
                with psycopg.connect(participant, autocommit=True) as conn:
                    conn.execute("CREATE TABLE account (id int PRIMARY KEY, balance int NOT NULL CHECK (balance >= 0))")
                    conn.execute("INSERT INTO account VALUES (1, 100)")
            yield participants
        finally:
            # Resolve only this experiment's transactions before dropping its databases.
            for name in names:
                with psycopg.connect(make_conninfo(dsn, dbname=name), autocommit=True) as conn:
                    for (gid,) in conn.execute("SELECT gid FROM pg_prepared_xacts WHERE database = current_database()").fetchall():
                        conn.execute(sql.SQL("ROLLBACK PREPARED {}").format(sql.Literal(gid)))
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def balances(dsns: list[str]) -> list[int]:
    result = []
    for dsn in dsns:
        with psycopg.connect(dsn) as conn:
            result.append(conn.execute("SELECT balance FROM account WHERE id = 1").fetchone()[0])
    return result
```

将下面的完整代码保存为 `labs/coordination/commit/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/commit/v1.py -->

```python
from __future__ import annotations

from contextlib import ExitStack
import json
from uuid import uuid4

import psycopg
from psycopg import sql

from pg import balances, resources


def experiment() -> dict[str, object]:
    with resources(prepared=True) as dsns, ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(dsn, autocommit=True)) for dsn in dsns]
        gids = ["d03_" + uuid4().hex for _ in dsns]
        for conn, delta, gid in zip(connections, [-30, 30], gids):
            conn.execute("BEGIN")
            conn.execute("UPDATE account SET balance = balance + %s WHERE id = 1", (delta,))
            conn.execute(sql.SQL("PREPARE TRANSACTION {}").format(sql.Literal(gid)))
        before = balances(dsns)
        prepared = sum(conn.execute("SELECT count(*) FROM pg_prepared_xacts WHERE database = current_database()").fetchone()[0] for conn in connections)
        assert before == [100, 100] and prepared == 2
        for conn, gid in zip(connections, gids):
            conn.execute(sql.SQL("COMMIT PREPARED {}").format(sql.Literal(gid)))
        after = balances(dsns)
        assert after == [70, 130]
        return {"before": before, "prepared": prepared, "after": after}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Checkpoint

Run from the repository root:

```bash
uv run python labs/coordination/commit/v1.py
```

The optional reference-branch replay suite extracts only these complete fences into a fresh temporary directory and verifies the reported behavior. Optional: use [参考分支检查](../../../../docs/reference-checks.md) with the disposable database configured.

Before moving on, verify both prepared updates are invisible to readers, both become visible after commit, and no prepared transactions remain. v2 addresses the missing durable decision on coordinator failure.

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/commit -q
```

</details>
