# C02 v1: a timeout starts a campaign, not authority

After the v0 partition, letting every silent node appoint itself violates exclusivity. Require votes from more than half of the fixed membership instead. In a three-node system, any two majorities intersect; one durable vote per voter per term prevents two different candidates from both collecting a majority in that term.

The scenario elects a in term 1, denies b another majority in term 1, delivers a heartbeat, and checks b has not timed out at time 4. After a is isolated, time 6 starts a new campaign: b and c grant b term 2. The trace records every delivered vote request and its decision; missing links do not count as votes.

Term 2 can exist while isolated a still thinks it leads term 1. campaign does not globally rewrite unreachable node state. The test explicitly asserts both beliefs coexist. Same-term majority uniqueness is the invariant, not global uniqueness of leadership beliefs. The trusted simulator registers only majority winners with the resource; clients cannot self-register an arbitrary integer as authority.

The shared infrastructure already writes vote records before replies. Version 2 makes that persistence boundary fail visibly in a separate process. This is election logic only: no replicated-log freshness test, log agreement, randomized retry, or fairness guarantee is implemented.

## Complete Checkpoint

Create the two files at their indicated paths in an empty directory. The code below is complete for this checkpoint. No repository source imports are needed beyond these extracted files.

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
```

<!-- checkpoint: labs/consensus/leader_election/experiments.py -->

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from labs.consensus.leader_election.model import Election, Node


def reject_write(cluster: Election, owner: str) -> None:
    before = cluster.resource.value
    try:
        cluster.write(owner, "stale")
    except ValueError:
        assert cluster.resource.value == before
    else:
        raise AssertionError("stale write accepted")


def run(version: int) -> dict[str, object]:
    with TemporaryDirectory() as folder:
        directory = Path(folder)
        cluster = Election(directory)
        if version == 0:
            # The intentionally broken baseline treats silence as authority.
            cluster.nodes["a"].leader = True
            cluster.isolate("a")
            cluster.now = 6
            for node in cluster.nodes.values():
                if node.timed_out(cluster.now):
                    node.leader = True
            beliefs = [n.name for n in cluster.nodes.values() if n.leader]
            assert len(beliefs) == 3
            return {"timeout_self_elected": beliefs, "split_brain": True}
        if version == 1:
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
        if version == 2:
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
            failed = subprocess.run([sys.executable, "-c", writer, folder], timeout=10)
            assert failed.returncode == 71
            recovered = subprocess.run([sys.executable, "-c", reader, folder], check=True, capture_output=True, text=True, timeout=10)
            return json.loads(recovered.stdout)
        if version == 3:
            assert cluster.campaign("a", 1)
            cluster.write("a", "first")
            cluster.now = 5
            reject_write(cluster, "a")
            cluster.isolate("a")
            cluster.now = 6
            assert cluster.campaign("b", 2)
            cluster.write("b", "successor")
            assert cluster.nodes["a"].leader
            reject_write(cluster, "a")
            return {"old_belief": True, "old_write_rejected": True, "value": cluster.resource.value, "resource_term": 2}
        if version == 4:
            outcomes = {}
            for fault in ("partition", "gc_pause", "restart"):
                case = directory / fault
                case.mkdir()
                cluster = Election(case)
                assert cluster.campaign("a", 1)
                cluster.write("a", "old")
                cluster.isolate("a")
                cluster.now = 6
                assert cluster.campaign("b", 2)
                cluster.write("b", "new")
                if fault == "restart":
                    cluster.nodes["a"] = Node("a", case, cluster.now)
                belief = cluster.nodes["a"].leader
                reject_write(cluster, "a")
                cluster.blocked.clear()
                cluster.broadcast("b")
                assert cluster.nodes["a"].term == 2
                assert not cluster.nodes["a"].leader
                reject_write(cluster, "a")
                outcomes[fault] = {"old_belief_before_heal": belief, "old_write_allowed": False, "term_after_heal": 2}
            return outcomes
        raise ValueError("version must be in 0..4")


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])), sort_keys=True))
```

From that directory, use Python 3.12 or later:

```bash
python -m labs.consensus.leader_election.experiments 1
```

From the repository, replay just this printed checkpoint with:

```bash
uv run python tests/consensus/leader_election/replay_c02.py --version 1
```

Replay extracts both files into an empty temporary directory and runs a fresh interpreter there. Version 2 also starts its writer and reader children within that directory. No network service or credentials are required.
