# C03 v0：单节点日志驱动状态机

场景是一个配置状态机。命令先进入带任期和索引的日志，只有提交后才按顺序应用。压力来自“追加不等于完成”：未提交记录不能改变状态机。

运行：`uv run pytest tests/consensus/raft/test_c03.py -q`。检查 `commit_index == 1` 且状态为 `{"mode": "safe"}`。

本版冻结范围是 `labs/consensus/raft/model.py` 的 `Entry`、`Node.append_command`、`Node.commit_to`。提交索引只能前进到已有日志，应用索引逐条前进；v1 才加入持久任期和投票。

<!-- checkpoint: labs/consensus/raft/model.py -->
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Entry:
    term: int
    index: int
    command: dict[str, str]

class Node:
    def __init__(self) -> None:
        self.current_term = 0
        self.log: list[Entry] = []
        self.commit_index = 0
        self.last_applied = 0
        self.state: dict[str, str] = {}

    def append_command(self, command: dict[str, str]) -> Entry:
        entry = Entry(self.current_term, len(self.log) + 1, dict(command))
        self.log.append(entry)
        return entry

    def commit_to(self, index: int) -> None:
        if index < self.commit_index or index > len(self.log):
            raise ValueError("commit index must advance within the log")
        self.commit_index = index
        while self.last_applied < self.commit_index:
            entry = self.log[self.last_applied]
            if set(entry.command) != {"key", "value"}:
                raise ValueError("unsupported command")
            self.state[entry.command["key"]] = entry.command["value"]
            self.last_applied += 1
```

<!-- checkpoint: labs/consensus/raft/experiments.py -->
```python
import json
from .model import Node

node = Node()
node.current_term = 1
node.append_command({"key": "mode", "value": "safe"})
node.commit_to(1)
assert node.state == {"mode": "safe"}
print(json.dumps({"commit_index": node.commit_index, "state": node.state}))
```
