# C02 v2：投过的票必须跨进程保存

v1 的 vote 只在内存里。b 在任期 7 投给 a，进程退出后再次启动会忘掉这张票，并可能投给 c；两个多数派相交的安全前提因此失效。现在只增加一项能力：回复投票成功前，持久化 term/vote。

前置：完成 [v1](../v1/tutorial.md)。

## 1. 投过的票必须跨进程保存

Node 的构造参数从 `(name, now)` 改为 `(name, directory, now)`，Election 同时接收目录。两处调用一起更新；节点状态文件只保存 term/vote，重启总是 follower。写临时文件、fsync 文件、replace、fsync 目录之后才回复。保留 v1 的投票与心跳流程，并在每次更新 term/vote 后调用 persist。此模型单进程顺序处理每个节点事件，没有并发文件写者。

将 `labs/consensus/leader_election/model.py` 替换为本版完整 checkpoint：

<!-- checkpoint: labs/consensus/leader_election/model.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path


class Node:
    """One sequential event-loop node; persist votes before replying."""

    def __init__(self, name: str, directory: Path, now: float = 0) -> None:
        self.name = name
        self.path = directory / (name + ".json")
        state = json.loads(self.path.read_text()) if self.path.exists() else {"term": 0, "vote": None}
        self.term, self.vote = state["term"], state["vote"]
        self.leader = False
        self.last_heartbeat = now

    def persist(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            json.dump({"term": self.term, "vote": self.vote}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def request_vote(self, candidate: str, term: int) -> bool:
        if term < self.term:
            return False
        if term > self.term:
            self.term, self.vote, self.leader = term, None, False
            self.persist()
        if self.vote not in (None, candidate):
            return False
        self.vote = candidate
        self.persist()
        return True

    def heartbeat(self, term: int, now: float) -> bool:
        if term < self.term:
            return False
        if term > self.term:
            self.term, self.vote = term, None
            self.persist()
        self.leader = False
        self.last_heartbeat = now
        return True

    def timed_out(self, now: float, timeout: float = 5) -> bool:
        return now - self.last_heartbeat >= timeout


class Election:
    """Deterministic message delivery with a shared test clock, not a network."""

    def __init__(self, directory: Path) -> None:
        self.now = 0.0
        self.nodes = {name: Node(name, directory) for name in ("a", "b", "c")}
        self.blocked: set[frozenset[str]] = set()
        self.messages: list[tuple[str, str, int, bool]] = []

    def connected(self, first: str, second: str) -> bool:
        return frozenset((first, second)) not in self.blocked

    def isolate(self, name: str) -> None:
        self.blocked = {frozenset((name, other)) for other in self.nodes if other != name}

    def campaign(self, candidate: str, term: int) -> bool:
        node = self.nodes[candidate]
        if term <= node.term:
            return False
        votes = set()
        for name, peer in self.nodes.items():
            if self.connected(candidate, name):
                granted = peer.request_vote(candidate, term)
                self.messages.append((candidate, name, term, granted))
                if granted:
                    votes.add(name)
        won = len(votes) > len(self.nodes) // 2
        node.leader = won
        return won

    def broadcast(self, leader: str) -> None:
        node = self.nodes[leader]
        for name, peer in self.nodes.items():
            if name != leader and self.connected(leader, name):
                if not peer.heartbeat(node.term, self.now):
                    node.heartbeat(peer.term, self.now)
```

## 2. 用实际状态检验结果

保存下面的完整 `experiments.py`。每版保留已引入的检查，不使用 version 参数切换未来功能。

<!-- checkpoint: labs/consensus/leader_election/experiments.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys

from labs.consensus.leader_election.model import Election, Node

def check_v1(directory):
    cluster = Election(directory)
    assert cluster.campaign('a', 1)
    assert not cluster.campaign('b', 1)
    assert all((n.vote == 'a' for n in cluster.nodes.values()))
    cluster.broadcast('a')
    cluster.now = 4
    assert not cluster.nodes['b'].timed_out(cluster.now)
    cluster.isolate('a')
    cluster.now = 6
    assert cluster.nodes['b'].timed_out(cluster.now)
    assert cluster.campaign('b', 2)
    assert cluster.nodes['a'].leader and cluster.nodes['b'].leader
    assert cluster.nodes['c'].vote == 'b'
    return {'term1_winner': 'a', 'term2_winner': 'b', 'message_trace': cluster.messages}


def check_v2(directory):
    cluster = Election(directory)
    writer = """import os,sys
from pathlib import Path
from labs.consensus.leader_election.model import Node
n=Node('a',Path(sys.argv[1])); assert n.request_vote('b',7)
os._exit(71)
"""
    reader = """import json,sys
from pathlib import Path
from labs.consensus.leader_election.model import Node
n=Node('a',Path(sys.argv[1])); assert n.term==7 and n.vote=='b'
assert not n.request_vote('c',7); assert not n.request_vote('c',6)
assert n.request_vote('b',7); assert not n.leader
print(json.dumps({'recovered_term':n.term,'recovered_vote':n.vote,'double_vote_rejected':True}))
"""
    failed = subprocess.run([sys.executable, '-c', writer, folder], timeout=10)
    assert failed.returncode == 71
    recovered = subprocess.run([sys.executable, '-c', reader, folder], check=True, capture_output=True, text=True, timeout=10)
    return json.loads(recovered.stdout)


if __name__ == "__main__":
    with TemporaryDirectory() as folder:
        case = Path(folder) / "v1"
        case.mkdir()
        print("v1", check_v1(case))
        case = Path(folder) / "v2"
        case.mkdir()
        print("v2", check_v2(case))
```

从仓库根目录运行：

```bash
uv run python -m labs.consensus.leader_election.experiments
```

先重跑 v1。再由独立子进程投票并以 71 强制退出，新进程读回 term=7/vote=b，拒绝同任期给 c 投票，也拒绝旧任期。允许重复给原候选人返回成功。它证明进程重启；断电语义仍依赖 POSIX 文件系统的 fsync 契约。下一版保护实际写入口。
