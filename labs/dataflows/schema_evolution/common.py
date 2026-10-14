from __future__ import annotations

import os

import psycopg


DSN = os.getenv("E02_DATABASE_URL", "postgresql://e02:e02_local_only@127.0.0.1:55451/e02")


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN, autocommit=True, connect_timeout=3)


def reset(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS schema_backfill_checkpoint, migration_clients")
    conn.execute("DROP TABLE IF EXISTS profiles")
