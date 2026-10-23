# Q01 v2：查询副本需要明确的维护入口

沿用 v1 的 create_order/join_order。仪表盘希望直接取出组装好的订单，我们增加 view，但它只是派生数据。产品改名后原 view 不会自动更新，先故意绕过维护入口复现旧名称，再用 rename_product 修复所有受影响行。

## 1. 把维护责任交给写入入口

`rebuild_view` 从事实数据重建全部副本；`rename_product` 改产品并更新引用它的所有副本，返回实际修改数量。这里只演示单线程完整调用，没有把跨字典更新伪装成数据库原子事务。后续若有 I/O 失败，必须另外定义补偿或重建。

## 2. 继续同一份完整文件

替换 `checkpoint.py`。v1 的关联、无效输入拒绝与历史价格检查仍保留。

<!-- checkpoint: checkpoint.py -->

```python
customers = {1: "Ada"}
products = {7: "Widget"}
orders = {}


def create_order(order_id, customer_id, product_id, price):
    if customer_id not in customers or product_id not in products:
        raise ValueError("unknown customer or product")
    if order_id in orders:
        raise ValueError("order already exists")
    orders[order_id] = (customer_id, product_id, price)


def join_order(order_id):
    customer, product, price = orders[order_id]
    return {"customer": customers[customer], "product": products[product], "price": price}

view = {}


def rebuild_view():
    view.clear()
    for order_id in orders:
        view[order_id] = join_order(order_id)


def rename_product(product_id, name):
    products[product_id] = name
    updated = 0
    for order_id, (_, product, _) in orders.items():
        if product == product_id:
            view[order_id]["product"] = name
            updated += 1
    return updated

create_order(10, 1, 7, 12)
customers[1] = "A. Lovelace"
assert join_order(10) == {"customer": "A. Lovelace", "product": "Widget", "price": 12}
before = dict(orders)
try:
    create_order(11, 9, 7, 1)
except ValueError:
    pass
else:
    raise AssertionError("invalid order accepted")
assert orders == before

create_order(11, 1, 7, 13)
rebuild_view()
products[7] = "Renamed outside maintenance"
assert join_order(10)["product"] != view[10]["product"]
assert rename_product(7, "New Widget") == 2
assert all(view[key] == join_order(key) for key in orders)
assert orders[10][2] == 12 and orders[11][2] == 13
print({"maintained_views": len(view), "historical_prices": [orders[10][2], orders[11][2]]})
```

## 运行与检查

```bash
uv run python checkpoint.py
```

预期维护了两条副本，两个订单价格仍为 12 和 13。一条产品更新导致多条副本更新，这就是接下来要测量的代价。
