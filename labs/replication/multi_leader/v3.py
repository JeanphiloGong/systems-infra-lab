from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Counter:
    region: str
    components: dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0})

    def __post_init__(self) -> None:
        if self.region not in {"A", "B"}:
            raise ValueError("unknown writer")

    def increment(self, amount: int = 1) -> None:
        if type(amount) is not int or amount < 1:
            raise ValueError("positive integer increment required")
        self.components[self.region] += amount

    def snapshot(self) -> dict[str, int]:
        return dict(self.components)

    def merge(self, snapshot: dict[str, int]) -> None:
        if set(snapshot) != {"A", "B"} or any(type(value) is not int or value < 0 for value in snapshot.values()):
            raise ValueError("invalid counter snapshot")
        for region, value in snapshot.items():
            self.components[region] = max(self.components[region], value)

    @property
    def value(self) -> int:
        return sum(self.components.values())


if __name__ == "__main__":
    first, second = Counter("A"), Counter("B")
    first.increment(2)
    old = first.snapshot()
    first.increment()
    second.increment(4)
    first.merge(second.snapshot())
    second.merge(first.snapshot())
    second.merge(old)
    second.merge(first.snapshot())
    assert first.value == second.value == 7
    print({"value": first.value, "components": first.components})
