from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from threading import Event
from time import monotonic

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema, churn


def compare(reader: psycopg.Connection, worker: psycopg.Connection, observer: psycopg.Connection) -> tuple[int, int, int]:
    churn(worker, 20)
    worker.execute("VACUUM (TRUNCATE FALSE) items")
    ordinary = worker.execute("SELECT pg_relation_size('items')").fetchone()[0]
    entered = Event()

    def full() -> None:
        entered.set()
        worker.execute("VACUUM FULL items")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with reader.transaction():
            reader.execute("SELECT count(*) FROM items").fetchone()
            worker.execute("SET statement_timeout='10s'")
            future = pool.submit(full)
            if not entered.wait(timeout=3):
                raise TimeoutError("FULL worker did not start")
            deadline = monotonic() + 5
            while reader.info.backend_pid not in observer.execute("SELECT pg_blocking_pids(%s)", (worker.info.backend_pid,)).fetchone()[0]:
                if monotonic() >= deadline:
                    raise TimeoutError("FULL did not wait for reader")
        future.result(timeout=12)
    rewritten = worker.execute("SELECT pg_relation_size('items')").fetchone()[0]
    logical = worker.execute("SELECT count(*) FROM items").fetchone()[0]
    return ordinary, rewritten, logical


def main() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as reader, psycopg.connect(dsn, autocommit=True) as worker, psycopg.connect(dsn, autocommit=True) as observer:
        schema = create_schema(worker)
        try:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            print(compare(reader, worker, observer))
        finally:
            worker.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
