from __future__ import annotations

import json
from common import connect, read_events


def experiment() -> dict[str, object]:
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY, value text)")
        slot = "e01_v1_slot"
        conn.execute("SELECT pg_drop_replication_slot(%s) FROM pg_replication_slots WHERE slot_name=%s", (slot, slot))
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s, 'test_decoding')", (slot,))
        conn.execute("INSERT INTO orders VALUES (1,'created')")
        conn.execute("UPDATE orders SET value='paid' WHERE id=1")
        conn.execute("DELETE FROM orders WHERE id=1")
        events = read_events(conn, slot)
        data_events = [event for event in events if event.operation != "TRANSACTION"]
        assert len(data_events) == 3
        assert len({event.source_position for event in data_events}) == len(data_events)
        assert [event.version for event in events] == list(range(1, len(events) + 1))
        conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
        return {"event_count": len(events), "data_event_count": len(data_events), "contains_insert": any(event.operation == "INSERT" for event in data_events), "contains_update": any(event.operation == "UPDATE" for event in data_events), "contains_delete": any(event.operation == "DELETE" for event in data_events), "source_positions": [event.source_position for event in events], "event_keys": [event.key for event in data_events], "versions": [event.version for event in events], "data_positions": [event.source_position for event in data_events], "xids": [event.xid for event in data_events], "operations": [event.operation for event in data_events], "source": "test_decoding"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
