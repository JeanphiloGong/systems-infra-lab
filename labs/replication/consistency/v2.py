from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    kind: str
    key: str
    value: str | None
    version: int | None
    invoked: int
    returned: int


def check_history(history: list[Operation]) -> bool:
    writes = [item for item in history if item.kind == "write"]
    if any(item.kind not in {"read", "write"} or item.invoked > item.returned for item in history):
        return False
    for read in (item for item in history if item.kind == "read"):
        visible = [write for write in writes if write.key == read.key and write.invoked <= read.invoked]
        expected = max(visible, key=lambda write: write.returned).value if visible else None
        if read.value != expected:
            return False
        if read.version is not None and not any(write.version == read.version and write.key == read.key
                                               and write.invoked <= read.returned for write in writes):
            return False
    return True


class LinearizableStore:
    """A fixed single-writer model with key/value and invocation intervals."""
    def __init__(self) -> None:
        self.version = 0; self.clock = 0
        self.data: dict[str, tuple[int, str]] = {}
        self.history: list[Operation] = []

    def write(self, key: str, value: str) -> int:
        self.clock += 1; invoked = self.clock; self.version += 1
        self.data[key] = (self.version, value); self.clock += 1
        self.history.append(Operation("write", key, value, self.version, invoked, self.clock))
        return self.version

    def read(self, key: str) -> str | None:
        self.clock += 1; invoked = self.clock; value = self.data.get(key)
        result = None if value is None else value[1]; version = None if value is None else value[0]
        self.clock += 1; self.history.append(Operation("read", key, result, version, invoked, self.clock))
        return result

    def check_history(self) -> bool:
        return check_history(self.history)


if __name__ == "__main__":
    store = LinearizableStore(); store.write("name", "Ada")
    print(store.read("name"), store.check_history())
