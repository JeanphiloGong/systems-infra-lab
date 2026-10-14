from concurrent.futures import ThreadPoolExecutor
import json
import os
from threading import Event

import psycopg
from psycopg import sql

from labs.query.derived.cache import Cache
from labs.query.derived.common import database, total


def run():
    outcomes = {}
    for guarded in (False, True):
        with database() as (writer, schema):
            now = [0.0]
            cache = Cache(lambda: now[0])
            captured, release = Event(), Event()

            def read():
                with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as reader:
                    reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))

                    def pause():
                        captured.set()
                        if not release.wait(5):
                            raise TimeoutError("writer did not release the paused fill")

                    return cache.get(lambda: total(reader), after_load=pause, guarded=guarded)

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(read)
                try:
                    assert captured.wait(5)
                    writer.execute("INSERT INTO sales VALUES (30001,0,50)")
                    committed_at = now[0]
                    # The SQL commit has completed before this invalidation.
                    cache.invalidate()
                finally:
                    release.set()
                returned = future.result(timeout=10)
            actual = total(writer)
            assert actual == 300050
            now[0] = 4.999
            before_expiry = cache.get(lambda: total(writer))
            now[0] = 5
            after_expiry = cache.get(lambda: total(writer))
            if guarded:
                assert returned == before_expiry == after_expiry == actual
                assert cache.rejected_fills == 1
            else:
                assert returned == before_expiry == 300000 and after_expiry == actual
            outcomes["epoch_guard" if guarded else "naive"] = {
                "returned": returned, "source": actual, "before_expiry": before_expiry,
                "after_expiry": after_expiry, "rejected_fills": cache.rejected_fills,
                "stale_window_in_this_schedule_seconds": 0 if returned == actual else now[0] - committed_at,
                "loads": cache.loads,
            }
    with database() as (writer, _):
        now = [0.0]
        cache = Cache(lambda: now[0])
        assert cache.get(lambda: total(writer)) == 300000
        now[0] = 1
        writer.execute("INSERT INTO sales VALUES (30001,0,50)")
        committed_at = now[0]
        assert cache.get(lambda: total(writer)) == 300000
        now[0] = 2
        cache.invalidate()
        assert cache.get(lambda: total(writer)) == 300050
        outcomes["commit_to_invalidation_gap"] = {
            "observed_logical_seconds": now[0] - committed_at,
            "old_read_during_gap": 300000, "after_invalidation": 300050,
        }
    return outcomes


if __name__ == "__main__":
    print(json.dumps(run()))
