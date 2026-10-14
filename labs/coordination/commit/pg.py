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
