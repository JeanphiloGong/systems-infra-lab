from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, name TEXT, state TEXT, PRIMARY KEY(order_id,name))")
        self.db.commit()

    def completed(self, order: str, name: str) -> bool:
        return self.db.execute("SELECT state='done' FROM steps WHERE order_id=? AND name=?", (order, name)).fetchone() == (1,)

    def run(self, order: str, name: str, effect) -> None:
        if self.completed(order, name):
            return
        self.db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, 'running')", (order, name))
        self.db.commit()
        effect()
        self.db.execute("UPDATE steps SET state='done' WHERE order_id=? AND name=?", (order, name))
        self.db.commit()

    def status(self, order: str) -> list[tuple[str, str]]:
        return self.db.execute("SELECT name,state FROM steps WHERE order_id=? ORDER BY rowid", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    calls: list[str] = []
    saga.run("order-1", "reserve", lambda: calls.append("reserve"))
    saga.run("order-1", "charge", lambda: calls.append("charge"))
    saga.run("order-1", "reserve", lambda: calls.append("duplicate"))
    print(calls, saga.status("order-1"))
