# C03 v3：由多数持久确认推进 commit

v2 能复制并修复日志，却还靠实验直接指定 commit。本版把提交决定接到真实确认消息：只有多数节点已持久保存同一位置，且该位置来自 leader 当前任期，才推进 commit 并通知 follower。

前置：[v2](../v2/tutorial.md) 的实际代码。

## 1. 由多数持久确认推进 commit

只在 ack 成功分支增加提交规则。match 存每个成员已确认的最大位置，leader 自己落盘后也算一份；取满足多数且 term_at(index)==当前任期的位置。apply 保存 commit 再更新状态机，随后 broadcast 让 follower 应用同一前缀。旧任期条目不能单独靠本轮多数计数提交；当前任期新条目提交后会一起提交前面的连续前缀。选举尚未检查候选日志，v4 前不能称作完整 Raft 安全实现。

下面是本版的完整 `model.py` checkpoint；替换上一版同名文件，不创建 advanced.py。

<!-- checkpoint: labs/consensus/raft/model.py -->

```python
from __future__ import annotations

import copy
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
        self.match, self.next, self.pending = {}, {}, {}
        self.serial = 0

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
        self.match[self.name] = self.last
        return self.broadcast()

    def broadcast(self):
        return [self.send_log(peer) for peer in self.members if peer != self.name]

    def send_log(self, peer):
        self.serial += 1
        self.pending[peer] = self.serial
        position = self.next[peer]
        previous = position - 1
        return self.message(peer, 'append', request=self.serial, previous=previous,
                            previous_term=self.term_at(previous),
                            entries=copy.deepcopy(self.log[position - 1:]),
                            commit=self.commit)

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
            if kind == 'append':
                return [self.message(source, 'ack', request=message['request'], ok=False, matched=0)]
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
            self.match = {name: 0 for name in self.members}
            self.match[self.name] = self.last
            self.next = {name: self.last + 1 for name in self.members}
            return self.broadcast()
        if kind == 'append':
            self.role = 'follower'
            previous = message['previous']
            if not 0 <= previous <= self.last or self.term_at(previous) != message['previous_term']:
                return [self.message(source, 'ack', request=message['request'], ok=False, matched=0)]
            for offset, entry in enumerate(message['entries'], previous + 1):
                if offset <= self.last and self.term_at(offset) != entry['term']:
                    if offset <= self.commit:
                        raise ValueError('committed prefix conflict')
                    del self.log[offset - 1:]
                if offset > self.last:
                    self.log.append(dict(entry))
            self.persist()
            matched = previous + len(message['entries'])
            self.apply(min(message['commit'], matched))
            return [self.message(source, 'ack', request=message['request'], ok=True, matched=matched)]
        if kind == 'ack':
            if self.role != 'leader' or self.pending.get(source) != message['request']:
                return []
            del self.pending[source]
            if not message['ok']:
                self.next[source] = max(1, self.next[source] - 1)
                return [self.send_log(source)]
            self.match[source] = max(self.match[source], message['matched'])
            self.next[source] = self.match[source] + 1
            for index in range(self.last, self.commit, -1):
                count = sum(matched >= index for matched in self.match.values())
                if count > len(self.members) // 2 and self.term_at(index) == self.term:
                    self.apply(index)
                    return self.broadcast()
            if self.next[source] <= self.last:
                return [self.send_log(source)]
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

    def propose(self, name, key, value):
        self.queue.extend(self.nodes[name].append(key, value))

    def deliver(self):
        message = self.queue.pop(0)
        lost = (message['src'], message['dst']) in self.blocked
        self.trace.append(dict(message, dropped=lost))
        if not lost:
            node = self.nodes[message['dst']]
            valid_contact = message['kind'] == 'append' and message['term'] >= node.term
            responses = node.receive(message)
            vote_granted = message['kind'] == 'vote' and responses[0]['granted']
            if valid_contact or vote_granted:
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

def prefix_repair(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    follower = cluster.nodes['b']
    bad = dict(src='a', dst='b', kind='append', term=1, request=1,
               previous=1, previous_term=1, entries=[], commit=0)
    assert not follower.receive(bad)[0]['ok']
    first = dict(bad, previous=0, previous_term=0,
                 entries=[dict(term=1, key='mode', value='old')])
    assert follower.receive(first)[0]['ok']
    assert follower.receive(first)[0]['ok'] and follower.last == 1
    repair = dict(first, term=3, request=2, commit=1,
                  entries=[dict(term=3, key='mode', value='new')])
    assert follower.receive(repair)[0]['ok']
    assert follower.log == [dict(term=3, key='mode', value='new')]
    assert follower.state == {'mode': 'new'} and follower.commit == 1
    try:
        follower.receive(dict(repair, term=4, entries=[dict(term=4, key='mode', value='unsafe')]))
    except ValueError as error:
        assert str(error) == 'committed prefix conflict'
    else:
        raise AssertionError('committed entry overwritten')
    return dict(bad_prefix_rejected=True, repaired_term=3, state=follower.state)


def majority(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.partition('a', 'bc')
    cluster.propose('a', 'mode', 'old-term')
    cluster.drain()
    assert cluster.nodes['a'].commit == 0
    # A new election raises the term while retaining the previous uncommitted entry.
    cluster.blocked.clear()
    cluster.timeout('a')
    cluster.drain()
    assert all(node.last == 1 for node in cluster.nodes.values())
    assert all(node.commit == 0 for node in cluster.nodes.values())
    old_term_commit = cluster.nodes['a'].commit
    cluster.propose('a', 'mode', 'current-term')
    cluster.drain()
    assert all(node.commit == 2 and node.state == {'mode': 'current-term'}
               for node in cluster.nodes.values())
    unknown = dict(src='not-a-member', dst='a', kind='ack', term=2, request=999, ok=True, matched=999)
    try:
        cluster.nodes['a'].receive(unknown)
    except ValueError:
        pass
    else:
        raise AssertionError('unknown peer accepted')
    return dict(old_term_commit=old_term_commit, current_term_commit=2,
                durable_lengths=[Node(n, cluster.members, directory).last for n in cluster.members])

def run_all():
    results = {}
    with TemporaryDirectory() as folder:
        case = Path(folder) / "state_machine"
        case.mkdir()
        results["state_machine"] = state_machine(case)
        case = Path(folder) / "election"
        case.mkdir()
        results["election"] = election(case)
        case = Path(folder) / "prefix_repair"
        case.mkdir()
        results["prefix_repair"] = prefix_repair(case)
        case = Path(folder) / "majority"
        case.mkdir()
        results["majority"] = majority(case)
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), sort_keys=True))
```

```bash
uv run python -m labs.consensus.raft.experiments
```

隔离 leader 后追加旧任期记录，commit 保持 0；恢复并提高任期使三份磁盘日志相同，也仍不提交旧条目。追加当前任期记录后三个节点 commit=2，mode=current-term。未知 peer 的 ack 被拒绝。v4 再保护换主时的日志完整性。
