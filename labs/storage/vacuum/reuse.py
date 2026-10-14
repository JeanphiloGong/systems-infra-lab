from __future__ import annotations

import os

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema


def reuse(conn: psycopg.Connection) -> tuple[int, int, int, int]:
    before = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    conn.execute("DELETE FROM items WHERE id<=800")
    conn.execute("VACUUM (TRUNCATE FALSE) items")
    cleaned = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    conn.execute("INSERT INTO items SELECT i,0 FROM generate_series(1,800) AS i")
    after = conn.execute("SELECT pg_relation_size('items')").fetchone()[0]
    count = conn.execute("SELECT count(*) FROM items").fetchone()[0]
    return before, cleaned, after, count


def main() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            print(reuse(conn))
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
