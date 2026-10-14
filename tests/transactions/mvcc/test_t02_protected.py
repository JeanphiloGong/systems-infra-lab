import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.mvcc.protected import protected_schedule


def test_v3_guard_conflict_requires_whole_transaction_retry() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t02_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            first.execute(Path("labs/transactions/mvcc/schema.sql").read_text())
            first.execute(Path("labs/transactions/mvcc/guard.sql").read_text())
            assert protected_schedule(first, second) == (1, False, 1)
            assert first.execute("SELECT on_call FROM doctors ORDER BY id").fetchall() == [(False,), (True,)]
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
