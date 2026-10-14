import json
import os
from time import perf_counter

import psycopg
from psycopg import sql

from labs.query.derived.common import database


def run():
    with database() as (writer, schema):
        writer.execute("CREATE MATERIALIZED VIEW daily AS SELECT day,sum(amount) AS amount FROM sales GROUP BY day")
        try:
            writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily")
        except psycopg.errors.ObjectNotInPrerequisiteState as error:
            prerequisite_error = error.sqlstate
        else:
            raise AssertionError("concurrent refresh should require a unique index")
        writer.execute("CREATE UNIQUE INDEX daily_day ON daily(day)")
        writer.execute("INSERT INTO sales VALUES (30001,0,50)")
        with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as reader:
            reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            reader.execute("SET lock_timeout='200ms'")
            writer.execute("SET lock_timeout='200ms'")
            with reader.transaction():
                reader.execute("SELECT * FROM daily").fetchall()
                started = perf_counter()
                try:
                    writer.execute("REFRESH MATERIALIZED VIEW daily")
                except psycopg.errors.LockNotAvailable:
                    ordinary_wait = perf_counter() - started
                else:
                    raise AssertionError("ordinary refresh should conflict with the open reader")
                writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily")
                assert reader.execute("SELECT sum(amount) FROM daily").fetchone()[0] == 300050
            with writer.transaction():
                writer.execute("REFRESH MATERIALIZED VIEW daily")
                try:
                    reader.execute("SELECT * FROM daily")
                except psycopg.errors.LockNotAvailable:
                    read_blocked = True
                else:
                    raise AssertionError("ordinary refresh lock should block another reader")
            assert reader.execute("SELECT sum(amount) FROM daily").fetchone()[0] == 300050
        writer.execute("CREATE MATERIALIZED VIEW unpopulated AS SELECT * FROM daily WITH NO DATA")
        writer.execute("CREATE UNIQUE INDEX unpopulated_day ON unpopulated(day)")
        try:
            writer.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY unpopulated")
        except psycopg.errors.FeatureNotSupported as error:
            unpopulated_error = error.sqlstate
        else:
            raise AssertionError("concurrent refresh must not populate an unpopulated view")
        return {"missing_index_sqlstate": prerequisite_error, "unpopulated_sqlstate": unpopulated_error,
                "ordinary_wait_seconds": ordinary_wait, "ordinary_blocks_read": read_blocked,
                "concurrent_refresh_with_open_reader": True, "new_total": 300050}


if __name__ == "__main__":
    print(json.dumps(run()))
