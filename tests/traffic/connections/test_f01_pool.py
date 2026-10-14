import os
from time import monotonic

import pytest
from psycopg_pool import PoolTimeout

from labs.traffic.connections.direct import connect_query
from labs.traffic.connections.pool import make_pool
from labs.traffic.connections.proxy import observe


def test_direct_connection_query() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_DATABASE_URL")
    value, elapsed = connect_query()
    assert value == 1
    assert elapsed >= 0

def test_reuses_connection() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_DATABASE_URL")
    pool = make_pool(max_size=1)
    try:
        with pool.connection() as first:
            first.execute("SELECT 1")
        with pool.connection() as second:
            assert second is first
    finally:
        pool.close()


def test_exception_resets_session() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_DATABASE_URL")
    pool = make_pool(max_size=1)
    try:
        with pytest.raises(RuntimeError):
            with pool.connection() as connection:
                connection.execute("SELECT 1")
                raise RuntimeError("handler failed")
        with pool.connection() as connection:
            connection.execute("SELECT 1")
    finally:
        pool.close()


def test_waiter_times_out_when_pool_is_exhausted() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_DATABASE_URL")
    pool = make_pool(max_size=1, timeout=0.1)
    try:
        with pool.connection():
            started = monotonic()
            with pytest.raises(PoolTimeout):
                with pool.connection():
                    pass
            assert monotonic() - started >= 0.08
    finally:
        pool.close()


def test_context_manager_returns_connection_after_body_failure() -> None:
    if "SYSTEMS_LAB_DATABASE_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_DATABASE_URL")
    pool = make_pool(max_size=1)
    try:
        with pytest.raises(RuntimeError):
            with pool.connection() as connection:
                connection.execute("SELECT 1")
                raise RuntimeError("body failed")
        with pool.connection() as connection:
            assert connection.execute("SELECT 1").fetchone()[0] == 1
    finally:
        pool.close()


def test_transaction_pool_proxy_resets_session_state() -> None:
    if "SYSTEMS_LAB_POOL_URL" not in os.environ:
        pytest.skip("set SYSTEMS_LAB_POOL_URL and start PgBouncer")
    result = observe()
    assert result["clients"] == 2
    assert result["backend_pids"][0] == result["backend_pids"][1]
    assert result["session_table_survived"] is False
