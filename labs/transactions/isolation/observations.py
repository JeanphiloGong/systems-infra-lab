from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.isolation.transfer import transfer


def dirty_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "READ UNCOMMITTED"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        with writer.transaction(force_rollback=True):
            writer.execute("UPDATE accounts SET balance=70 WHERE id=1")
            own = writer.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
            other = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        after = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
    return own, other, after


def read_skew(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "REPEATABLE READ"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        first = reader.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        transfer(writer, 1, 2, 30)
        second = reader.execute("SELECT balance FROM accounts WHERE id=2").fetchone()[0]
        single_statement = reader.execute("SELECT sum(balance) FROM accounts").fetchone()[0]
    return first, second, single_statement


def phantom_read(writer: psycopg.Connection, reader: psycopg.Connection, level: str) -> tuple[int, int, int]:
    if level not in {"READ COMMITTED", "REPEATABLE READ"}:
        raise ValueError("unsupported isolation level")
    with reader.transaction():
        reader.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL " + level))
        before = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
        with writer.transaction():
            writer.execute("INSERT INTO accounts VALUES (3, 50)")
        after = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    fresh = reader.execute("SELECT count(*) FROM accounts WHERE balance >= 50").fetchone()[0]
    return before, after, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe overlapping PostgreSQL transactions")
    parser.add_argument("--scenario", choices=["dirty", "skew", "phantom"], default="dirty")
    parser.add_argument("--level", choices=["READ COMMITTED", "READ UNCOMMITTED", "REPEATABLE READ"], default="READ COMMITTED")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as writer, psycopg.connect(dsn, autocommit=True, connect_timeout=5) as reader:
        schema = "t01_" + uuid4().hex
        writer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for conn in (writer, reader):
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("SET statement_timeout = '5s'")
        try:
            writer.execute(Path(__file__).with_name("schema.sql").read_text())
            if args.scenario == "dirty":
                print(dirty_read(writer, reader, args.level))
            elif args.scenario == "skew":
                print(read_skew(writer, reader, args.level))
            else:
                print(phantom_read(writer, reader, args.level))
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
