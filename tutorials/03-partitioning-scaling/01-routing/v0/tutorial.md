# P01 v0：先让一份订单数据能够读写

客服输入订单 ID 20，希望看到“已付款”。我们先把系统压缩为一份内存字典：
整数键表示订单 ID，字符串表示状态。没有网络和持久化，退出进程数据就消失。
这个起点保留了分片以后仍必须满足的契约：写入某个 ID 后，按同一个 ID 应该找到它。

先在仓库根目录运行 `uv sync --locked`。本篇无需数据库。

## 1. 从调用者的订单开始

这段独立 Python 示例可以直接运行：

```python
orders: dict[int, str] = {}
orders[20] = "created"
orders[20] = "paid"
assert orders.get(20) == "paid"
assert orders.get(99) is None
```

相同 ID 的第二次写入覆盖第一次。查询缺失订单返回 None，这与保存一个空字符串不同。
这里的类型注解表达调用契约，不会自动把字符串 `"20"` 变成整数。
现在点查已经正确；下一位客服却要求“列出 ID 在 5 到 20 之间的订单”，单次 `get` 无法回答。

## 2. 给范围一个明确边界

在前面示例末尾应用这个局部 patch：

```python
orders[5] = "created"
orders[10] = "shipped"
rows = sorted((key, value) for key, value in orders.items() if 5 <= key < 20)
assert rows == [(5, "created"), (10, "shipped")]
```

采用左闭右开区间 `[start, stop)`，因此 20 不在结果中。排序很重要：字典迭代顺序是插入顺序，
不是键的数值顺序。这个实现检查所有订单再排序匹配项；它是正确基线，不是一个范围索引。
`start == stop` 或起点大于终点时，结果自然为空，本版不会把它们当作输入异常。

## 3. 固定完整的单分片检查点

将刚才的操作收拢为三个函数，调用者仍拥有并传入同一份字典。新建
`labs/partitioning/routing/single.py`，这是完整 checkpoint：

<!-- checkpoint: labs/partitioning/routing/single.py -->
```python
def put_order(orders: dict[int, str], order_id: int, status: str) -> None:
    orders[order_id] = status


def get_order(orders: dict[int, str], order_id: int) -> str | None:
    return orders.get(order_id)


def scan_orders(orders: dict[int, str], start: int, stop: int) -> list[tuple[int, str]]:
    return sorted((key, value) for key, value in orders.items() if start <= key < stop)
```

运行以下检查，只操作本进程内的数据：

```bash
uv run python - <<'PY'
from labs.partitioning.routing.single import get_order, put_order, scan_orders

orders: dict[int, str] = {}
assert get_order(orders, 20) is None
put_order(orders, 20, "created")
put_order(orders, 20, "paid")
put_order(orders, 5, "created")
put_order(orders, 10, "shipped")
assert get_order(orders, 20) == "paid"
assert scan_orders(orders, 5, 20) == [(5, "created"), (10, "shipped")]
assert scan_orders(orders, 20, 20) == []
assert scan_orders(orders, 30, 20) == []
print("single shard ok")
PY
```

成功输出 `single shard ok`。空数据、覆盖更新和范围边界都不需要外部服务。
当前全部数据仍落在一个节点：当它的容量不足时，需要决定哪些 ID 分给哪个新节点。
下一版添加确定性路由，并观察节点数变化后同一个 ID 的归属为什么会改变。
