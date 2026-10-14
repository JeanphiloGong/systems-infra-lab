"""A denormalized projection is idempotent and rebuildable from the event log."""
from __future__ import annotations

import json
import sqlite3


class Projection:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript("CREATE TABLE IF NOT EXISTS orders (stream TEXT PRIMARY KEY, state TEXT, version INTEGER); CREATE TABLE IF NOT EXISTS processed (stream TEXT, version INTEGER, PRIMARY KEY(stream,version))")
        self.db.commit()

    def apply(self, stream, version, kind):
        if self.db.execute("SELECT 1 FROM processed WHERE stream=? AND version=?", (stream, version)).fetchone():
            return False
        current = self.db.execute("SELECT version FROM orders WHERE stream=?", (stream,)).fetchone()
        expected = 1 if current is None else current[0] + 1
        if version != expected:
            raise ValueError(f"out-of-order version {version}, expected {expected}")
        state = {"OrderPlaced": "placed", "OrderPaid": "paid", "OrderShipped": "shipped"}[kind]
        self.db.execute("INSERT OR REPLACE INTO orders VALUES (?,?,?)", (stream, state, version))
        self.db.execute("INSERT INTO processed VALUES (?,?)", (stream, version))
        self.db.commit()
        return True

    def rebuild(self, events):
        self.db.execute("DELETE FROM orders"); self.db.execute("DELETE FROM processed"); self.db.commit()
        for event in events:
            self.apply(*event)

    def read(self, stream):
        return self.db.execute("SELECT state,version FROM orders WHERE stream=?", (stream,)).fetchone()


def experiment():
    events = [("order-1", 1, "OrderPlaced"), ("order-1", 2, "OrderPaid"), ("order-1", 3, "OrderShipped")]
    projection = Projection()
    applied = [projection.apply(*event) for event in events]
    duplicate = projection.apply(*events[1])
    try:
        projection.apply("order-2", 2, "OrderPaid")
    except ValueError:
        out_of_order_rejected = True
    else:
        out_of_order_rejected = False
    lagged = Projection(); [lagged.apply(*event) for event in events[:2]]
    lagged.rebuild(events)
    assert applied == [True, True, True] and not duplicate and out_of_order_rejected and lagged.read("order-1") == ("shipped", 3)
    return {"applied": sum(applied), "duplicate_applied": duplicate, "out_of_order_rejected": out_of_order_rejected, "lagged_after_rebuild": lagged.read("order-1")}


if __name__ == "__main__":
    print(json.dumps(experiment()))
