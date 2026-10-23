# P03 v4: recovery and fencing

Migration phases must be restartable. A stale owner token must not write after cutover.

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

    def write_from_owner(self, owner: str, key: int, value: int | None, token: int) -> None:
        if token != self.fence or owner != self.route.owner(key):
            raise ValueError("stale owner fenced")
        self.shards[owner][key] = value

import json, subprocess, sys
from pathlib import Path

if len(sys.argv) == 3 and sys.argv[1] == "--child":
    state_path = Path(sys.argv[2]); state = json.loads(state_path.read_text())
    resumed = Migration(tuple(state["owners"])); resumed.route = Route(state["version"], tuple(state["owners"]))
    resumed.fence = state["fence"]; resumed.sequence = state["sequence"]; resumed.log = [tuple(item) for item in state["log"]]
    resumed.shards = {owner: {int(key): value for key, value in rows.items()} for owner, rows in state["shards"].items()}
    assert [resumed.read(key) for key in range(5)] == [10, 1, 22, None, 4]
    try: resumed.write_from_owner("a", 9, 98, state["fence"] - 1)
    except ValueError: stale_rejected = True
    else: stale_rejected = False
    assert stale_rejected
    resumed.write_from_owner("b", 9, 99, state["fence"])
    assert resumed.read(9) == 99
    assert [resumed.read(key) for key in range(5)] == [10, 1, 22, None, 4]
    state["shards"] = resumed.shards; state["phase"] = "resumed"; state_path.write_text(json.dumps(state))
    print({"restarted": True, "stale_old_owner_rejected": stale_rejected, "new_owner_write": 99})
    raise SystemExit

migration=Migration(("a",));
for key in range(4): migration.write(key,key)
migration.write(0,10)
watermark=migration.start_copy(("a","b")); migration.write(2,22); migration.write(3,None); migration.write(4,4); migration.apply_delta(("a","b"),watermark); barrier=migration.sequence; migration.cutover(("a","b"),barrier)
state=Path("migration-state.json"); state.write_text(json.dumps({"phase":"cutover","version":migration.route.version,"owners":["a","b"],"fence":migration.fence,"sequence":migration.sequence,"log":migration.log,"shards":migration.shards}))
subprocess.run([sys.executable,__file__,"--child",str(state)],check=True)
restarted=json.loads(state.read_text())
assert restarted["phase"] == "resumed" and restarted["shards"]["b"]["9"] == 99
print({"restarted":True,"stale_old_owner_rejected":True,"new_owner_write":99,"changed_partition":True})
```

JSON 对象的键会变成字符串，因此在恢复入口把分片键一次性还原为整数；`read` 继续只接受原来的整数键。子进程先通过原接口读回 0..4（包括覆盖后的 10/22 与删除后的 None），再验证旧 token 拒绝、新 owner 写入以及旧数据不变。不能只检查 JSON 中新增的 `"9"`。

这里保存并重开的是已完成 cutover 的本地 JSON 快照；没有在复制途中恢复，也没有原子发布或 fsync 协议，因此只证明新进程重建状态，不证明任意崩溃和断电安全。

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python checkpoint.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
