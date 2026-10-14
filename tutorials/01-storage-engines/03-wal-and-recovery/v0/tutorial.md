# S03 v0：进程退出后，转账只完成了一半

支付服务把 Alice 的 10 元转给 Bob。Alice 与 Bob 各有 100 元，成功后应为 90 和 110，总额仍为 200。先别讨论数据库，假设我们只把账户字典写进一个 JSON 文件。

我们将实际系统压缩为固定账户、固定金额和单个写者。输入文件由实验生成，不处理负余额、用户认证或并发请求。本篇故意实现不安全版本，让一个确定的退出位置揭示问题。它不是推荐的持久化实现。

## 1. 写两次不等于一个事务

直觉上的程序是：读取账户，扣 Alice 10 元，保存；给 Bob 加 10 元，再保存。正常执行没有问题。但如果第一次保存后进程突然退出，文件已经记录扣款，第二次保存永远不会发生。

我们关心的不变量不是“每次 JSON 都能读”，而是一次转账全部完成或者全部不完成。把两次 `write_text` 放在同一个函数里，不会让文件系统自动理解这个业务边界。

## 2. 在确定边界退出

新建 `labs/storage/wal/baseline.py`，以下是完整检查点。`--crash` 只供本实验子进程使用：第一次保存返回后执行 `os._exit(73)`，不运行 Python 的异常清理。73 是我们约定的故障退出码，便于与模块导入失败等非预期错误区分。

`Path.write_text` 在返回前关闭文件，因此这次进程退出后，其他进程通常已经能看到第一份 JSON；它没有调用 fsync，不承诺断电后仍存在。直接覆盖本身也可能在更早退出时留下截断文件，本篇只选择第一次完整覆盖之后的边界。

<!-- checkpoint: labs/storage/wal/baseline.py -->
```python
"""Deliberately unsafe two-step transfer, retained as a failure experiment."""

import argparse
import json
import os
from pathlib import Path


def transfer(path: Path, crash: bool = False) -> None:
    balances = json.loads(path.read_text())
    balances["alice"] -= 10
    path.write_text(json.dumps(balances))
    if crash:
        os._exit(73)
    balances["bob"] += 10
    path.write_text(json.dumps(balances))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--crash", action="store_true")
    args = parser.parse_args()
    transfer(args.path, args.crash)


if __name__ == "__main__":
    main()
```

从仓库根目录运行下面的检查，所有文件在临时目录中，终止的只是实验创建的子进程：

```bash
uv run python - <<'PY'
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    path = Path(directory) / "balances.json"
    initial = {"alice": 100, "bob": 100}
    path.write_text(json.dumps(initial))
    subprocess.run([sys.executable, "-m", "labs.storage.wal.baseline", str(path)], check=True)
    assert json.loads(path.read_text()) == {"alice": 90, "bob": 110}
    path.write_text(json.dumps(initial))
    result = subprocess.run(
        [sys.executable, "-m", "labs.storage.wal.baseline", str(path), "--crash"],
        check=False,
    )
    assert result.returncode == 73
    broken = json.loads(path.read_text())
    assert broken == {"alice": 90, "bob": 100}
    assert sum(broken.values()) == 190
    print("after crash:", broken)
print("v0 reproduced partial update")
PY
```

预期输出 `after crash: {'alice': 90, 'bob': 100}` 和 `v0 reproduced partial update`。这是一个“实验通过，设计失败”的检查：我们准确复现了丢失 10 元，而不是修复了它。正常分支作为对照，保证故障确实来自退出位置。

现在文件里没有说明这次转账是否完成的信息。不能通过重跑原函数恢复，因为那会再次扣款。下一篇先解决更基础的问题：追加记录如何在半条写入后仍能识别完整前缀。之后再把操作和提交意图写入日志，定义恢复规则。
