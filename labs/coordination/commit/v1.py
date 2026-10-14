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
