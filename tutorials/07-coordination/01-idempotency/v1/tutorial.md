# D01 v1: request-key deduplication

A request key is claimed under one lock together with order creation. A repeated key, including concurrent duplicates, returns the original order instead of running the business effect again. The lock stands in for a database unique constraint and transaction boundary.

将下面的完整代码保存为 `labs/coordination/idempotency/v1.py`；文件已存在时，以本版内容替换该文件。

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

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/coordination/idempotency/v1.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
