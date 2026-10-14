# D01 v1: request-key deduplication

A request key is claimed under one lock together with order creation. A repeated key, including concurrent duplicates, returns the original order instead of running the business effect again. The lock stands in for a database unique constraint and transaction boundary.

<!-- checkpoint: labs/coordination/idempotency/v1.py -->

```python
from __future__ import annotations

from threading import Lock


class OrderService:
    def __init__(self) -> None:
        self.orders: list[str] = []
        self.responses: dict[str, str] = {}
        self._lock = Lock()

    def create_order(self, request_key: str, customer: str) -> str:
        if not request_key:
            raise ValueError("request_key is required")
        with self._lock:
            if request_key in self.responses:
                return self.responses[request_key]
            order_id = f"order-{len(self.orders) + 1}"
            self.orders.append(order_id)
            self.responses[request_key] = order_id
            return order_id


if __name__ == "__main__":
    service = OrderService()
    print(service.create_order("request-1", "ada"))
    print(service.create_order("request-1", "ada"))
```

