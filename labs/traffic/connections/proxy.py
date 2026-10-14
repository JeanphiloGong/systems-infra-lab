import os
import psycopg


def observe() -> dict[str, object]:
    dsn = os.environ["SYSTEMS_LAB_POOL_URL"]
    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as first, psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as second:
        with first.transaction():
            first_pid = first.execute("SELECT pg_backend_pid()").fetchone()[0]
            first.execute("SET LOCAL application_name = 'f01-request'")
            first.execute("CREATE TEMP TABLE f01_session_only (value integer)")
        with second.transaction():
            second_pid = second.execute("SELECT pg_backend_pid()").fetchone()[0]
            assert first_pid == second_pid
            assert second.execute("SHOW application_name").fetchone()[0] != "f01-request"
            assert second.execute("SELECT to_regclass('pg_temp.f01_session_only')").fetchone()[0] is None
    return {"clients": 2, "backend_pids": [first_pid, second_pid], "session_table_survived": False}


if __name__ == "__main__":
    print(observe())
