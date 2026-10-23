# P03 v1: background copy exposes a gap

Copying history while accepting writes leaves a delta that the first copy did not see.

将下面的完整代码保存为 `checkpoint.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: checkpoint.py -->

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    version: int
    owners: tuple[str, ...]

    def owner(self, key: int) -> str:
        return self.owners[key % len(self.owners)]


class Migration:
    def __init__(self, owners: tuple[str, ...] = ("a", "b")) -> None:
        if not owners or len(set(owners)) != len(owners):
            raise ValueError("owners must be unique")
        self.route = Route(1, owners)
        self.shards = {owner: {} for owner in owners}
        self.log: list[tuple[int, str, int | None, int]] = []
        self.sequence = 0
        self.paused = False
        self.fence = 1

    def write(self, key: int, value: int | None, route_version: int | None = None) -> int:
        if route_version is not None and route_version != self.route.version:
            raise ValueError("stale route version")
        if self.paused:
            raise RuntimeError("writes paused")
        self.sequence += 1
        owner = self.route.owner(key)
        self.shards[owner][key] = value
        self.log.append((key, owner, value, self.sequence))
        return self.sequence

    def read(self, key: int, route_version: int | None = None) -> int | None:
        if route_version is not None and route_version != self.route.version:
            raise ValueError("stale route version")
        return self.shards[self.route.owner(key)].get(key)

    def pause_and_copy(self, target: tuple[str, ...]) -> None:
        self.paused = True
        self._copy(target)

    def start_copy(self, target: tuple[str, ...]) -> int:
        self._copy(target)
        return self.sequence

    def _copy(self, target: tuple[str, ...]) -> None:
        for owner, data in list(self.shards.items()):
            for key, value in data.items():
                self.shards.setdefault(target[key % len(target)], {})[key] = value

    def apply_delta(self, target: tuple[str, ...], since: int, seen: set[int] | None = None) -> int:
        seen = set() if seen is None else seen
        applied = 0
        for key, _old_owner, value, sequence in self.log:
            if sequence <= since or sequence in seen:
                continue
            self.shards.setdefault(target[key % len(target)], {})[key] = value
            seen.add(sequence); applied += 1
        return applied

    def cutover(self, target: tuple[str, ...], barrier: int) -> None:
        if any(sequence > barrier for *_rest, sequence in self.log):
            raise ValueError("barrier is behind writes")
        self.route = Route(self.route.version + 1, target)
        self.fence += 1
        self.paused = False

    def fence_old_owner(self, owner: str, token: int) -> None:
        if token != self.fence or owner not in self.shards:
            raise ValueError("stale owner fence")

migration=Migration(("a",));
for key in range(4): migration.write(key,key)
watermark=migration.start_copy(("a","b")); migration.write(4,4)
assert migration.read(4) == 4 and 4 not in migration.shards["b"]
print({"watermark":watermark,"gap":4})
```

The gap is concrete evidence that “copy complete” is not yet a cutover condition.

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python checkpoint.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
