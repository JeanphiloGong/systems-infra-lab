# C03 v1：把任期和投票接到同一节点

v0 只回答“哪条命令已应用”。三个节点还需要决定谁接收新命令，重启后也不能在同一任期重复投票。本版增加持久任期/投票和带逻辑时钟的消息队列；日志与 commit 仍属于同一 Node，尚不复制。

前置：[v0](../v0/tutorial.md) 的实际代码。

## 1. 把任期和投票接到同一节点

构造从 Node(name) 改为 Node(name, members, directory)，实验调用一并更新；新增条目携带 term，原 key/value 不变。持久文件保存 term、vote、log、commit；role 和收到的票是易失状态，重启回 follower。写临时文件、fsync、原子 replace、fsync 目录之后才答复。Cluster 排队交付 vote/voted，deadline 使用错开的逻辑时刻；同刻竞选会平票，下一轮错开可收敛。本版尚无心跳，不能长时间维持 leader。

下面是本版的完整 `model.py` checkpoint；替换上一版同名文件，不创建 advanced.py。

<!-- checkpoint: labs/consensus/raft/model.py -->

```python
from __future__ import annotations

import json
import os
from pathlib import Path


class Node:
    """Fixed-membership teaching node; sequential event loop, trusted peers."""

    def __init__(self, name, members, directory: Path):
        self.name, self.members = name, tuple(members)
        self.path = directory / (name + '.json')
        saved = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.term = saved.get('term', 0)
        self.vote = saved.get('vote')
        self.log = saved.get('log', [])
        self.commit = saved.get('commit', 0)
        self.state = {}
        for entry in self.log[:self.commit]:
            self.state[entry['key']] = entry['value']
        self.role, self.votes = 'follower', set()

    @property
    def last(self):
        return len(self.log)

    def term_at(self, index):
        if index == 0:
            return 0
        return self.log[index - 1]['term']

    def persist(self):
        payload = {key: getattr(self, key) for key in
                   ('term', 'vote', 'log', 'commit')}
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def message(self, peer, kind, **fields):
        return dict(src=self.name, dst=peer, kind=kind, term=self.term, **fields)

    def campaign(self):
        self.term += 1
        self.vote, self.role, self.votes = self.name, 'candidate', {self.name}
        self.persist()
        return [self.message(peer, 'vote')
                for peer in self.members if peer != self.name]

    def append(self, key, value):
        if self.role != 'leader':
            raise ValueError('only elected leader accepts proposals')
        self.log.append(dict(term=self.term, key=key, value=value))
        self.persist()
        return self.last

    def apply(self, index):
        if index <= self.commit:
            return
        if index > self.last:
            raise ValueError('commit exceeds log')
        old, self.commit = self.commit, index
        self.persist()
        for position in range(old + 1, index + 1):
            entry = self.log[position - 1]
            self.state[entry['key']] = entry['value']

    def receive(self, message):
        source, kind, term = message['src'], message['kind'], message['term']
        if source not in self.members or source == self.name:
            raise ValueError('unknown peer')
        if term > self.term:
            self.term, self.vote, self.role = term, None, 'follower'
            self.persist()
        if term < self.term:
            if kind == 'vote':
                return [self.message(source, 'voted', granted=False)]
            return []
        if kind == 'vote':
            granted = self.vote in (None, source)
            if granted:
                self.vote = source
                self.persist()
            return [self.message(source, 'voted', granted=granted)]
        if kind == 'voted':
            if self.role != 'candidate' or not message['granted']:
                return []
            self.votes.add(source)
            if len(self.votes) <= len(self.members) // 2:
                return []
            self.role = 'leader'
            return []
        raise ValueError('unknown message')


class Cluster:
    """Bounded message queue; timers use explicit logical time, no wall sleeps."""

    def __init__(self, directory, members=('a', 'b', 'c')):
        self.directory, self.members = directory, tuple(members)
        self.nodes = {name: Node(name, self.members, directory) for name in members}
        self.queue, self.trace = [], []
        self.blocked = set()
        self.now = 0
        self.deadline = {name: 10 + index for index, name in enumerate(members)}

    def partition(self, first, second):
        self.blocked = {(a, b) for a in first for b in second} | {(b, a) for a in first for b in second}

    def tick(self, now):
        if now < self.now:
            raise ValueError('logical time cannot go backwards')
        self.now = now
        for name, node in self.nodes.items():
            if node.role != 'leader' and now >= self.deadline[name]:
                self.timeout(name)

    def timeout(self, name):
        self.deadline[name] = self.now + 10 + self.members.index(name)
        self.queue.extend(self.nodes[name].campaign())

    def deliver(self):
        message = self.queue.pop(0)
        lost = (message['src'], message['dst']) in self.blocked
        self.trace.append(dict(message, dropped=lost))
        if not lost:
            node = self.nodes[message['dst']]
            responses = node.receive(message)
            vote_granted = message['kind'] == 'vote' and responses[0]['granted']
            if vote_granted:
                self.deadline[node.name] = self.now + 10 + self.members.index(node.name)
            self.queue.extend(responses)

    def drain(self, limit=1000):
        for _ in range(limit):
            if not self.queue:
                return
            self.deliver()
        raise RuntimeError('message budget exceeded')

    def restart(self, name):
        self.nodes[name] = Node(name, self.members, self.directory)
        self.deadline[name] = self.now + 10 + self.members.index(name)
```

