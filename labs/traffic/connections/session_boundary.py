from __future__ import annotations

import os

from psycopg_pool import ConnectionPool


def main() -> None:
    pool = ConnectionPool(
        os.environ["SYSTEMS_LAB_DATABASE_URL"],
        min_size=1,
        max_size=1,
        timeout=1.0,
        open=True,
    )
    try:
        with pool.connection() as first:
            first.execute("SET application_name = 'f01-v3'")
            first.execute("SELECT 1")

        with pool.connection() as second:
            # In this installed version, transaction state is reset but this
            # application_name setting persists across the pool return.
            state = second.execute("SELECT current_setting('application_name')").fetchone()[0]
            assert state == "f01-v3"
            print({"reused_session": True, "application_name_after_return": state})

        with pool.connection() as transaction_connection:
            with transaction_connection.transaction():
                transaction_connection.execute("SELECT 1")
            # The transaction is complete before the context returns the session.
            print({"transaction_status": transaction_connection.info.transaction_status.name})
    finally:
        pool.close()


if __name__ == "__main__":
    main()
