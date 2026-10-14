from __future__ import annotations

import json

from common import connect, scalar, wait_for
from v1 import setup


def slot_bytes(conn) -> int:
    value = scalar(conn, "SELECT COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn),0)::bigint FROM pg_replication_slots WHERE slot_name='r04_sub' AND NOT active")
    return int(value or 0)


def experiment() -> dict[str, object]:
    setup()
    with connect("primary") as primary, connect("subscriber") as subscriber:
        subscriber.execute("ALTER SUBSCRIPTION r04_sub DISABLE")
        wait_for(lambda: scalar(primary, "SELECT active IS FALSE FROM pg_replication_slots WHERE slot_name='r04_sub'") is True, "slot pause")
        before = slot_bytes(primary)
        primary.execute("INSERT INTO orders(value) SELECT 'paused-' || n FROM generate_series(1, 20000) AS n")
        after = slot_bytes(primary)
        assert after > before
        subscriber.execute("ALTER SUBSCRIPTION r04_sub ENABLE")
        wait_for(lambda: scalar(subscriber, "SELECT count(*) FROM orders") == 20001, "subscriber catch-up", seconds=90)
        wait_for(lambda: scalar(primary, "SELECT active IS TRUE FROM pg_replication_slots WHERE slot_name='r04_sub'") is True, "slot active")
        recovered = slot_bytes(primary)
        assert recovered < after
        return {"paused_bytes": before, "retained_bytes": after, "recovered_bytes": recovered, "subscriber_rows": 20001, "slot": "r04_sub"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
