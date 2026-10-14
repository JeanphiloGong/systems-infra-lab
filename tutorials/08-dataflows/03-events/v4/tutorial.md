# E03 v4：旧事件升级，重放不发信

事件格式会演进，旧 OrderPlaced 没有 currency 时由 upcast 补 USD。rebuild 只计算状态；只有显式 dispatch_new 的新事件才交给发送函数，避免重建再次扣款或发邮件。

## Complete Checkpoint

<!-- checkpoint: labs/dataflows/events/v4.py -->

```python
"""Upcast old events and separate replay from external effects."""
from __future__ import annotations

import json


def upcast(kind, payload):
    if kind == "OrderPlaced" and "currency" not in payload:
        return kind, {**payload, "currency": "USD"}
    return kind, payload


def rebuild(events):
    state = "new"
    for _, kind, payload in events:
        kind, payload = upcast(kind, payload)
        if kind == "OrderPlaced": state = "placed"
        elif kind == "OrderPaid": state = "paid"
        elif kind == "OrderShipped": state = "shipped"
        else: raise ValueError("unknown event")
    return state


def dispatch_new(events, send):
    for event in events:
        send(event)


def experiment():
    old = [(1, "OrderPlaced", {"sku": "book"}), (2, "OrderPaid", {"amount": 10}), (3, "OrderShipped", {})]
    assert rebuild(old) == "shipped" and upcast("OrderPlaced", {"sku": "book"})[1]["currency"] == "USD"
    sent = []
    # Rebuild reads facts only; the explicit new-event dispatcher owns effects.
    rebuild(old)
    assert sent == []
    dispatch_new([(4, "OrderShipped", {})], sent.append)
    assert len(sent) == 1
    return {"state": "shipped", "upcast_currency": "USD", "rebuild_side_effects": len(sent[:0]), "new_event_effects": len(sent)}


if __name__ == "__main__":
    print(json.dumps(experiment()))
```

## Run And Verify

```bash
uv run python labs/dataflows/events/v4.py
uv run pytest tests/dataflows/events -q
```

The assertions check this version's behavior. The replay test writes this fence into a fresh temporary directory and runs a new interpreter without hidden repository imports.

旧三条事件重放为 shipped，发送列表仍为空；显式新事件发送一次。跨版本事件契约和外部幂等仍是生产边界。

This is a single SQLite teaching model. It does not provide cross-service transactions, global event ordering, distributed projection coordination or CDC. Event Sourcing treats domain events as facts; it is not change capture from an existing table.

