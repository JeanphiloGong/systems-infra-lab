# Q01 v0 计划：重复客户姓名发生更新异常

前置：模块总计划中的基础知识和 uv 环境。本文只规划当前 tutorial 的可执行行为。

- Pressure：重复客户姓名发生更新异常。
- Naive：两笔订单直接保存同一 customer=Ada；单独修改一笔使同一个事实自相矛盾。
- Break：只把 orders[0].customer 改成 A. Lovelace，orders[1] 仍为 Ada。
- Change：冻结重复存储的失败基线，不提前引入客户实体。
- Check：两行 customer 不等，输出 inconsistent_rows=2；这是演示值而非通用异常计数器。
- Freeze：`tutorials/04-query/01-modeling/v0/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：没有关系约束或历史价格语义，只展示一次更新异常。
- Next：v1 将 customer_id -> customer_name 存储一次，读取时 join。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/04-query/01-modeling/v0/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/query/modeling/replay_q01.py`。它执行全部版本，不能替代上面的单版本检查。
