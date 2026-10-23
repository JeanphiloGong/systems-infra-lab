# C02 v3：由资源拒绝旧 leader 写入

v2 保存了投票，却不能阻止暂停的旧 leader 恢复后继续写。现在让被写资源检查 owner、term 和到期时刻。这个资源是实验中可信且不重启的授权入口；选举成功后由模拟器注册新 owner，真实服务还需要验证授权证据并持久化 fence。

前置：完成 [v2](../v2/tutorial.md)。

## 1. 由资源拒绝旧 leader 写入

新增 `Resource.activate/write`，Election 只有赢得多数票才调用 activate。write 把当前节点身份交给资源；判断基于资源自己的逻辑时钟，等于 expires 就拒绝。这里没有租约续期，也不声称各机器时钟同步；资源换了 owner 后，即使旧节点后来获知新 term，也因 owner 不匹配被拒绝。

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


class Resource:
    """Trusted simulator registers quorum winners; resource owns its clock."""

    def __init__(self) -> None:
        self.term = 0
        self.owner: str | None = None
        self.expires = 0.0
        self.value: str | None = None

    def activate(self, owner: str, term: int, now: float, ttl: float = 5) -> None:
        if term <= self.term or ttl <= 0:
            raise ValueError("activation must have a newer term and positive lease")
        self.term, self.owner, self.expires = term, owner, now + ttl

    def write(self, owner: str, term: int, now: float, value: str) -> None:
        if owner != self.owner or term != self.term or now >= self.expires:
            raise ValueError("resource rejects stale or expired authority")
        self.value = value


class Election:
    """Deterministic message delivery with a shared test clock, not a network."""

    def __init__(self, directory: Path) -> None:
        self.now = 0.0
        self.nodes = {name: Node(name, directory) for name in ("a", "b", "c")}
        self.blocked: set[frozenset[str]] = set()
        self.resource = Resource()
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
        if won:
            self.resource.activate(candidate, term, self.now)
        return won

    def broadcast(self, leader: str) -> None:
        node = self.nodes[leader]
        for name, peer in self.nodes.items():
            if name != leader and self.connected(leader, name):
                if not peer.heartbeat(node.term, self.now):
                    node.heartbeat(peer.term, self.now)

    def write(self, leader: str, value: str) -> None:
        node = self.nodes[leader]
        self.resource.write(leader, node.term, self.now, value)
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

def reject_write(cluster: Election, owner: str) -> None:
    before = cluster.resource.value
    try:
        cluster.write(owner, "stale")
    except ValueError:
        assert cluster.resource.value == before
    else:
        raise AssertionError("stale write accepted")


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


def check_v3(directory):
    cluster = Election(directory)
    assert cluster.campaign('a', 1)
    cluster.write('a', 'first')
    cluster.now = 5
    reject_write(cluster, 'a')
    cluster.isolate('a')
    cluster.now = 6
    assert cluster.campaign('b', 2)
    cluster.write('b', 'successor')
    assert cluster.nodes['a'].leader
    reject_write(cluster, 'a')
    return {'old_belief': True, 'old_write_rejected': True, 'value': cluster.resource.value, 'resource_term': 2}


if __name__ == "__main__":
    with TemporaryDirectory() as folder:
        case = Path(folder) / "v1"
        case.mkdir()
        print("v1", check_v1(case))
        case = Path(folder) / "v2"
        case.mkdir()
        print("v2", check_v2(case))
        case = Path(folder) / "v3"
        case.mkdir()
        print("v3", check_v3(case))
```

从仓库根目录运行：

```bash
uv run python -m labs.consensus.leader_election.experiments
```

先保留 v1/v2 检查，再检查期限恰好到 5 时写入失败、term2 的 b 可写 successor、a 仍自认 leader 但写入失败且值不变。没有日志复制，所以这只保护资源写权限。v4 扩充故障组合。
