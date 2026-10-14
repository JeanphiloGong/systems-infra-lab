import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from labs.transactions.isolation.acid import constraint_trace
from labs.transactions.isolation.transfer import transfer


def test_v4_constraint_and_reconnect() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    schema = "t01_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            admin.execute(Path("labs/transactions/isolation/schema.sql").read_text())
            assert constraint_trace(admin) == (200, 199)
            admin.execute("UPDATE accounts SET balance=100")
            with psycopg.connect(dsn, autocommit=True) as writer:
                writer.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                transfer(writer, 1, 2, 30)
            with psycopg.connect(dsn, autocommit=True) as reader:
                reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                assert reader.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(70,), (130,)]
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
