# P01 v1：用哈希给订单选择节点

[v0](../v0/tutorial.md) 的一份字典已经能保存订单。现在准备了 a、b、c 三个节点，
每个节点各有一份字典。如果写入时随意选择节点，读取时就不得不问遍所有节点。
我们需要同一个 ID、同一份节点配置永远计算出同一个主要归属。

本篇只模拟路由，不启动三个数据库。分片实际可以是独立数据库；进程内三份字典
让我们先看清路由变化的后果。按 [环境说明](../../../../docs/environment.md) 安装依赖即可，无需数据库。

## 1. 先固定“哈希”到底是哪一种

Python 的 `hash("20")` 不适合作为持久路由格式：字符串哈希默认受进程种子影响。
即使同一个进程运行两次结果相同，也不能证明另一个进程会选同一个节点。
我们选 SHA256 的前 8 字节，按大端解释成整数；整数 ID 先变为十进制文本，再编码为 UTF-8。

下面是独立检查：

```python
from hashlib import sha256

value = int.from_bytes(sha256(b"abc").digest()[:8], "big")
assert value == int.from_bytes(bytes.fromhex("ba7816bf8f01cfea"), "big")
```

固定算法与编码使不同进程能够复算。这里不需要密码学安全性，但需要算法、字节顺序和键编码一致。
哈希碰撞让两个键落到相同位置并不意味着订单键相同；每个分片仍按完整 ID 存数据。

## 2. 将哈希值映射到有序节点列表

对三个节点取余得到 0、1、2。节点元组的顺序也是路由配置的一部分，
如果一台机器用 `(a,b,c)`，另一台用 `(b,a,c)`，它们会给同一订单不同归属。
空列表无法取模，重复节点会让容量权重失真，因此配置时直接拒绝。

新建 `labs/partitioning/routing/hashing.py`，完整 checkpoint 如下：

<!-- checkpoint: labs/partitioning/routing/hashing.py -->
```python
from hashlib import sha256


def stable_hash(text: str) -> int:
    return int.from_bytes(sha256(text.encode("utf-8")).digest()[:8], "big")


def modulo_node(order_id: int, nodes: tuple[str, ...]) -> str:
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError("nodes must be nonempty and unique")
    return nodes[stable_hash(str(order_id)) % len(nodes)]
```

`stable_hash` 首次被需要，是因为路由必须跨进程可复算；它不保存状态。
这个函数只选节点，不写数据。调用者在选出的节点执行 v0 的字典读写即可。

## 3. 扩容后先不要假定数据已经移动

从 3 个节点改成 4 个，取模除数发生变化。旧订单仍在旧节点，路由函数却可能给出新位置。
在仓库根目录运行完整实验：

```bash
uv run python - <<'PY'
from labs.partitioning.routing.hashing import modulo_node, stable_hash

old = ("a", "b", "c")
new = (*old, "d")
stores: dict[str, dict[int, str]] = {node: {} for node in new}
for key in range(1000):
    stores[modulo_node(key, old)][key] = "paid"
assert all(stores[modulo_node(key, old)][key] == "paid" for key in range(1000))
moved = [key for key in range(1000) if modulo_node(key, old) != modulo_node(key, new)]
assert moved
assert all(key not in stores[modulo_node(key, new)] for key in moved)
assert stable_hash("abc") == int.from_bytes(bytes.fromhex("ba7816bf8f01cfea"), "big")
for nodes in ((), ("a", "a")):
    try:
        modulo_node(0, nodes)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid configuration accepted")
print(f"moved={len(moved)}/1000; old routes still read all orders")
PY
```

移动数量由这里固定的 1000 个键和哈希函数决定；它不是每个业务的迁移比例保证。
在均匀哈希的直觉下，3→4 的简单取模会移动约四分之三键，而不只是新节点最终分到的四分之一。

现在点查无需广播，但按 ID 范围查找仍不能仅凭范围确定几个节点。
下一版尝试保留键顺序的范围分区；节点增减的迁移成本会在 v3 再处理。
