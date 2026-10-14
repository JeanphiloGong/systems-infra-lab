import pytest

from labs.recovery.ha.model import HACluster


def test_v0_measures_interruption_window():
    cluster = HACluster(); cluster.write("a", "order", "one"); cluster.stop("a"); cluster.tick(3)
    assert cluster.now == 3 and cluster.nodes["b"].rows == {"order": "one"}


def test_v1_manual_promotion_preserves_confirmed_write():
    cluster = HACluster(); cluster.write("a", "order", "one"); cluster.stop("a"); cluster.promote("b")
    cluster.write("b", "order", "two")
    assert cluster.primary == "b" and cluster.nodes["b"].rows["order"] == "two"


def test_v2_timeout_promotes_healthy_replica():
    cluster = HACluster(); cluster.write("a", "order", "one"); cluster.stop("a"); cluster.tick(6)
    assert cluster.primary == "b"


def test_v3_isolated_old_primary_is_fenced():
    cluster = HACluster(); cluster.write("a", "order", "one"); cluster.isolate("a"); cluster.promote("b")
    with pytest.raises(RuntimeError, match="fenced"):
        cluster.write("a", "order", "stale")
    cluster.write("b", "order", "two")
    assert cluster.nodes["a"].rows["order"] == "one"


def test_v4_rejoin_and_cutover():
    cluster = HACluster(); cluster.write("a", "order", "one"); cluster.stop("a"); cluster.promote("b"); cluster.write("b", "order", "two")
    cluster.nodes["a"].alive = True; cluster.rejoin("a")
    assert cluster.nodes["a"].rows == cluster.nodes["b"].rows
    cluster.promote("a"); cluster.write("a", "order", "three")
    assert cluster.nodes["a"].rows["order"] == "three"
