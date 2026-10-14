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
        if term < node.term:
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
