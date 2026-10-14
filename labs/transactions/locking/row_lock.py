from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import os
from pathlib import Path
from threading import Event
from time import monotonic
from uuid import uuid4

import psycopg
from psycopg import sql


def row_lock(owner: psycopg.Connection, waiter: psycopg.Connection, observer: psycopg.Connection) -> tuple[int, float, float]:
    """Use fresh autocommit connections sharing the initialized inventory schema."""
    entered = Event()

    def decrement() -> float:
        with waiter.transaction():
            waiter.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            entered.set()
            start = monotonic()
            quantity = waiter.execute("SELECT quantity FROM inventory WHERE id=1 FOR UPDATE").fetchone()[0]
            waited = monotonic() - start
            if quantity > 0:
                waiter.execute("UPDATE inventory SET quantity=%s WHERE id=1", (quantity - 1,))
        return waited

    with ThreadPoolExecutor(max_workers=1) as pool:
        with owner.transaction():
            quantity = owner.execute("SELECT quantity FROM inventory WHERE id=1 FOR UPDATE").fetchone()[0]
            held_start = monotonic()
            future = pool.submit(decrement)
            if not entered.wait(timeout=5):
                raise TimeoutError("waiter never entered")
            deadline = monotonic() + 5
            while True:
                blockers = observer.execute("SELECT pg_blocking_pids(%s)", (waiter.info.backend_pid,)).fetchone()[0]
                if owner.info.backend_pid in blockers:
                    break
                if monotonic() >= deadline:
                    raise TimeoutError("waiter never blocked on owner")
            if quantity > 0:
                owner.execute("UPDATE inventory SET quantity=%s WHERE id=1", (quantity - 1,))
            held = monotonic() - held_start
        waited = future.result(timeout=5)
    final = observer.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0]
    return final, waited, held


def main() -> None:
    with ExitStack() as stack:
        connections = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(3)]
        owner = connections[0]
        schema = "t03_" + uuid4().hex
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in connections:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            owner.execute(Path(__file__).with_name("schema.sql").read_text())
            final, waited, held = row_lock(*connections)
            print(f"quantity={final} wait_seconds={waited:.6f} hold_seconds={held:.6f}")
        finally:
            owner.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
