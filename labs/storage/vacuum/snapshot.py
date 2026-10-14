from __future__ import annotations

import os

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema


def observe(reader: psycopg.Connection, writer: psycopg.Connection) -> tuple[int, int, int]:
    with reader.transaction():
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        before = reader.execute("SELECT sum(value) FROM items").fetchone()[0]
        writer.execute("UPDATE items SET value=1")
        writer.execute("VACUUM items")
        old_snapshot = reader.execute("SELECT sum(value) FROM items").fetchone()[0]
        current = writer.execute("SELECT sum(value) FROM items").fetchone()[0]
    writer.execute("VACUUM items")
    assert before == old_snapshot
    return old_snapshot, current, reader.execute("SELECT sum(value) FROM items").fetchone()[0]


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as reader, psycopg.connect(dsn, autocommit=True) as writer:
        schema = create_schema(writer)
        try:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            print(observe(reader, writer))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
