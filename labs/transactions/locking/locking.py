from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def lost_update(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    a = first.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    b = second.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    first.execute("UPDATE inventory SET quantity=%s WHERE id=1", (a - 1,))
    second.execute("UPDATE inventory SET quantity=%s WHERE id=1", (b - 1,))
    return a, b, first.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]


def optimistic(conn: psycopg.Connection) -> tuple[int, int]:
    row = conn.execute("SELECT quantity,version FROM inventory WHERE id=1").fetchone()
    statement = (
        "UPDATE inventory SET quantity=quantity-1,version=version+1 "
        "WHERE id=1 AND version=%s AND quantity>0"
    )
    changed = conn.execute(statement, (row[1],)).rowcount
    conflict = conn.execute(statement, (row[1],)).rowcount
    return changed, conflict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimistic", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t03_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            print(optimistic(first) if args.optimistic else lost_update(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
