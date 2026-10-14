from __future__ import annotations


class MemTable:
    """String map with sorted snapshots; sorting is deferred until items()."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("key and value must be strings")
        self._values[key] = value

    def get(self, key: str) -> str | None:
        return self._values.get(key)

    def items(self) -> list[tuple[str, str]]:
        return sorted(self._values.items())


def main() -> None:
    table = MemTable()
    table.put("z", "old")
    table.put("a", "first")
    table.put("z", "new")
    print(table.items())
    print("fresh instance:", MemTable().get("z"))


if __name__ == "__main__":
    main()
