# C03 v6：用队列重放分区、丢包、重复和乱序

先提交 stable=yes，再隔离 a。a 的孤立写入不能提交；b/c 选出新领导者并提交 successor。网络恢复时，我们复制待投递消息、丢弃其中一条并逆序投递，最后发送心跳重新推进。所有节点必须保留 stable，并统一到 successor。

队列是显式传输模型，不是数字计数替代网络。每条消息进入节点 receive；trace 记录实际丢弃的方向与内容。request ID 使旧响应和重复响应不能倒退进度。实验覆盖指定有限轨迹，不宣称穷尽全部调度或证明 Raft。

## 从失败轨迹到实现

先阅读 experiments 中的场景输入与断言，再回到 Node 的状态转换。每次 receive 都由实际消息触发；持久化成功后才产生成功响应。完成这一版后，下面的整份 checkpoint 是下一版的可运行基线。

<!-- checkpoint: labs/consensus/raft/advanced.py -->

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
        self.base = saved.get('base', 0)
        self.base_term = saved.get('base_term', 0)
        self.snapshot_state = saved.get('snapshot_state', {})
        self.commit = saved.get('commit', 0)
        self.state = dict(self.snapshot_state)
        for entry in self.log[:self.commit - self.base]:
            self.state[entry['key']] = entry['value']
        self.role, self.votes = 'follower', set()
        self.match, self.next, self.pending = {}, {}, {}
        self.serial = 0
        self.fault = None

    @property
    def last(self):
        return self.base + len(self.log)

    def term_at(self, index):
        if index == self.base:
            return self.base_term
        return self.log[index - self.base - 1]['term']

    def persist(self):
        payload = {key: getattr(self, key) for key in
                   ('term', 'vote', 'log', 'base', 'base_term', 'snapshot_state', 'commit')}
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if self.fault == 'before_replace':
            os._exit(71)
        os.replace(temporary, self.path)
        if self.fault == 'after_replace':
            os._exit(72)
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        if self.fault == 'after_directory_sync':
            os._exit(73)

    def message(self, peer, kind, **fields):
        return dict(src=self.name, dst=peer, kind=kind, term=self.term, **fields)

    def campaign(self):
        self.term += 1
        self.vote, self.role, self.votes = self.name, 'candidate', {self.name}
        self.persist()
        return [self.message(peer, 'vote', last=self.last, last_term=self.term_at(self.last))
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
        if position <= self.base:
            return self.message(peer, 'snapshot', request=self.serial, base=self.base,
                                base_term=self.base_term, state=dict(self.snapshot_state))
        previous = position - 1
        return self.message(peer, 'append', request=self.serial, previous=previous,
                            previous_term=self.term_at(previous),
                            entries=copy.deepcopy(self.log[position - self.base - 1:]),
                            commit=self.commit)

    def apply(self, index):
        if index <= self.commit:
            return
        if index > self.last:
            raise ValueError('commit exceeds log')
        old, self.commit = self.commit, index
        self.persist()
        for position in range(old + 1, index + 1):
            entry = self.log[position - self.base - 1]
            self.state[entry['key']] = entry['value']

    def compact(self):
        if self.commit <= self.base:
            return
        term = self.term_at(self.commit)
        self.log = self.log[self.commit - self.base:]
        self.base, self.base_term = self.commit, term
        self.snapshot_state = dict(self.state)
        self.persist()

    def receive(self, message):
        source, kind, term = message['src'], message['kind'], message['term']
        if source not in self.members or source == self.name:
            raise ValueError('unknown peer')
        if term > self.term:
            self.term, self.vote, self.role = term, None, 'follower'
            self.persist()
        if term < self.term:
            if kind in ('append', 'snapshot'):
                return [self.message(source, 'ack', request=message['request'], ok=False, matched=0)]
            if kind == 'vote':
                return [self.message(source, 'voted', granted=False)]
            return []
        if kind == 'vote':
            fresh = (message['last_term'], message['last']) >= (self.term_at(self.last), self.last)
            granted = fresh and self.vote in (None, source)
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
        if kind == 'snapshot':
            self.role = 'follower'
            if message['base'] > self.commit:
                index = message['base']
                keep = index <= self.last and self.term_at(index) == message['base_term']
                self.log = self.log[index - self.base:] if keep else []
                self.base, self.base_term = index, message['base_term']
                self.snapshot_state = dict(message['state'])
                self.commit, self.state = index, dict(message['state'])
                self.persist()
            return [self.message(source, 'ack', request=message['request'],
                                 ok=True, matched=message['base'])]
        if kind == 'append':
            self.role = 'follower'
            previous = message['previous']
            if not self.base <= previous <= self.last or self.term_at(previous) != message['previous_term']:
                return [self.message(source, 'ack', request=message['request'], ok=False, matched=0)]
            for offset, entry in enumerate(message['entries'], previous + 1):
                if offset <= self.last and self.term_at(offset) != entry['term']:
                    if offset <= self.commit:
                        raise ValueError('committed prefix conflict')
                    del self.log[offset - self.base - 1:]
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

    def deliver(self, position=0, drop=False):
        message = self.queue.pop(position)
        lost = drop or (message['src'], message['dst']) in self.blocked
        self.trace.append(dict(message, dropped=lost))
        if not lost:
            node = self.nodes[message['dst']]
            valid_contact = message['kind'] in ('append', 'snapshot') and message['term'] >= node.term
            responses = node.receive(message)
            vote_granted = message['kind'] == 'vote' and responses[0]['granted']
            if valid_contact or vote_granted:
                self.deadline[node.name] = self.now + 10 + self.members.index(node.name)
            self.queue.extend(responses)

    def drain(self, limit=1000, reverse=False):
        for _ in range(limit):
            if not self.queue:
                return
            self.deliver(-1 if reverse else 0)
        raise RuntimeError('message budget exceeded')

    def restart(self, name):
        self.nodes[name] = Node(name, self.members, self.directory)
        self.deadline[name] = self.now + 10 + self.members.index(name)
```

<!-- checkpoint: labs/consensus/raft/advanced_experiments.py -->

```python
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .advanced import Cluster, Node


def faults(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.propose('a', 'stable', 'yes')
    cluster.drain()
    cluster.partition('a', 'bc')
    cluster.propose('a', 'mode', 'orphan')
    cluster.drain()
    assert cluster.nodes['a'].commit == 1
    cluster.timeout('b')
    cluster.drain()
    cluster.propose('b', 'mode', 'successor')
    cluster.drain()
    assert cluster.nodes['b'].commit == cluster.nodes['c'].commit == 2
    assert cluster.nodes['a'].state == {'stable': 'yes'}
    cluster.blocked.clear()
    cluster.queue.extend(cluster.nodes['b'].broadcast())
    cluster.queue.extend(copy.deepcopy(cluster.queue))
    cluster.deliver(drop=True)
    cluster.drain(reverse=True)
    cluster.queue.extend(cluster.nodes['b'].broadcast())
    cluster.drain()
    assert all(node.commit == 2 and node.state == {'stable': 'yes', 'mode': 'successor'}
               for node in cluster.nodes.values())
    assert cluster.nodes['a'].role == 'follower'
    return dict(final_commit=2, state=cluster.nodes['a'].state, delivered=len(cluster.trace),
                dropped=sum(item['dropped'] for item in cluster.trace))


def run(version=6):
    if version != 6:
        raise ValueError('this checkpoint runs version 6')
    with TemporaryDirectory() as folder:
        return faults(Path(folder))


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
```

## 检查点

在空目录中创建上述文件后运行：

```bash
python -m labs.consensus.raft.advanced_experiments
```

输出来自场景断言后的实际节点状态；不变量不成立会使进程失败。

这是一条固定成员教学链。它没有动态成员变更、联合共识、线性一致读协议或生产性能保证。验证通过后冻结本版代码，再进入下一版；测试通过不等于算法证明。

