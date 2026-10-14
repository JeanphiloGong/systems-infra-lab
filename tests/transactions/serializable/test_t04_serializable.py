import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4
import psycopg
from psycopg import sql
from labs.transactions.serializable.serializable import concurrent_once
from labs.transactions.serializable.serializable import retry_once
from labs.transactions.serializable.serializable import concurrent_retry, measure_once


def test_serializable_aborts_one_transaction() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as a, psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as b:
        schema = "t04_" + uuid4().hex
        a.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for c in (a,b): c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            a.execute(Path("labs/transactions/serializable/schema.sql").read_text())
            assert concurrent_once(a,b)[0] == 1
        finally: a.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))

def test_retry_re_reads_clean_snapshot() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as conn:
        schema = "t04_" + uuid4().hex
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute(Path("labs/transactions/serializable/schema.sql").read_text())
            assert retry_once(conn, 1, max_retries=2) == (0, True)
            assert conn.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 1
        finally: conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_conflict_retry_rechecks_business_rule_and_load_metrics() -> None:
    dsn = os.environ["SYSTEMS_LAB_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
        schema = "t04_" + uuid4().hex
        first.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            for conn in (first, second):
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                conn.execute("SET statement_timeout='8s'")
            first.execute(Path("labs/transactions/serializable/schema.sql").read_text())
            outcomes = concurrent_retry(first, second)
            assert sorted(allowed for _, allowed in outcomes) == [False, True]
            assert sum(retries for retries, _ in outcomes) >= 1
            assert all(not allowed for retries, allowed in outcomes if retries)
            assert first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 1
            metrics = measure_once(first, second, rounds=5)
            assert metrics["operations"] == metrics["committed"] == 10
            assert metrics["aborted_attempts"] == metrics["retries"] >= 5
            assert metrics["allowed"] == metrics["refused"] == 5
            assert metrics["remaining"] == 1
            assert metrics["operations_per_second"] > 0
            first.execute("UPDATE doctors SET on_call=true")
            barrier = Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(retry_once, first, 1, 0, barrier),
                    pool.submit(retry_once, second, 2, 0, barrier),
                ]
                failures = 0
                for future in futures:
                    try:
                        assert future.result(timeout=12) == (0, True)
                    except psycopg.errors.SerializationFailure:
                        failures += 1
            assert failures == 1
            assert first.execute("SELECT count(*) FROM doctors WHERE on_call").fetchone()[0] == 1
        finally:
            first.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
