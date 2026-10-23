# T03 v4：锁升级改变阻塞范围

前置v3。大量行锁需要大量锁记录；能否用一条表锁代表同一个事务的全部行锁？这就是本版要比较的机制。下面是独立的单线程教学模型，不连接PostgreSQL。PostgreSQL不会做SQL Server式的自动行锁升级。

## 1. 从行锁集合开始

模型只支持一张表的排他锁，不含意向锁、共享锁、等待队列、公平性或数据库完整死锁检测。acquire(owner,row)成功返回True，冲突返回False；它不阻塞线程。rows记录行到拥有者映射。同一拥有者重复获取允许成功。

## 2. 合并记录需要先检查竞争者

A持有三行，B仍可获取无关行99。A不能在B持有该行时升级，否则会越过现有锁；escalate必须先检查所有行锁都属于A，再设table_owner并清空行表。失败时状态完全不变，空锁集合也拒绝升级。release删除指定拥有者记录。

释放B以后，A从三条行锁升级为一条表锁记录。这次B连原本无关的99也无法获取；A释放后B才再次成功。记录数量3→1说明元数据规模变化，不能将它直接当真实字节内存测量。代价是阻塞范围扩大。

## 3. 完整检查点与验证

本版不需要数据库，只需要uv Python环境。下面完整新建 `labs/transactions/locking/escalation.py`，代码包含上述机制及完整调用入口。

<!-- checkpoint: labs/transactions/locking/escalation.py -->

```python
from __future__ import annotations


class LockModel:
    """Single-threaded teaching model: exclusive locks on one table only."""

    def __init__(self) -> None:
        self.rows: dict[int, str] = {}
        self.table_owner: str | None = None

    def acquire(self, owner: str, row: int) -> bool:
        if self.table_owner is not None:
            return self.table_owner == owner
        if row in self.rows and self.rows[row] != owner:
            return False
        self.rows[row] = owner
        return True

    def escalate(self, owner: str) -> bool:
        if self.table_owner is not None:
            return self.table_owner == owner
        if not self.rows or any(holder != owner for holder in self.rows.values()):
            return False
        self.table_owner = owner
        self.rows.clear()
        return True

    def release(self, owner: str) -> None:
        if self.table_owner == owner:
            self.table_owner = None
        self.rows = {row: holder for row, holder in self.rows.items() if holder != owner}


def main() -> None:
    model = LockModel()
    for row in range(3):
        assert model.acquire("A", row)
    before = len(model.rows)
    assert model.acquire("B", 99)
    assert not model.escalate("A")
    model.release("B")
    assert model.escalate("A")
    after = len(model.rows) + int(model.table_owner is not None)
    assert not model.acquire("B", 99)
    model.release("A")
    assert model.acquire("B", 99)
    print(f"records_before={before} records_after={after} unrelated_row_blocked=True")


if __name__ == "__main__":
    main()
```

```bash
uv run python -m labs.transactions.locking.escalation
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/transactions/locking/test_t03_escalation.py -q
```

</details>

输出records_before=3 records_after=1 unrelated_row_blocked=True。参考分支的历史测试同时检查升级失败不丢原锁、拥有者可重入、释放恢复访问和空集合边界。冻结T03，后续T04研究完整可串行化与事务重试。
