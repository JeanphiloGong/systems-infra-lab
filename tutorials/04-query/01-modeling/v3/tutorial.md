# Q01 v3：执行相同读写，再比较代价

v2 正确维护了两条派生记录，但“读更快、写更贵”还没有数字来源。本版让相同 10 次查询分别走关联读取与副本读取，逐次累计字典查询数；再改一次产品并累计实际副本更新数。计数是 Python 字典操作，不是数据库 I/O 或耗时。

## 1. 给两个实际读取路径增加计数

关联读取需要一份订单和两个描述，共三次字典查询；副本读取一次。没有在输出前直接指定 30 或 10：循环每次执行后增加计数，重复次数变化时结果也变化。产品维护仍调用 v2 的 rename_product，返回更新过的副本数。

## 2. 保留规则，加入同负载检查

替换 `checkpoint.py` 为完整文件：

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
normalized_reads = 0
view_reads = 0
for index in range(10):
    key = 10 + index % 2
    customer, product, price = orders[key]
    normalized_reads += 1
    name = customers[customer]
    normalized_reads += 1
    product_name = products[product]
    normalized_reads += 1
    derived = dict(view[key])
    view_reads += 1
    assert derived == {"customer": name, "product": product_name, "price": price}
extra_writes = rename_product(7, "New Widget")
assert normalized_reads == 30 and view_reads == 10 and extra_writes == 2
assert all(view[key] == join_order(key) for key in orders)
assert orders[10][2] == 12 and orders[11][2] == 13
print({"normalized_read_ops": normalized_reads, "view_read_ops": view_reads,
       "extra_view_writes": extra_writes, "historical_prices": [12, 13]})
```

## 运行与检查

```bash
uv run python checkpoint.py
```

同一批结果正确时，才比较 30 次关联字典读取和 10 次副本读取。维护一次产品名实际更新两条副本；它们不是固定性能承诺。最终保存当前描述、历史价格和派生副本三种语义；没有缓存过期、持久化或并发发布。
