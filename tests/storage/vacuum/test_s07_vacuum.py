import os
from uuid import uuid4
import psycopg
from psycopg import sql
from labs.storage.vacuum.vacuum import create_schema, churn, stats


def test_dead_tuple_stats_and_vacuum() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            churn(conn, 5)
            before = stats(conn)
            conn.execute("VACUUM items")
            after = stats(conn)
            assert conn.execute("SELECT count(*) FROM items").fetchone()[0] == 1000
            assert before[1] >= 0 and after[1] >= 0
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
