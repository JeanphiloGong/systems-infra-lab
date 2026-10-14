from __future__ import annotations

import json

from common import connect, order_change, read_events, snapshot_cut


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v2_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        try:
            conn.execute("INSERT INTO orders VALUES (1,'before-snapshot'),(3,'remove me'),(4,'old incarnation')")
            conn.execute("UPDATE orders SET value='snapshot updated' WHERE id=1")
            snapshot, cursor = snapshot_cut(conn, slot)
            with conn.transaction():
                conn.execute("UPDATE orders SET value=%s WHERE id=1", ("paid in full; customer's order",))
                conn.execute("DELETE FROM orders WHERE id IN (3,4)")
                conn.execute("INSERT INTO orders VALUES (4,'new incarnation')")
                conn.execute("INSERT INTO orders VALUES (2,'after-snapshot')")
            projection = dict(snapshot)
            events = read_events(conn, slot)
            for event in events:
                change = order_change(event)
                if change is None:
                    continue
                identifier, value = change
                if event.operation == "DELETE":
                    projection.pop(identifier, None)
                else:
                    projection[identifier] = value
            expected = dict(conn.execute("SELECT id,value FROM orders").fetchall())
            assert projection == expected
            assert conn.execute("SELECT %s::pg_lsn > %s::pg_lsn", (events[-1].source_position, cursor)).fetchone()[0]
            return {"snapshot_rows": len(snapshot), "projection": projection, "snapshot_cursor": cursor, "last_source_position": events[-1].source_position, "matches_source": True, "operations": [event.operation for event in events if event.operation != "TRANSACTION"]}
        finally:
            conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))


if __name__ == "__main__":
    print(json.dumps(experiment()))
