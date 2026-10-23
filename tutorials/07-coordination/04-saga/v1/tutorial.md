# D04 v1：持久化步骤进度并从重启继续

SQLite 记录每个订单步骤状态。进程重启后已完成步骤不重复执行，未完成步骤可以继续。

在 v0 的扣款完成后重启，协调者若只从函数开头重跑，就无法区分库存是否已预留。本版用 `(order_id, name)` 唯一标识一个步骤，把状态从内存移到 SQLite。它不是迁移 v0 的服务数据，而是增加协调者自己的执行记录。

读 `run` 时按三段看：先查询是否已为 `done`；否则提交 `running`，调用外部 `effect`；最后提交 `done`。第一次提交让异常留下可见的未完成记录，第二次提交让后续调用跳过已完成步骤。`status` 只是查询轨迹，不负责自动调度后续步骤。

## 1. 保存已完成步骤

下面保持 `run` 的三个阶段。入口增加两种明确角色：父进程只执行 reserve 并关闭数据库，子进程从同一文件恢复再执行剩余 charge。用新解释器排除内存对象仍存在的干扰；本版不在 effect 与 done 之间注入故障。

将下面的完整代码保存为 `labs/coordination/saga/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/coordination/saga/v1.py -->

```python
from __future__ import annotations

import sqlite3


class Saga:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS steps (order_id TEXT, name TEXT, state TEXT, PRIMARY KEY(order_id,name))")
        self.db.commit()

    def completed(self, order: str, name: str) -> bool:
        return self.db.execute("SELECT state='done' FROM steps WHERE order_id=? AND name=?", (order, name)).fetchone() == (1,)

    def run(self, order: str, name: str, effect) -> None:
        if self.completed(order, name):
            return
        self.db.execute("INSERT OR REPLACE INTO steps VALUES (?, ?, 'running')", (order, name))
        self.db.commit()
        effect()
        self.db.execute("UPDATE steps SET state='done' WHERE order_id=? AND name=?", (order, name))
        self.db.commit()

    def status(self, order: str) -> list[tuple[str, str]]:
        return self.db.execute("SELECT name,state FROM steps WHERE order_id=? ORDER BY rowid", (order,)).fetchall()


if __name__ == "__main__":
    import json
    from pathlib import Path
    import subprocess
    import sys
    from tempfile import TemporaryDirectory

    if len(sys.argv) == 2:
        saga = Saga(sys.argv[1])
        try:
            calls: list[str] = []
            saga.run("order-1", "reserve", lambda: calls.append("duplicate"))
            saga.run("order-1", "charge", lambda: calls.append("charge"))
            assert calls == ["charge"]
            assert saga.status("order-1") == [("reserve", "done"), ("charge", "done")]
            print(json.dumps({"resumed_calls": calls, "status": saga.status("order-1")}))
        finally:
            saga.db.close()
    else:
        with TemporaryDirectory() as folder:
            database = str(Path(folder) / "saga.sqlite")
            saga = Saga(database)
            try:
                calls: list[str] = []
                saga.run("order-1", "reserve", lambda: calls.append("reserve"))
                assert calls == ["reserve"]
            finally:
                saga.db.close()
            subprocess.run([sys.executable, __file__, database], check=True, timeout=10)
```

## 运行

```bash
uv run python labs/coordination/saga/v1.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/coordination/saga -q
```

</details>

直接运行会先在文件数据库完成 reserve、关闭连接，再启动一个全新 Python 进程。子进程重新调用 reserve 和 charge，但只允许 `resumed_calls=["charge"]`，两条状态均为 done。若删掉 done 的读取或换成 `:memory:`，子进程断言会失败。临时目录在子进程结束后清理。

必须区分“done 后重启”和“effect 成功、done 提交前崩溃”：后一种会留下 `running`，重试仍可能重复效果。外部服务需要自己的幂等键，本版不保证 exactly-once。它也没有修复配送失败留下的库存和扣款，下一版为这些已完成效果加入补偿。

