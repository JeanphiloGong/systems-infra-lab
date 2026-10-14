from __future__ import annotations

import argparse
import os
from time import monotonic
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql


def leave(conn: psycopg.Connection, doctor: int, barrier: Barrier | None = None) -> bool:
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
            if barrier is not None:
                barrier.wait(timeout=5)
            if count > 1:
                conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
        return True
    except psycopg.errors.SerializationFailure:
        return False


def concurrent_once(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(leave, first, 1, barrier), pool.submit(leave, second, 2, barrier)]
        outcomes = [future.result(timeout=12) for future in results]
    return outcomes.count(False), first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]


def retry_once(
    conn: psycopg.Connection,
    doctor: int,
    max_retries: int = 3,
    barrier: Barrier | None = None,
) -> tuple[int, bool]:
    if max_retries < 0:
        raise ValueError("max_retries must be nonnegative")
    retries = 0
    while True:
        try:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                count = conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
                allowed = count > 1
                if retries == 0 and barrier is not None:
                    barrier.wait(timeout=5)
                if allowed:
                    conn.execute("UPDATE doctors SET on_call=false WHERE id=%s", (doctor,))
            return retries, allowed
        except psycopg.errors.SerializationFailure:
            retries += 1
            if retries > max_retries:
                raise


def concurrent_retry(
    first: psycopg.Connection, second: psycopg.Connection,
) -> list[tuple[int, bool]]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(retry_once, first, 1, 3, barrier),
            pool.submit(retry_once, second, 2, 3, barrier),
        ]
        return [future.result(timeout=12) for future in futures]


def measure_once(
    first: psycopg.Connection, second: psycopg.Connection, rounds: int = 10,
) -> dict[str, float | int]:
    if rounds < 1:
        raise ValueError("rounds must be positive")
    retries = allowed = 0
    started = monotonic()
    for _ in range(rounds):
        first.execute("UPDATE doctors SET on_call=true")
        outcomes = concurrent_retry(first, second)
        retries += sum(count for count, _ in outcomes)
        allowed += sum(decision for _, decision in outcomes)
    elapsed = monotonic() - started
    remaining = first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0]
    return {
        "operations": rounds * 2, "committed": rounds * 2,
        "aborted_attempts": retries, "retries": retries,
        "allowed": allowed, "refused": rounds * 2 - allowed,
        "remaining": remaining, "elapsed_seconds": elapsed,
        "operations_per_second": rounds * 2 / elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--metrics", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t04_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            if args.metrics:
                print(measure_once(first, second))
            else:
                print(concurrent_retry(first, second) if args.retry else concurrent_once(first, second))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
