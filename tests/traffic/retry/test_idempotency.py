from labs.traffic.retry.idempotency import OperationStore


def test_duplicate_operation_id_runs_once() -> None:
    calls = 0
    def effect() -> str:
        nonlocal calls
        calls += 1
        return "charged"
    store: OperationStore[str] = OperationStore()
    assert store.run("payment-1", effect) == "charged"
    assert store.run("payment-1", effect) == "charged"
    assert calls == 1
