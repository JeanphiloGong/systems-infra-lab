# T04 v0：执行两条串行轨迹，建立参考

两位医生都在岗，每人各请求下班一次。规则是先读在岗人数，只有大于一人时才允许当前医生离开。若直接把两个请求都批准，就会无人值班；现在先按串行顺序运行请求，作为之后并发调度的参照。

## 1. 每次请求都重新判断

按 1→2 执行时，第一位读取两人并离开，第二位重新读到一人而拒绝。反向执行则得到相反结果。`run_serial` 每次建立同样初始状态，按输入顺序调用同一条判断规则；不是预先填一份结果集合。

## 2. 保存并执行完整检查点

新建 `labs/transactions/serializable/serial_reference.py`：

<!-- checkpoint: labs/transactions/serializable/serial_reference.py -->

```python
from itertools import permutations


def run_serial(order):
    on_call = {1: True, 2: True}
    for doctor in order:
        if sum(on_call.values()) > 1:
            on_call[doctor] = False
    return tuple(on_call[doctor] for doctor in (1, 2))


if __name__ == "__main__":
    results = {order: run_serial(order) for order in permutations((1, 2))}
    assert results[(1, 2)] == (False, True)
    assert results[(2, 1)] == (True, False)
    assert all(sum(state) == 1 for state in results.values())
    print(results)
```

```bash
uv run python -m labs.transactions.serializable.serial_reference
```

应得到 `(1,2): (False,True)` 与 `(2,1): (True,False)`。断言同时核对每条轨迹的结果与最后一人值班；把 `> 1` 改为 `> 0` 会产生无人值班并失败。

此处只实现串行工作负载，无需 PostgreSQL。若并发请求都先读到两人、再更新自己的行，可能得到 `(False,False)`；下一版用真实 SERIALIZABLE 观察这种历史被中止。最终状态匹配只是这个小例子的必要检查，不能单独证明任意事务历史可串行化。
