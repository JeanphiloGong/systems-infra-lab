from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from labs.coordination.saga import v0, v1, v2, v3, v4


def test_v0_partial_effect() -> None:
    services = v0.Services()
    with pytest.raises(RuntimeError):
        v0.create_order(services, "o1", True)
    assert services.inventory == {"o1"} and services.charged == {"o1"} and not services.shipments


def test_v1_restart_does_not_repeat_done_step(tmp_path) -> None:
    path = str(tmp_path / "saga.db")
    calls = []
    saga = v1.Saga(path)
    saga.run("o1", "reserve", lambda: calls.append("reserve"))
    saga.db.close()
    saga = v1.Saga(path)
    saga.run("o1", "reserve", lambda: calls.append("duplicate"))
    assert calls == ["reserve"]


def test_v2_reverse_compensation_is_idempotent() -> None:
    saga = v2.Saga(":memory:")
    effects = []
    saga.step("o1", 1, "reserve", lambda: effects.append("reserve"))
    saga.step("o1", 2, "charge", lambda: effects.append("charge"))
    saga.compensate("o1", 2, lambda: effects.append("refund"))
    saga.compensate("o1", 1, lambda: effects.append("release"))
    saga.compensate("o1", 1, lambda: effects.append("duplicate"))
    assert effects == ["reserve", "charge", "refund", "release"]


def test_v3_timeout_retries_then_manual() -> None:
    saga = v3.Saga(":memory:")
    saga.seed("o1", 1, "reserve")
    assert saga.compensate("o1", 1, lambda _: (_ for _ in ()).throw(TimeoutError()), 2) == "manual"
    assert saga.status("o1") == [(1, "reserve", "manual", 2)]


def test_v4_concurrent_orders_are_key_isolated() -> None:
    orders = v4.Orders(":memory:")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: orders.apply("o1", "reserve"), range(4)))
        results += list(pool.map(lambda _: orders.apply("o2", "reserve"), range(4)))
    assert sum(results) == 2
    assert orders.snapshot() == [("o1", "reserve", "done"), ("o2", "reserve", "done")]
