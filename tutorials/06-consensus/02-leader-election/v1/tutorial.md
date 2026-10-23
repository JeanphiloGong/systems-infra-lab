# C02 v1：把超时改成多数派投票

v0 的三个节点都把超时当成授权。现在超时只能发起竞选：固定成员 a/b/c 中至少两票才当选。任期区分选举轮次，同一节点在同一任期只投一名候选人。多数派相交因此排除同任期两个胜者；不同任期的旧 leader 仍可能相信自己有效。

前置：完成 [v0](../v0/tutorial.md)。

## 1. 把超时改成多数派投票

保留 v0 的 `timed_out`，增加 `request_vote` 和 `campaign`。`campaign` 要求候选人提出比自己已知任期更大的编号；失败也不能在同一任期改投。`heartbeat` 更新最近联系时间，并在更高任期退位。`blocked` 只决定消息能否到达，不等于授权状态。

将 `labs/consensus/leader_election/model.py` 替换为本版完整 checkpoint：

<!-- checkpoint: labs/consensus/leader_election/model.py -->

```python
from __future__ import annotations


class Node:
    """One sequential event-loop node; votes are volatile in this version."""

    def __init__(self, name: str, now: float = 0) -> None:
        self.name = name
        self.term, self.vote = 0, None
        self.leader = False
        self.last_heartbeat = now

    def request_vote(self, candidate: str, term: int) -> bool:
        if term < self.term:
            return False
        if term > self.term:
            self.term, self.vote, self.leader = term, None, False
        if self.vote not in (None, candidate):
            return False
        self.vote = candidate
        return True

    def heartbeat(self, term: int, now: float) -> bool:
        if term < self.term:
            return False
        if term > self.term:
            self.term, self.vote = term, None
        self.leader = False
        self.last_heartbeat = now
        return True

    def timed_out(self, now: float, timeout: float = 5) -> bool:
        return now - self.last_heartbeat >= timeout


class Election:
    """Deterministic message delivery with a shared test clock, not a network."""

    def __init__(self) -> None:
        self.now = 0.0
        self.nodes = {name: Node(name) for name in ("a", "b", "c")}
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
    cluster = Election()
    assert cluster.campaign("a", 1)
    assert not cluster.campaign("b", 1)
    assert all(n.vote == "a" for n in cluster.nodes.values())
    cluster.broadcast("a")
    cluster.now = 4
    assert not cluster.nodes["b"].timed_out(cluster.now)
    cluster.isolate("a")
    cluster.now = 6
    assert cluster.nodes["b"].timed_out(cluster.now)
    assert cluster.campaign("b", 2)
    assert cluster.nodes["a"].leader and cluster.nodes["b"].leader
    assert cluster.nodes["c"].vote == "b"
    return {"term1_winner": "a", "term2_winner": "b", "message_trace": cluster.messages}


if __name__ == "__main__":
    with TemporaryDirectory() as folder:
        case = Path(folder) / "v1"
        case.mkdir()
        print("v1", check_v1(case))
```

从仓库根目录运行：

```bash
uv run python -m labs.consensus.leader_election.experiments
```

断言检查 a 赢 term1、b 不能在 term1 再获胜；时间到 6 且 a 被隔离后，b/c 可以选出 term2 的 b。a 与 b 的 leader 判断同时为真是预期暴露的缺口。当前投票尚不持久；v2 修复重启遗忘。
