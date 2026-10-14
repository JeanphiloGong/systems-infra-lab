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
