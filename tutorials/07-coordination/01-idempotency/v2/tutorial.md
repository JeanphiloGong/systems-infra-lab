# D01 v2: one transaction for business state and deduplication

The order record and request record are modeled as one atomic commit. A crash before commit leaves no record to replay; a response loss after commit is safe to retry.

<!-- checkpoint: labs/coordination/idempotency/v2.py -->

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Record:
    request_key: str
    order_id: str
    state: str = "committed"


class TransactionalOrders:
    def __init__(self) -> None:
        self.orders: dict[str, Record] = {}
        self.next_id = 1

    def create(self, request_key: str, crash_at: str | None = None) -> str:
        if request_key in self.orders:
            return self.orders[request_key].order_id
        order_id = f"order-{self.next_id}"
        if crash_at == "before_commit":
            raise ConnectionError("crash before transaction commit")
        self.orders[request_key] = Record(request_key, order_id)
        self.next_id += 1
        if crash_at == "after_commit":
            raise ConnectionError("response lost after transaction commit")
        return order_id


if __name__ == "__main__":
    service = TransactionalOrders()
    try:
        service.create("request-1", crash_at="after_commit")
    except ConnectionError:
        pass
    print(service.create("request-1"), len(service.orders))
```

