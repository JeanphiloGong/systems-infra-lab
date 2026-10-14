from itertools import permutations

import pytest

from labs.consensus.leader_election.experiments import run
from labs.consensus.leader_election.model import Election, Node


@pytest.mark.parametrize("version", range(5))
def test_checkpoint_experiment(version: int) -> None:
    assert run(version)


def test_every_campaign_order_has_one_majority_winner(tmp_path) -> None:
    for order in permutations("abc"):
        directory = tmp_path / "".join(order)
        directory.mkdir()
        cluster = Election(directory)
        winners = [candidate for candidate in order if cluster.campaign(candidate, 1)]
        assert winners == [order[0]]


def test_quorum_is_required_and_healed_node_rejects_old_messages(tmp_path) -> None:
    cluster = Election(tmp_path)
    cluster.isolate("a")
    assert not cluster.campaign("a", 1)
    assert cluster.campaign("b", 2)
    cluster.blocked.clear()
    cluster.broadcast("b")
    assert not cluster.nodes["a"].request_vote("a", 1)
    assert not cluster.nodes["a"].heartbeat(1, 100)
    assert cluster.nodes["a"].last_heartbeat == 0


def test_resource_rejects_wrong_owner_even_with_current_term(tmp_path) -> None:
    cluster = Election(tmp_path)
    assert cluster.campaign("a", 1)
    with pytest.raises(ValueError):
        cluster.resource.write("b", 1, 0, "forged")
    cluster.now = 5
    with pytest.raises(ValueError):
        cluster.write("a", "late")


def test_restart_preserves_vote_and_clears_volatile_leader(tmp_path) -> None:
    node = Node("a", tmp_path)
    assert node.request_vote("b", 7)
    node.leader = True
    restarted = Node("a", tmp_path)
    assert (restarted.term, restarted.vote, restarted.leader) == (7, "b", False)
    assert not restarted.request_vote("c", 7)
