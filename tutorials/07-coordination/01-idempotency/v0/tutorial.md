# D01 v0: reproduce a duplicate after response loss

The server creates an order before the client receives the response. Retrying the same logical request has no key to identify it, so a second order is created.

将下面的完整代码保存为 `labs/coordination/idempotency/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/idempotency/v0.py -->

```python
from __future__ import annotations


class OrderService:
    def __init__(self) -> None:
        self.orders: list[str] = []

    def create_order(self, customer: str) -> str:
        order_id = f"order-{len(self.orders) + 1}"
        self.orders.append(order_id)
        return order_id


if __name__ == "__main__":
    service = OrderService()
    print(service.create_order("ada"))
    print(service.create_order("ada"))
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/coordination/idempotency/v0.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
