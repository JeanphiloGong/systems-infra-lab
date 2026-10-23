# Q01 v1：按 ID 关联，并在写入之前拒绝无效订单

v0 中一个客户的名字复制到了多行。现在独立保存客户、产品和订单：订单的 customer_id/product_id 引用当前描述，而 price 保留购买当时的事实。当前例子改用客户 1、产品 7、订单 10；这些是固定输入，不是迁移旧数据的脚本。

## 1. 区分当前描述与历史事实

`join_order` 从同一订单的 ID 取出客户和产品，再组合返回值。改客户姓名会影响下次读取；改产品描述不会修改已保存价格。外键的最小规则放在 `create_order`：两端存在后才插入，错误请求不得改变 orders。这里用 Python 字典说明规则，真实数据库用 FOREIGN KEY 保护并发入口。

## 2. 替换完整检查点

替换仓库根目录 `checkpoint.py`；下面先实现规则，再调用有效和无效输入。

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
print({"join": join_order(10), "invalid_order_rejected": 11 not in orders})
```

## 运行与检查

```bash
uv run python checkpoint.py
```

输出的 `invalid_order_rejected=True` 必须和 `orders == before` 同时成立。只捕获断言但保留非法记录不能叫拒绝。现在读一笔订单需要关联两个描述；下一版为频繁查询保存可维护的结果副本。
