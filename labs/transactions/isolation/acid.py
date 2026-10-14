from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.isolation.transfer import transfer


def constraint_trace(conn: psycopg.Connection) -> tuple[int, int]:
    try:
        with conn.transaction():
            conn.execute("UPDATE accounts SET balance=-1 WHERE id=1")
    except psycopg.errors.CheckViolation:
        pass
    after_rejection = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    with conn.transaction():
        conn.execute("UPDATE accounts SET balance=balance-1 WHERE id=1")
    after_legal_sql = conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    return after_rejection, after_legal_sql


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    schema = "t01_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            admin.execute(Path(__file__).with_name("schema.sql").read_text())
            print("constraint, business total:", constraint_trace(admin))
            admin.execute("UPDATE accounts SET balance=100")
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer:
                writer.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                transfer(writer, 1, 2, 30)
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader:
                reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                print("after reconnect:", reader.execute("SELECT balance FROM accounts ORDER BY id").fetchall())
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
