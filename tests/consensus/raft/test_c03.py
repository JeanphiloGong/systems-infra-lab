from labs.consensus.raft.experiments import run
from labs.consensus.raft.model import Entry, Node


def test_checkpoints() -> None:
    assert run(0)["state"] == {"mode": "safe"}
    assert run(1)["double_vote_rejected"]
    assert run(2)["state"] == {"mode": "new"}


def test_prefix_mismatch_rejected(tmp_path) -> None:
    node = Node("f", tmp_path)
    node.current_term = 2
    node.append_command({"key": "x", "value": "a"}, term=2)
    assert not node.append_entries(term=2, prev_log_index=1, prev_log_term=1, entries=[], leader_commit=0)


def test_conflicting_suffix_is_repaired(tmp_path) -> None:
    node = Node("f", tmp_path)
    node.current_term = 3
    node.append_command({"key": "x", "value": "old"}, term=1)
    incoming = Entry(3, 1, {"key": "x", "value": "new"})
    assert node.append_entries(term=3, prev_log_index=0, prev_log_term=0, entries=[incoming], leader_commit=1)
    assert node.log == [incoming]
    assert node.state == {"x": "new"}
