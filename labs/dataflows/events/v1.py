"""Append immutable domain events and replay a deterministic order state."""
from __future__ import annotations

import json
import sqlite3


class EventStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (stream TEXT, version INTEGER, kind TEXT, payload TEXT, PRIMARY KEY(stream, version))")
        self.db.commit()

    def append(self, stream, kind, payload):
        version = self.db.execute("SELECT coalesce(max(version),0)+1 FROM events WHERE stream=?", (stream,)).fetchone()[0]
        self.db.execute("INSERT INTO events VALUES (?,?,?,?)", (stream, version, kind, json.dumps(payload, sort_keys=True)))
        self.db.commit()
        return version

    def read(self, stream):
        return [(version, kind, json.loads(payload)) for version, kind, payload in self.db.execute("SELECT version,kind,payload FROM events WHERE stream=? ORDER BY version", (stream,))]


def replay(events):
    state = "new"
    allowed = {"new": {"OrderPlaced": "placed"}, "placed": {"OrderPaid": "paid", "OrderCancelled": "cancelled"}, "paid": {"OrderShipped": "shipped"}, "shipped": {}, "cancelled": {}}
    for _, kind, _ in events:
        if kind not in allowed[state]:
            raise ValueError(f"invalid transition {state}->{kind}")
        state = allowed[state][kind]
    return state


def experiment():
    store = EventStore()
    for kind in ("OrderPlaced", "OrderPaid", "OrderShipped"):
        store.append("order-1", kind, {})
    events = store.read("order-1")
    assert [version for version, _, _ in events] == [1, 2, 3] and replay(events) == "shipped"
    try:
        replay([(1, "OrderShipped", {})])
    except ValueError:
        invalid_rejected = True
    else:
        invalid_rejected = False
    assert invalid_rejected
    return {"versions": [v for v, _, _ in events], "state": replay(events), "invalid_rejected": invalid_rejected}


if __name__ == "__main__":
    print(json.dumps(experiment()))
