# D03 v0: a local commit cannot transfer money across databases

Start with Alice and Bob, each holding 100 units in a different PostgreSQL database. Transfer 30: debit Alice, then credit Bob. Our invariant is a final total of 200. Two ordinary transactions make each local change atomic but do not make the pair atomic.

Run this only against a disposable PostgreSQL server. Set D03_DATABASE_URL to its admin database; the role needs CREATEDB and ownership of its new databases. The helper creates two unique databases on that one server. They are independent transaction resources, but this is not a two-host failure experiment.

## Commit the debit and lose the credit

The source connection context commits on exit. The destination raises after its UPDATE but before its context exits, so PostgreSQL rolls it back. This is a deterministic application failure; it does not simulate a disk failure. Observe [70, 100], not [70, 130]. The missing 30 makes the atomicity problem visible.

Create the following complete checkpoint files in labs/coordination/commit. pg.py owns setup, observation and cleanup only; it does not coordinate commits. Every experiment has its own database names and cleanup touches only those names.

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

<!-- checkpoint: labs/coordination/commit/v0.py -->

```python
from __future__ import annotations

import json
import psycopg

from pg import balances, resources


def experiment() -> dict[str, object]:
    with resources() as dsns:
        with psycopg.connect(dsns[0]) as source:
            source.execute("UPDATE account SET balance = balance - 30 WHERE id = 1")
        try:
            with psycopg.connect(dsns[1]) as target:
                target.execute("UPDATE account SET balance = balance + 30 WHERE id = 1")
                raise RuntimeError("second database fails before commit")
        except RuntimeError:
            pass
        result = balances(dsns)
        assert result == [70, 100]
        return {"balances": result, "total": sum(result)}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Checkpoint

Run from the repository root:

```bash
uv run python labs/coordination/commit/v0.py
```

The replay suite extracts only these complete fences into a fresh temporary directory and verifies the reported behavior. Run `uv run python -m pytest tests/coordination/commit -q` with the disposable database configured.

Before moving on, verify the total is 170 and explain which local transaction committed. v1 must prevent this decision being made before both resources are ready.