## 2. 运行本版检查并保留旧行为

替换 `labs/consensus/raft/experiments.py`。各检查使用单独临时目录，数据和故障互不污染。

<!-- checkpoint: labs/consensus/raft/experiments.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import subprocess
import sys

from .model import Node, Cluster

def state_machine(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    node = cluster.nodes['a']
    node.append('mode', 'safe')
    # Direct local apply checks the state machine; it is not a client commit API.
    assert node.state == {} and node.commit == 0
    node.apply(1)
    node.apply(1)
    assert node.state == {'mode': 'safe'} and node.commit == 1
    try:
        node.apply(2)
    except ValueError:
        pass
    else:
        raise AssertionError('committed beyond log')
    return dict(commit_index=node.commit, state=node.state)


def election(directory):
    cluster = Cluster(directory)
    cluster.deadline = {name: 10 for name in cluster.members}
    cluster.tick(10)
    cluster.drain()
    assert all(node.role == 'candidate' for node in cluster.nodes.values())
    assert {node.term for node in cluster.nodes.values()} == {1}
    cluster.deadline = dict(a=20, b=21, c=22)
    cluster.tick(20)
    cluster.drain()
    assert cluster.nodes['a'].role == 'leader'
    cluster.restart('b')
    assert cluster.nodes['b'].vote == 'a'
    reply = cluster.nodes['b'].receive(dict(src='c', dst='b', kind='vote', term=2, last=0, last_term=0))
    assert not reply[0]['granted']
    worker = """import os,sys
from pathlib import Path
from labs.consensus.raft.model import Node
n=Node('b',('a','b','c'),Path(sys.argv[1]))
assert n.vote=='a' and n.term==2
assert not n.receive(dict(src='c',kind='vote',term=2,last=0,last_term=0))[0]['granted']
os._exit(74)
"""
    crashed = subprocess.run([sys.executable, '-c', worker, str(directory)], timeout=10)
    assert crashed.returncode == 74
    cluster.restart('b')
    assert cluster.nodes['b'].vote == 'a' and cluster.nodes['b'].term == 2
    return dict(simultaneous_candidates=3, elected_term=2, restart_vote=cluster.nodes['b'].vote,
                messages=len(cluster.trace), restart_exit=crashed.returncode)

def run_all():
    results = {}
    with TemporaryDirectory() as folder:
        case = Path(folder) / "state_machine"
        case.mkdir()
        results["state_machine"] = state_machine(case)
        case = Path(folder) / "election"
        case.mkdir()
        results["election"] = election(case)
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), sort_keys=True))
```

```bash
uv run python -m labs.consensus.raft.experiments
```

保留本地状态机检查，再让三个节点同刻竞选而平票；错开下一次期限后 a 在 term2 当选。b 进程退出后仍保存投给 a 的票，拒绝同任期给 c 投票。下一版把日志加入消息路径。
