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
