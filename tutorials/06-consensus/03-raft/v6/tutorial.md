# C03 v6：控制消息丢失、重复和倒序

v5 的持久化检查不覆盖迟到响应。旧 leader 被隔离后产生未提交后缀，剩下多数提交不同后缀，再恢复通信并重复、倒序、丢弃消息。目标是所有节点最后保留已提交前缀并接受新 leader 的后缀。

前置：[v5](../v5/tutorial.md) 的实际代码。

## 1. 控制消息丢失、重复和倒序

核心 Node 不变。Cluster.deliver 新增 position/drop，drain 新增 reverse；原来的 term、pending 和 committed-prefix 规则要承受新日程。丢包后必须再显式 broadcast 才保证有新尝试；模型不承诺无限丢包下仍可用。故障 trace 记录每条投递是否被丢弃，计数来自实际队列。

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
        self.fault = None

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

    def deliver(self, position=0, drop=False):
        message = self.queue.pop(position)
        lost = drop or (message['src'], message['dst']) in self.blocked
        self.trace.append(dict(message, dropped=lost))
        if not lost:
            node = self.nodes[message['dst']]
            valid_contact = message['kind'] == 'append' and message['term'] >= node.term
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

def freshness(directory):
    cluster = Cluster(directory)
    cluster.timeout('a')
    cluster.drain()
    cluster.partition('c', 'ab')
    cluster.propose('a', 'mode', 'committed')
    cluster.drain()
    assert cluster.nodes['a'].commit == cluster.nodes['b'].commit == 1
    cluster.blocked.clear()
    cluster.timeout('c')
    cluster.drain()
    assert cluster.nodes['c'].role == 'candidate'
    assert cluster.nodes['c'].votes == {'c'}
    cluster.timeout('b')
    cluster.drain()
    assert cluster.nodes['b'].role == 'leader'
    cluster.propose('b', 'next', 'kept')
    cluster.drain()
    assert all(node.state == {'mode': 'committed', 'next': 'kept'} for node in cluster.nodes.values())
    return dict(stale_candidate_votes=1, winner='b', preserved='committed')

def crashes(directory):
    outcomes = {}
    for action in ('vote', 'append', 'commit'):
        for fault, expected_code in [('before_replace', 71), ('after_replace', 72), ('after_directory_sync', 73)]:
            case = directory / (action + '-' + fault)
            case.mkdir()
            node = Node('a', ('a', 'b', 'c'), case)
            node.term = 1
            node.role = 'leader'
            node.match = dict(a=0, b=0, c=0)
            node.next = dict(a=1, b=1, c=1)
            node.persist()
            if action == 'commit':
                node.append('mode', 'saved')
            worker = """import sys
from pathlib import Path
from labs.consensus.raft.model import Node
n=Node('a',('a','b','c'),Path(sys.argv[1]))
n.fault=sys.argv[3]
action=sys.argv[2]
if action=='vote': n.campaign()
elif action=='append':
 n.role='leader'; n.match=dict(a=0,b=0,c=0); n.next=dict(a=1,b=1,c=1); n.append('mode','saved')
elif action=='commit': n.apply(1)
"""
            killed = subprocess.run([sys.executable, '-c', worker, str(case), action, fault], timeout=10)
            assert killed.returncode == expected_code
            recovered = Node('a', ('a', 'b', 'c'), case)
            published = fault != 'before_replace'
            if action == 'vote':
                assert recovered.term == (2 if published else 1)
                assert recovered.vote == ('a' if published else None)
            if action == 'append':
                assert recovered.last == (1 if published else 0)
                assert recovered.state == {}
            if action == 'commit':
                assert recovered.commit == (1 if published else 0)
                assert recovered.state == ({'mode': 'saved'} if published else {})
            outcomes[action + ':' + fault] = dict(exit=killed.returncode, commit=recovered.commit)
    return outcomes

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
        case = Path(folder) / "freshness"
        case.mkdir()
        results["freshness"] = freshness(case)
        case = Path(folder) / "crashes"
        case.mkdir()
        results["crashes"] = crashes(case)
        case = Path(folder) / "faults"
        case.mkdir()
        results["faults"] = faults(case)
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), sort_keys=True))
```

```bash
uv run python -m labs.consensus.raft.experiments
```

先提交 stable=yes，隔离 a 后它的 orphan 不能提交。b/c 提交 successor；网络恢复后即使消息重复/倒序/丢失，最终三节点 commit=2、stable=yes、mode=successor，a 已退位。输出的 dropped 是真实故障数量。
