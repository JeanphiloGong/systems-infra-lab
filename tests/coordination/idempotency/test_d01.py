from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest

from labs.coordination.idempotency import v0, v1, v2, v3, v4


def test_v0_response_loss_repeats_business_effect() -> None:
    service = v0.OrderService()
    assert service.create_order("ada") == "order-1"
    assert service.create_order("ada") == "order-2"
    assert len(service.orders) == 2


def test_v1_request_key_replays_response() -> None:
    service = v1.OrderService()
    first = service.create_order("request-1", "ada")
    assert service.create_order("request-1", "ada") == first
    assert len(service.orders) == 1
    with pytest.raises(ValueError):
        service.create_order("", "ada")


def test_v1_atomic_claim_handles_concurrent_duplicate_requests() -> None:
    service = v1.OrderService()
    barrier = Barrier(8)

    def request() -> str:
        barrier.wait()
        return service.create_order("request-concurrent", "ada")

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: request(), range(8)))
    assert responses == ["order-1"] * 8
    assert service.orders == ["order-1"]


def test_v2_crash_boundaries_are_distinct() -> None:
    service = v2.TransactionalOrders()
    with pytest.raises(ConnectionError):
        service.create("request-before", crash_at="before_commit")
    assert "request-before" not in service.orders
    with pytest.raises(ConnectionError):
        service.create("request-after", crash_at="after_commit")
    assert service.create("request-after") == "order-1"
    assert len(service.orders) == 1


def test_v3_conflict_processing_replay_and_expiry() -> None:
    store = v3.IdempotencyStore(retention=1)
    assert store.create("request-1", {"customer": "ada"}) == "order-1"
    assert store.create("request-1", {"customer": "ada"}) == "order-1"
    with pytest.raises(ValueError):
        store.create("request-1", {"customer": "grace"})
    store.begin("request-2", {"customer": "ada"})
    with pytest.raises(RuntimeError):
        store.create("request-2", {"customer": "ada"})
    store.advance()
    store.advance()
    assert store.create("request-1", {"customer": "grace"}) == "order-2"


def test_v4_receiver_scope_defines_external_duplicate_behavior() -> None:
    deduped = v4.MailReceiver(supports_idempotency=True)
    service = v4.OrderAndMail(deduped)
    with pytest.raises(ConnectionError):
        service.create_then_send("request-1", "ada@example.test", response_lost=True)
    service.create_then_send("request-1", "ada@example.test")
    assert deduped.deliveries == ["ada@example.test"]

    unaware = v4.MailReceiver(supports_idempotency=False)
    service = v4.OrderAndMail(unaware)
    with pytest.raises(ConnectionError):
        service.create_then_send("request-1", "ada@example.test", response_lost=True)
    service.create_then_send("request-1", "ada@example.test")
    assert unaware.deliveries == ["ada@example.test", "ada@example.test"]
