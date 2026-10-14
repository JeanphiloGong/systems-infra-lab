from collections.abc import Iterator
import os
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from labs.transactions.isolation.transfer import transfer


@pytest.fixture
def account_db() -> Iterator[psycopg.Connection]:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = "t01_" + uuid4().hex
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        try:
            conn.execute(Path("labs/transactions/isolation/schema.sql").read_text())
            yield conn
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_success(account_db: psycopg.Connection) -> None:
    transfer(account_db, 1, 2, 30)
    assert account_db.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(70,), (130,)]


def test_failure_rolls_back(account_db: psycopg.Connection) -> None:
    with pytest.raises(RuntimeError, match="after debit"):
        transfer(account_db, 1, 2, 30, fail_after_debit=True)
    assert account_db.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]


@pytest.mark.parametrize("source,target,amount", [(1,2,0),(1,2,-1),(1,2,101),(1,1,30),(3,2,30),(1,3,30),(1,2,True)])
def test_invalid_request_preserves_balances(account_db: psycopg.Connection, source: int, target: int, amount: int) -> None:
    with pytest.raises(ValueError):
        transfer(account_db, source, target, amount)
    assert account_db.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]


def test_exact_balance(account_db: psycopg.Connection) -> None:
    transfer(account_db, 1, 2, 100)
    assert account_db.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(0,), (200,)]


def test_connection_failure_never_reports_success() -> None:
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        result = subprocess.run(
            [sys.executable, "-m", "labs.transactions.isolation.transfer"],
            env={**os.environ, "SYSTEMS_LAB_DATABASE_URL": f"postgresql://127.0.0.1:{port}/missing"},
            capture_output=True, text=True, timeout=10,
        )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "OperationalError" in result.stderr
