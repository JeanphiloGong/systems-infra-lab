from contextlib import ExitStack
import os

import psycopg
from psycopg import sql

from labs.storage.vacuum.vacuum import create_schema
from labs.storage.vacuum.reuse import reuse
from labs.storage.vacuum.snapshot import observe
from labs.storage.vacuum.full import compare
from labs.storage.vacuum.automatic import observe as automatic


def test_reuse_without_file_shrink() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            before, cleaned, after, count = reuse(conn)
            assert before == cleaned == after
            assert count == 1000
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_snapshot_and_full_lock() -> None:
    with ExitStack() as stack:
        reader, writer, observer = [stack.enter_context(psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True)) for _ in range(3)]
        schema = create_schema(writer)
        try:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            assert observe(reader, writer) == (0,1000,1000)
            before, after, count = compare(reader, writer, observer)
            assert after <= before
            assert count == 1000
        finally:
            writer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_autovacuum_bounded_observation() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = create_schema(conn)
        try:
            result = automatic(conn, 0)
            assert isinstance(result["observed"], bool)
            assert result["elapsed_seconds"] >= 0
            assert conn.execute("SELECT count(*) FROM items").fetchone()[0] == 200
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
