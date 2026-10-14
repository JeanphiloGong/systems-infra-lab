from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, position INTEGER, name TEXT, state TEXT, attempts INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(order_id,position))")
        self.db.commit()

    def seed(self, order: str, position: int, name: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO steps(order_id,position,name,state) VALUES (?, ?, ?, 'done')", (order, position, name))
        self.db.commit()

    def compensate(self, order: str, position: int, effect, max_attempts: int = 3) -> str:
        row = self.db.execute("SELECT state,attempts FROM steps WHERE order_id=? AND position=?", (order, position)).fetchone()
        if row is None or row[0] == "compensated":
            return "already_done"
        attempts = row[1]
        while attempts < max_attempts:
            attempts += 1
            self.db.execute("UPDATE steps SET state='compensating',attempts=? WHERE order_id=? AND position=?", (attempts, order, position))
            self.db.commit()
            try:
                effect(attempts)
            except TimeoutError:
                continue
            self.db.execute("UPDATE steps SET state='compensated' WHERE order_id=? AND position=?", (order, position))
            self.db.commit()
            return "compensated"
        self.db.execute("UPDATE steps SET state='manual' WHERE order_id=? AND position=?", (order, position))
        self.db.commit()
        return "manual"

    def status(self, order: str) -> list[tuple[int, str, str, int]]:
        return self.db.execute("SELECT position,name,state,attempts FROM steps WHERE order_id=? ORDER BY position", (order,)).fetchall()


if __name__ == "__main__":
    saga = Saga(":memory:")
    saga.seed("order-1", 1, "reserve")
    print(saga.compensate("order-1", 1, lambda attempt: (_ for _ in ()).throw(TimeoutError()), max_attempts=2))
    print(saga.status("order-1"))
