from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    user: int
    day: int
    order_id: int
    amount: int


class Table:
    def __init__(self, rows: list[Row]) -> None:
        self.rows = rows
        self.index: dict[tuple[int, int], list[int]] = {}
        self.index_writes = 0
        self.visible = [True] * len(rows)

    def build_index(self, columns=("user",)) -> None:
        self.index.clear()
        for position, row in enumerate(self.rows):
            key = tuple(getattr(row, column) for column in columns)
            self.index.setdefault(key, []).append(position); self.index_writes += 1

    def query(self, user: int, day: int | None = None, covering: bool = False) -> tuple[list[Row], dict[str, int]]:
        candidates = []
        if day is None and (user,) in self.index: candidates = self.index[(user,)]
        elif day is not None and (user, day) in self.index: candidates = self.index[(user, day)]
        else: candidates = list(range(len(self.rows)))
        heap_fetches = 0 if covering and all(self.visible[position] for position in candidates) else len(candidates)
        result = [self.rows[position] for position in candidates if self.rows[position].user == user and (day is None or self.rows[position].day == day)]
        return result, {"index_entries": len(candidates), "heap_fetches": heap_fetches}

    def update(self, position: int, amount: int) -> None:
        row = self.rows[position]; self.rows[position] = Row(row.user, row.day, row.order_id, amount); self.visible[position] = False
