from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def write_skew(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    with first.transaction():
        first.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        with second.transaction():
            second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            first_count = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            second_count = second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            if first_count > 1:
                first.execute("UPDATE doctors SET on_call=false WHERE id=1")
            if second_count > 1:
                second.execute("UPDATE doctors SET on_call=false WHERE id=2")
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return first_count, second_count, remaining


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as first, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as second:
        schema = "t02_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(write_skew(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
