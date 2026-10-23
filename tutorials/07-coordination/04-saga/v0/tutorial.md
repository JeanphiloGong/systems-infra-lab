# D04 v0：串行 Saga 留下部分效果

订单依次预留库存、扣款、安排配送。第三步失败时，前两步已产生业务效果；这不是数据库回滚。

先把三个服务缩成三个集合：订单 ID 出现在 `inventory` 表示库存已预留，出现在 `charged` 表示已扣款，出现在 `shipments` 表示已安排配送。真实服务可能在不同数据库中，本章只保留“调用已经生效”这个事实，暂不加入网络和消息队列。

`create_order` 按顺序执行三个动作。让 `ship` 在插入集合前抛错，观察 Python 异常只中断后续执行，不会撤销前两个集合的修改。入口捕获异常是为了能检查失败后的状态，不代表订单已经成功。

将下面的完整代码保存为 `labs/coordination/saga/v0.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/saga/v0.py -->

```python
from __future__ import annotations


class Services:
    def __init__(self) -> None:
        self.inventory: set[str] = set()
        self.charged: set[str] = set()
        self.shipments: set[str] = set()

    def reserve(self, order: str) -> None:
        self.inventory.add(order)

    def charge(self, order: str) -> None:
        self.charged.add(order)

    def ship(self, order: str, fail: bool = False) -> None:
        if fail:
            raise RuntimeError("delivery unavailable")
        self.shipments.add(order)


def create_order(services: Services, order: str, fail_delivery: bool = False) -> str:
    services.reserve(order)
    services.charge(order)
    services.ship(order, fail_delivery)
    return "completed"


if __name__ == "__main__":
    services = Services()
    try:
        create_order(services, "order-1", fail_delivery=True)
    except RuntimeError:
        pass
    print({"inventory": services.inventory, "charged": services.charged, "shipments": services.shipments})
```

## 运行

```bash
uv run python labs/coordination/saga/v0.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/saga -q
```

</details>

在仓库根目录使用 `uv sync` 准备环境。脚本应打印 `inventory={'order-1'}`、`charged={'order-1'}`、`shipments=set()`；`test_v0_partial_effect` 验证同样的部分效果，replay 测试另从正文提取围栏到临时目录执行。

这是后续设计的失败基线：库存和扣款没有丢，但也没有自动恢复一致。集合只在内存中，且天然去重，不能据此推断真实支付服务支持重试。下一版先记录哪个步骤完成，让重启后的协调者有依据继续，再讨论如何撤销业务效果。

