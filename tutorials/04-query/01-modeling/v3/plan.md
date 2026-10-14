# Q01 v3 计划：区分可刷新的副本与不可变历史事实

前置：同模块 v2 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：区分可刷新的副本与不可变历史事实。
- Naive：v2 只展示维护副本，容易把订单价格也误当最新产品价格同步。
- Break：products 改名后旧 view 仍为 Widget；新 order 11 保存 price=13，旧 order 10 保持 12。
- Change：明确 read-model 字段的维护责任与订单历史价格边界，并列出逻辑操作预算。
- Check：normalized_read_ops=2,denormalized_read_ops=1,extra_write_ops=1,stale_read_model=True,snapshot_price=12。
- Freeze：`tutorials/04-query/01-modeling/v3/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：view_writes=1 是声明的维护预算，正文未执行更新；不是实际写入或性能基准。
- Next：Q02 用真实数据库测量索引访问；Q04 深入派生数据维护。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/04-query/01-modeling/v3/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/query/modeling/replay_q01.py`。它执行全部版本，不能替代上面的单版本检查。
