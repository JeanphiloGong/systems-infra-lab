from __future__ import annotations

import argparse
import os
from uuid import uuid4

import psycopg
from psycopg import sql


SCHEMA = "CREATE TABLE items (id integer PRIMARY KEY, value integer NOT NULL) WITH (autovacuum_enabled=false)"


def create_schema(conn: psycopg.Connection) -> str:
    schema = "s07_" + uuid4().hex
    conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    conn.execute(SCHEMA)
    conn.execute("INSERT INTO items SELECT i, 0 FROM generate_series(1,1000) AS i")
    return schema


def stats(conn: psycopg.Connection) -> tuple[int, int, int]:
    conn.execute("SELECT pg_stat_force_next_flush()")
    conn.execute("SELECT pg_stat_clear_snapshot()")
    row = conn.execute("SELECT n_live_tup, n_dead_tup, pg_total_relation_size('items') FROM pg_stat_user_tables WHERE relid='items'::regclass").fetchone()
    if row is None:
        raise RuntimeError("items statistics unavailable")
    return tuple(int(value) for value in row)


def churn(conn: psycopg.Connection, rounds: int) -> None:
    if rounds < 1:
        raise ValueError("rounds must be positive")
    for _ in range(rounds):
        conn.execute("UPDATE items SET value=value+1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--vacuum", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            churn(conn, args.rounds)
            print("logical rows:", conn.execute("SELECT count(*) FROM items").fetchone()[0])
            before = stats(conn)
            if args.full:
                conn.execute("VACUUM FULL items")
            elif args.vacuum:
                conn.execute("VACUUM items")
            after = stats(conn)
            print({"before": before, "after": after})
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
