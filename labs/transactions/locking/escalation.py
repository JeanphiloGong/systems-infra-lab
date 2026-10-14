from __future__ import annotations


class LockModel:
    """Single-threaded teaching model: exclusive locks on one table only."""

    def __init__(self) -> None:
        self.rows: dict[int, str] = {}
        self.table_owner: str | None = None

    def acquire(self, owner: str, row: int) -> bool:
        if self.table_owner is not None:
            return self.table_owner == owner
        if row in self.rows and self.rows[row] != owner:
            return False
        self.rows[row] = owner
        return True

    def escalate(self, owner: str) -> bool:
        if self.table_owner is not None:
            return self.table_owner == owner
        if not self.rows or any(holder != owner for holder in self.rows.values()):
            return False
        self.table_owner = owner
        self.rows.clear()
        return True

    def release(self, owner: str) -> None:
        if self.table_owner == owner:
            self.table_owner = None
        self.rows = {row: holder for row, holder in self.rows.items() if holder != owner}


def main() -> None:
    model = LockModel()
    for row in range(3):
        assert model.acquire("A", row)
    before = len(model.rows)
    assert model.acquire("B", 99)
    assert not model.escalate("A")
    model.release("B")
    assert model.escalate("A")
    after = len(model.rows) + int(model.table_owner is not None)
    assert not model.acquire("B", 99)
    model.release("A")
    assert model.acquire("B", 99)
    print(f"records_before={before} records_after={after} unrelated_row_blocked=True")


if __name__ == "__main__":
    main()
