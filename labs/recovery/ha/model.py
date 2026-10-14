from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Replica:
    name: str
    role: str = "standby"
    generation: int = 0
    rows: dict[str, str] = field(default_factory=dict)
    alive: bool = True
    isolated: bool = False
    last_heartbeat: int = 0


class HACluster:
    """A two-replica failover model with explicit fencing and logical time."""

    def __init__(self) -> None:
        self.nodes = {"a": Replica("a", role="primary"), "b": Replica("b")}
        self.primary = "a"
        self.generation = 1
        self.nodes["a"].generation = self.generation
        self.now = 0
        self.events: list[dict[str, object]] = []

    def write(self, node: str, key: str, value: str) -> None:
        replica = self.nodes[node]
        if not replica.alive or replica.isolated or replica.role != "primary" or replica.generation != self.generation:
            raise RuntimeError("write fenced")
        replica.rows[key] = value
        for peer in self.nodes.values():
            if peer.name != node and peer.alive and not peer.isolated:
                peer.rows = dict(replica.rows)
                peer.generation = self.generation
        self.events.append({"at": self.now, "kind": "write", "node": node, "key": key})

    def isolate(self, node: str) -> None:
        self.nodes[node].isolated = True
        self.events.append({"at": self.now, "kind": "isolate", "node": node})

    def stop(self, node: str) -> None:
        self.nodes[node].alive = False
        self.events.append({"at": self.now, "kind": "stop", "node": node})

    def promote(self, node: str) -> None:
        candidate = self.nodes[node]
        if not candidate.alive or candidate.isolated:
            raise RuntimeError("candidate unavailable")
        old = self.primary
        self.generation += 1
        candidate.role, candidate.generation = "primary", self.generation
        self.primary = node
        self.nodes[old].role = "standby"
        self.events.append({"at": self.now, "kind": "promote", "old": old, "new": node, "generation": self.generation})

    def tick(self, seconds: int, timeout: int = 5) -> None:
        if seconds < 0:
            raise ValueError("logical time cannot go backwards")
        self.now += seconds
        current = self.nodes[self.primary]
        if current.alive and not current.isolated:
            for peer in self.nodes.values():
                if peer.name != self.primary and peer.alive and not peer.isolated:
                    peer.last_heartbeat = self.now
        if not current.alive or current.isolated:
            candidates = [node for node in self.nodes.values() if node.name != self.primary and node.alive and not node.isolated]
            if candidates and self.now - candidates[0].last_heartbeat >= timeout:
                self.promote(candidates[0].name)

    def rejoin(self, node: str) -> None:
        replica = self.nodes[node]
        if replica.alive and not replica.isolated:
            replica.rows = dict(self.nodes[self.primary].rows)
            replica.generation = self.generation
            replica.role = "standby"
            self.events.append({"at": self.now, "kind": "rejoin", "node": node, "generation": self.generation})
