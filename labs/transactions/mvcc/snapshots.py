from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def snapshot_timing(reader: psycopg.Connection, writer: psycopg.Connection, *, early_read: bool) -> tuple[bool, bool, bool]:
    with reader.transaction():
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if early_read:
            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        with writer.transaction():
            writer.execute("UPDATE doctors SET on_call=false WHERE id=1")
        if not early_read:
            first = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
        second = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
    fresh = reader.execute("SELECT on_call FROM doctors WHERE id=1").fetchone()[0]
    return first, second, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe snapshot establishment in PostgreSQL")
    parser.add_argument("--early-read", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer:
        schema = "t02_" + uuid4().hex
        reader.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (reader, writer):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            reader.execute(Path(__file__).with_name("schema.sql").read_text())
            print(snapshot_timing(reader, writer, early_read=args.early_read))
        finally:
            reader.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
