# Q01 v0：重复的客户事实只更新了一半

客服要把 Ada 的姓名改成 A. Lovelace。同一个客户有两笔订单，每行都复制姓名。先改其中一行：页面立即给同一个人显示两个名字。模型只有两个订单与一个姓名，不涉及数据库性能或事务。

## 1. 让矛盾可以观察

新建仓库根目录的 `checkpoint.py`。下面是本版完整文件；不提前引入客户表或维护函数。

<!-- checkpoint: checkpoint.py -->

```python
orders = [
    {"id": 1, "customer_id": 9, "customer": "Ada", "product": "Widget"},
    {"id": 2, "customer_id": 9, "customer": "Ada", "product": "Widget"},
]
orders[0]["customer"] = "A. Lovelace"
names = {order["customer"] for order in orders if order["customer_id"] == 9}
assert names == {"Ada", "A. Lovelace"}
print({"customer_id": 9, "names": sorted(names), "contradiction": len(names) > 1})
```

## 运行与检查

```bash
uv run python checkpoint.py
```

两个名称来自实际记录集合。下一版把“客户 9 的当前姓名”保存到唯一位置；订单保留客户 ID，而购买价格仍属于历史订单。
