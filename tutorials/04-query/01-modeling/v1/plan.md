# Q01 v1 计划：消除重复事实并保留订单价格

前置：同模块 v0 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：消除重复事实并保留订单价格。
- Naive：v0 每笔订单复制客户姓名；更新所有副本需要额外协调。
- Break：将 customers[1] 改成 A. Lovelace 后 join order 10，再尝试不存在的 customer 9。
- Change：拆分 customers/products，以 ID 关联订单；price=12 留在订单事实中。
- Check：join={customer:A. Lovelace,product:Widget,price:12},foreign_key_rejected=True。
- Freeze：`tutorials/04-query/01-modeling/v1/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：这是字典与 assert 模型，非法 orders[11] 仍已插入；不是数据库外键回滚。
- Next：v2 为频繁读取建立派生副本，观察维护成本。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/04-query/01-modeling/v1/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/query/modeling/replay_q01.py`。它执行全部版本，不能替代上面的单版本检查。
