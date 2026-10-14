"""Manual PostgreSQL physical-standby promotion probe.

Start ``infra/r04.compose.yaml`` first. The probe only promotes the disposable
standby; it never targets a user database.
"""

from __future__ import annotations

import json
import time

import psycopg


def connect(port: int) -> psycopg.Connection:
    return psycopg.connect(host="127.0.0.1", port=port, dbname="r04", user="r04", password="r04_local_only", autocommit=True, connect_timeout=3)


def wait(check, seconds: float = 30) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.1)
    raise TimeoutError("PostgreSQL promotion probe timed out")


def run() -> dict[str, object]:
    with connect(55440) as primary, connect(55441) as standby:
        primary.execute("DROP TABLE IF EXISTS a03_probe")
        primary.execute("CREATE TABLE a03_probe (id integer PRIMARY KEY, value text NOT NULL)")
        primary.execute("INSERT INTO a03_probe VALUES (1, 'before-promotion')")
        target = primary.execute("SELECT pg_current_wal_lsn()").fetchone()[0]
        wait(lambda: standby.execute("SELECT pg_last_wal_replay_lsn() >= %s::pg_lsn", (target,)).fetchone()[0])
        assert standby.execute("SELECT pg_is_in_recovery()").fetchone()[0] is True
        standby.execute("SELECT pg_promote(wait => true)")
        wait(lambda: standby.execute("SELECT NOT pg_is_in_recovery()").fetchone()[0])
        standby.execute("INSERT INTO a03_probe VALUES (2, 'after-promotion')")
        rows = standby.execute("SELECT id,value FROM a03_probe ORDER BY id").fetchall()
        return {"replica_promoted": True, "rows": rows, "old_primary_fence_required": True}


if __name__ == "__main__":
    print(json.dumps(run(), default=list, sort_keys=True))
