import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from labs.transactions.locking.deadlock import deadlock, ordered


def test_victim_rollback_retry_and_ordered_locks() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as a, psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as b:
        schema = "t03_" + uuid4().hex
        a.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for c in (a, b):
                c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                c.execute("SET statement_timeout='8s'")
            a.execute(Path("labs/transactions/locking/schema.sql").read_text())
            a.execute("INSERT INTO inventory VALUES (2,10,0)")
            assert deadlock(a, b) == (1, 8, 8)
            a.execute("UPDATE inventory SET quantity=10")
            assert ordered(a, b) == (8, 8)
        finally:
            a.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
