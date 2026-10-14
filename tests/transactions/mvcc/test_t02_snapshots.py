from collections.abc import Iterator
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from labs.transactions.mvcc.snapshots import snapshot_timing


@pytest.fixture
def doctors() -> Iterator[tuple[psycopg.Connection, psycopg.Connection]]:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as reader, psycopg.connect(dsn, autocommit=True) as writer:
        schema = "t02_" + uuid4().hex
        reader.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (reader, writer):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout = '5s'")
            reader.execute(Path("labs/transactions/mvcc/schema.sql").read_text())
            yield reader, writer
        finally:
            reader.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.mark.parametrize("early_read,expected", [(True,(True,True,False)), (False,(False,False,False))])
def test_v0_snapshot_starts_at_first_read(doctors: tuple[psycopg.Connection, psycopg.Connection], early_read: bool, expected: tuple[bool,bool,bool]) -> None:
    assert snapshot_timing(*doctors, early_read=early_read) == expected
