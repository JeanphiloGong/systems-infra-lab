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
