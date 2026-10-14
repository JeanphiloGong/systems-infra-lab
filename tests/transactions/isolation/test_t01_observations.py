import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from labs.transactions.isolation.observations import dirty_read, read_skew, phantom_read


@pytest.fixture
def pair() -> Iterator[tuple[psycopg.Connection, psycopg.Connection]]:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as writer, psycopg.connect(dsn, autocommit=True) as reader:
        schema = "t01_" + uuid4().hex
        writer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for conn in (writer, reader):
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("SET statement_timeout = '5s'")
        try:
            writer.execute(Path("labs/transactions/isolation/schema.sql").read_text())
            yield writer, reader
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.mark.parametrize("level", ["READ COMMITTED", "READ UNCOMMITTED"])
def test_v1_uncommitted_debit_is_invisible(pair: tuple[psycopg.Connection, psycopg.Connection], level: str) -> None:
    writer, reader = pair
    assert dirty_read(writer, reader, level) == (70, 100, 100)
    assert reader.execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]


@pytest.mark.parametrize("level,expected", [("READ COMMITTED", (100,130,200)), ("REPEATABLE READ", (100,100,200))])
def test_v2_two_reads_straddle_commit(pair: tuple[psycopg.Connection, psycopg.Connection], level: str, expected: tuple[int,int,int]) -> None:
    assert read_skew(*pair, level) == expected
    assert pair[0].execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(70,), (130,)]


@pytest.mark.parametrize("level,expected", [("READ COMMITTED", (2,3,3)), ("REPEATABLE READ", (2,2,3))])
def test_v3_predicate_membership(pair: tuple[psycopg.Connection, psycopg.Connection], level: str, expected: tuple[int,int,int]) -> None:
    assert phantom_read(*pair, level) == expected


@pytest.mark.parametrize("scenario", ["dirty", "skew", "phantom"])
def test_invalid_isolation_rejected_before_mutation(pair: tuple[psycopg.Connection, psycopg.Connection], scenario: str) -> None:
    with pytest.raises(ValueError, match="unsupported isolation level"):
        if scenario == "dirty":
            dirty_read(*pair, "not an isolation level")
        elif scenario == "skew":
            read_skew(*pair, "not an isolation level")
        else:
            phantom_read(*pair, "not an isolation level")
    assert pair[0].execute("SELECT balance FROM accounts ORDER BY id").fetchall() == [(100,), (100,)]
