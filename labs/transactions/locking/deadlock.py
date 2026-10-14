from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql


def decrement_pair(conn: psycopg.Connection, order: tuple[int, int], barrier: Barrier | None = None) -> bool:
    try:
        with conn.transaction():
            for index, item in enumerate(order):
                quantity = conn.execute("SELECT quantity FROM inventory WHERE id=%s FOR UPDATE", (item,)).fetchone()[0]
                if index == 0 and barrier is not None:
                    barrier.wait(timeout=5)
                if quantity <= 0:
                    raise ValueError("insufficient stock")
                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=%s", (item,))
        return True
    except psycopg.errors.DeadlockDetected:
        return False


def deadlock(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int, int]:
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(decrement_pair, first, (1, 2), barrier)
        b = pool.submit(decrement_pair, second, (2, 1), barrier)
        outcomes = [a.result(timeout=12), b.result(timeout=12)]
    if sum(outcomes) != 1:
        raise AssertionError("expected exactly one deadlock victim")
    loser = first if not outcomes[0] else second
    if not decrement_pair(loser, (1, 2)):
        raise AssertionError("ordered retry failed")
    quantities = first.execute("SELECT quantity FROM inventory ORDER BY id").fetchall()
    return outcomes.count(False), quantities[0][0], quantities[1][0]


def ordered(first: psycopg.Connection, second: psycopg.Connection) -> tuple[int, int]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(decrement_pair, first, (1, 2))
        b = pool.submit(decrement_pair, second, (1, 2))
        if not a.result(timeout=12) or not b.result(timeout=12):
            raise AssertionError("ordered run deadlocked")
    values = first.execute("SELECT quantity FROM inventory ORDER BY id").fetchall()
    return values[0][0], values[1][0]


def main() -> None:
    with ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(2)]
        first = connections[0]
        schema = "t03_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in connections:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path(__file__).with_name("schema.sql").read_text())
            first.execute("INSERT INTO inventory VALUES (2,10,0)")
            print("victims and retried quantities:", deadlock(*connections))
            first.execute("UPDATE inventory SET quantity=10")
            print("ordered quantities:", ordered(*connections))
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
