from labs.transactions.locking.escalation import LockModel


def test_escalation_tradeoff_and_release() -> None:
    model = LockModel()
    assert model.acquire("A", 1)
    assert model.acquire("A", 2)
    assert model.acquire("B", 99)
    assert not model.escalate("A")
    assert len(model.rows) == 3
    model.release("B")
    assert model.escalate("A")
    assert model.rows == {}
    assert not model.acquire("B", 99)
    assert model.acquire("A", 99)
    model.release("A")
    assert model.acquire("B", 99)


def test_cannot_escalate_without_locks() -> None:
    assert not LockModel().escalate("A")
