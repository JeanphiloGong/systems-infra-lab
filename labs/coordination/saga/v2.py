from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, position INTEGER, name TEXT, state TEXT, PRIMARY KEY(order_id,position))")
        self.db.commit()

    def step(self, order: str, position: int, name: str, effect) -> None:
        row = self.db.execute("SELECT state FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row and row[0] == "done":
            return
        self.db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, ?, 'running')", (order, position, name))
        self.db.commit()
        effect()
        self.db.execute("UPDATE steps SET state='done' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()

    def compensate(self, order: str, position: int, effect) -> None:
        row = self.db.execute("SELECT state FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row is None or row[0] == "compensated":
            return
        effect()
        self.db.execute("UPDATE steps SET state='compensated' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()

    def status(self, order: str) -> list[tuple[int, str, str]]:
        return self.db.execute("SELECT position,name,state FROM steps WHERE order_id=? ORDER BY position", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    effects: list[str] = []
    saga.step("order-1", 1, "reserve", lambda: effects.append("reserved"))
    saga.step("order-1", 2, "charge", lambda: effects.append("charged"))
    saga.compensate("order-1", 2, lambda: effects.append("refunded"))
    saga.compensate("order-1", 1, lambda: effects.append("released"))
    saga.compensate("order-1", 1, lambda: effects.append("duplicate-release"))
    print(effects, saga.status("order-1"))
