from __future__ import annotations

import os

from psycopg_pool import ConnectionPool


def make_pool(min_size: int = 0, max_size: int = 4, timeout: float = 1.0, max_waiting: int = 32) -> ConnectionPool:
    if min_size < 0 or max_size < 1 or min_size > max_size or timeout <= 0 or max_waiting < 1:
        raise ValueError("invalid pool bounds")
    return ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        max_waiting=max_waiting,
        open=True,
    )


if __name__ == "__main__":
    pool = make_pool(min_size=1, max_size=2)
    try:
        with pool.connection() as connection:
            print(connection.execute("SELECT 1").fetchone()[0])
    finally:
        pool.close()
