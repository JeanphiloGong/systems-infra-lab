# C03 v2：AppendEntries 前缀检查与冲突修复

领导者发送 `term`、`prev_log_index`、`prev_log_term`、entries 和 `leader_commit`。跟随者先检查前缀；任期不匹配时拒绝。前缀匹配后，冲突后缀被删除并追加领导者记录，提交位置再推进并应用。

运行：`uv run python -m labs.consensus.raft.experiments 2`。输出必须显示 `repaired_term=3` 和状态 `mode=new`；专项测试还验证错误前缀被拒绝，以及已提交记录不能被覆盖。

本版仍是单进程、确定性调用。多数复制、候选人日志新旧规则和网络故障属于路线图 v3 以后，不能把这个检查点称作完整 Raft。

## 完整 checkpoint

下面的文件可以复制到一个空目录中运行；它不依赖仓库中的实现。

<!-- checkpoint: labs/consensus/raft/model.py -->

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    term: int
    index: int
    command: dict[str, str]


class Node:
    def __init__(self, name: str, directory: Path) -> None:
        self.name = name
        self.path = directory / f"{name}.json"
        saved = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.current_term = int(saved.get("term", 0))
        self.voted_for = saved.get("voted_for")
        self.log = [Entry(**entry) for entry in saved.get("log", [])]
        self.commit_index = int(saved.get("commit_index", 0))
        self.last_applied = int(saved.get("last_applied", 0))
        self.state: dict[str, str] = dict(saved.get("state", {}))

    def persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {"term": self.current_term, "voted_for": self.voted_for,
                   "log": [entry.__dict__ for entry in self.log],
                   "commit_index": self.commit_index,
                   "last_applied": self.last_applied, "state": self.state}
        with temporary.open("w") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)

    def request_vote(self, term: int, candidate: str) -> bool:
        if term < self.current_term:
            return False
        if term > self.current_term:
            self.current_term, self.voted_for = term, None
        if self.voted_for not in (None, candidate):
            self.persist()
            return False
        self.voted_for = candidate
        self.persist()
        return True

    def append_command(self, command: dict[str, str], term: int | None = None) -> Entry:
        entry = Entry(term or self.current_term, len(self.log) + 1, dict(command))
        self.log.append(entry)
        self.persist()
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
        self.persist()

    def append_entries(self, *, term: int, prev_log_index: int,
                       prev_log_term: int, entries: list[Entry],
                       leader_commit: int) -> bool:
        if term < self.current_term:
            return False
        if term > self.current_term:
            self.current_term, self.voted_for = term, None
        if prev_log_index and (prev_log_index > len(self.log) or
                               self.log[prev_log_index - 1].term != prev_log_term):
            self.persist()
            return False
        for incoming in entries:
            position = incoming.index - 1
            if position < len(self.log) and self.log[position].term != incoming.term:
                if position < self.commit_index:
                    raise ValueError("cannot overwrite committed entry")
                del self.log[position:]
            if position >= len(self.log):
                self.log.append(incoming)
        target = min(leader_commit, len(self.log))
        if target > self.commit_index:
            self.commit_to(target)
        else:
            self.persist()
        return True
```

<!-- checkpoint: labs/consensus/raft/experiments.py -->

```python
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .model import Entry, Node


def run() -> dict[str, object]:
    with TemporaryDirectory() as folder:
        node = Node("f", Path(folder))
        node.current_term = 3
        node.append_command({"key": "mode", "value": "old"}, term=1)
        replacement = Entry(3, 1, {"key": "mode", "value": "new"})
        assert not node.append_entries(term=3, prev_log_index=1, prev_log_term=3,
                                       entries=[], leader_commit=0)
        assert node.append_entries(term=3, prev_log_index=0, prev_log_term=0,
                                   entries=[replacement], leader_commit=1)
        return {"repaired_term": node.log[0].term, "state": node.state}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
```
