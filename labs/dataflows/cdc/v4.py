from __future__ import annotations

import json

from common import connect


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v4_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        conn.execute("INSERT INTO orders SELECT n, 'paused-' || n FROM generate_series(1,20000) n")
        retained = conn.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)::bigint FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        assert retained > 0
        confirmed_before = conn.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        events = conn.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s,NULL,NULL)", (slot,)).fetchone()[0]
        conn.execute("CHECKPOINT")
        remaining = conn.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)::bigint FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        confirmed_after = conn.execute("SELECT confirmed_flush_lsn FROM pg_replication_slots WHERE slot_name=%s", (slot,)).fetchone()[0]
        assert events > 20000 and confirmed_after >= confirmed_before
        conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
        return {"rows_written": 20000, "retained_bytes": retained, "events_replayed": events, "remaining_bytes": remaining, "confirmed_advanced": confirmed_after >= confirmed_before, "paused_then_recovered": True}


if __name__ == "__main__":
    print(json.dumps(experiment()))
