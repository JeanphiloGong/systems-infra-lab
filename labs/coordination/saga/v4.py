from __future__ import annotations

import sqlite3
from threading import Lock


class Orders:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS effects (order_id TEXT, name TEXT, state TEXT, PRIMARY KEY(order_id,name))")
        self.db.commit()
        self.lock = Lock()

    def apply(self, order: str, name: str) -> bool:
        with self.lock:
            row = self.db.execute("SELECT state FROM effects WHERE order_id=? AND name=?", (order, name)).fetchone()
            if row is not None:
                return False
            self.db.execute("INSERT INTO effects VALUES (?, ?, 'done')", (order, name))
            self.db.commit()
            return True

    def snapshot(self) -> list[tuple[str, str, str]]:
        return self.db.execute("SELECT order_id,name,state FROM effects ORDER BY order_id,name").fetchall()


if __name__ == "__main__":
    orders = Orders(":memory:")
    assert orders.apply("order-a", "reserve")
    assert not orders.apply("order-a", "reserve")
    assert orders.apply("order-b", "reserve")
    print(orders.snapshot())
