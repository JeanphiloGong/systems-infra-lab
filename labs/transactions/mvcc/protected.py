from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def protected_schedule(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, bool, int]:
    conflicts = 0
    try:
        with second.transaction():
            second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()
            with first.transaction():
                first.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                first.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
                if first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1:
                    first.execute("UPDATE doctors SET on_call=false WHERE id=1")
            second.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
            raise AssertionError("expected a stale-snapshot write conflict")
    except psycopg.errors.SerializationFailure:
        conflicts += 1
    with second.transaction():
        second.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        second.execute("UPDATE roster_guard SET version=version+1 WHERE id=1")
        allowed = second.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] > 1
        if allowed:
            second.execute("UPDATE doctors SET on_call=false WHERE id=2")
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return conflicts, allowed, remaining


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
            first.execute(Path(__file__).with_name("guard.sql").read_text())
            print(protected_schedule(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
