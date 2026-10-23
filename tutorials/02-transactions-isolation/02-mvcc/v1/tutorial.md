# T02 v1：只保存当前值，无法回答旧快照

[v0](../v0/tutorial.md) 中，写者提交 false 后，旧读者仍读到 true。现在用一个十几行的教学模型解释这种能力。这个模型不是 PostgreSQL 源码，也不参与真实数据库测试；它只保存单个医生的已提交历史。

## 1. 覆盖旧值会丢失什么？

下面是可直接运行的 Python checkpoint：

```python
on_call = True
old_snapshot = 1
on_call = False
assert on_call is False
print(on_call)
```

即使变量还记着 old_snapshot=1，也无法从被覆盖的 bool 还原 true。缺口不在于给读取加一个参数，而在于旧值已经丢失。我们需要保留版本，并定义快照能选哪些版本。

## 2. 让快照选择一个已提交版本

将当前脚本替换为下面 checkpoint：

```python
versions = [(1, True), (2, False)]
snapshot = 1
result = next(value for committed_at, value in reversed(versions) if committed_at <= snapshot)
assert result is True
print(result)
```

这里的时间是我们自定义的严格递增提交序号，不是 PostgreSQL transaction ID。倒序扫描遇到第一个不晚于快照的版本，就得到该快照可见的最新值。把 snapshot 改成 2 得到 false，与 v0 的新旧读者观察一致。

如果快照为 0，脚本会抛 StopIteration。含义是对象尚不存在，我们希望调用者收到表达这一含义的 LookupError；这要求把查找过程写成一个小函数，而不是引入事务管理框架。

## 3. 保存完整模型并与数据库对照

新建 `labs/transactions/mvcc/model.py`，下面是完整 checkpoint。输入版本列表由本实验按提交顺序追加，函数信任这个内部契约，不排序或修改列表；如果将来接受外部输入，需要在那个入口验证顺序。

<!-- checkpoint: labs/transactions/mvcc/model.py -->

```python
def visible(versions: list[tuple[int, bool]], snapshot: int) -> bool:
    """Read an append-ordered committed-version list at a logical timestamp."""
    for committed_at, value in reversed(versions):
        if committed_at <= snapshot:
            return value
    raise LookupError("no visible version")


def main() -> None:
    versions = [(1, True)]
    old_snapshot = 1
    versions.append((2, False))
    print(visible(versions, old_snapshot), visible(versions, 2))


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.mvcc.model
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/mvcc/test_t02_model.py -q
```

</details>

```bash
uv run python -m labs.transactions.mvcc.snapshots --early-read
```

模型输出 `True False`，真实库输出 `(True, True, False)`。对应关系是旧快照在提交前后仍读 true，新快照读 false。测试还检查空列表、创建前快照和晚于最新版本的读取。

真实 PostgreSQL 必须处理进行中事务、自己的写入、删除、事务 ID、并发冲突及版本回收，不能简单按这个整数阈值完整描述。我们冻结的是“保留历史版本以服务旧读取”的最小模型。下一版回到真实数据库，观察两个事务各自使用正确快照，却共同做出错误业务决定。
