from contextlib import ExitStack
import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql

from labs.transactions.locking.row_lock import row_lock


def test_two_locked_decrements() -> None:
    with ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(3)]
        owner, waiter, observer = connections
        schema = "t03_" + uuid4().hex
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in connections:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            owner.execute(Path("labs/transactions/locking/schema.sql").read_text())
            final, waited, held = row_lock(owner, waiter, observer)
            assert final == 8
            assert waited >= 0 and held >= 0
        finally:
            owner.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
