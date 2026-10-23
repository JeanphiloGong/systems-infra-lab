# D01 v4: external effects and exactly-once scope

A local transaction cannot undo or deduplicate an external email call. A receiver that supports the same idempotency key can provide one delivery within its own scope; an unaware receiver retains duplicate risk.

将下面的完整代码保存为 `labs/coordination/idempotency/v4.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/idempotency/v4.py -->

```python
from __future__ import annotations


class MailReceiver:
    def __init__(self, supports_idempotency: bool) -> None:
        self.supports_idempotency = supports_idempotency
        self.deliveries: list[str] = []
        self.seen_keys: set[str] = set()

    def send(self, key: str, address: str) -> None:
        if self.supports_idempotency and key in self.seen_keys:
            return
        self.seen_keys.add(key)
        self.deliveries.append(address)


class OrderAndMail:
    def __init__(self, mail: MailReceiver) -> None:
        self.mail = mail
        self.orders: dict[str, str] = {}

    def create_then_send(self, key: str, address: str, response_lost: bool = False) -> str:
        order_id = self.orders.setdefault(key, f"order-{len(self.orders) + 1}")
        self.mail.send(key, address)
        if response_lost:
            raise ConnectionError("response lost after external effect")
        return order_id


if __name__ == "__main__":
    receiver = MailReceiver(supports_idempotency=True)
    service = OrderAndMail(receiver)
    try:
        service.create_then_send("request-1", "ada@example.test", response_lost=True)
    except ConnectionError:
        pass
    print(service.create_then_send("request-1", "ada@example.test"), receiver.deliveries)
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/coordination/idempotency/v4.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
