from __future__ import annotations

import os

from psycopg_pool import ConnectionPool, PoolTimeout


def main() -> None:
    pool = ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=0,
        max_size=1,
        timeout=0.2,
        open=True,
    )
    try:
        with pool.connection() as held:
            held.execute("SELECT 1")
            try:
                with pool.connection():
                    raise AssertionError("the second checkout should wait")
            except PoolTimeout:
                print("bounded exhaustion observed")

        try:
            with pool.connection() as connection:
                connection.execute("SELECT 1")
                raise RuntimeError("simulated handler failure")
        except RuntimeError:
            pass

        with pool.connection() as recovered:
            print({"recovered": recovered.execute("SELECT 1").fetchone()[0]})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
