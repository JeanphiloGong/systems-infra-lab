# Q01 v2 计划：免 join 的读模型会落后源数据

前置：同模块 v1 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：免 join 的读模型会落后源数据。
- Naive：v1 每次读取做关联；直接复制字段提升读取便利性但引入更新责任。
- Break：构造 view 后将 products[7] 改为 New Widget；view 仍是 Widget，随后显式更新。
- Change：引入一个由源数据维护的 read model，并展示一次维护写入。
- Check：read_joins=0,view_update_writes=1,stale_window=True；更新后 view product=New Widget。
- Freeze：`tutorials/04-query/01-modeling/v2/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：无并发失效、消费位置或自动 rebuild，计数是逻辑操作而非耗时。
- Next：v3 对照读取操作、维护写入和不可改写的历史价格。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/04-query/01-modeling/v2/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/query/modeling/replay_q01.py`。它执行全部版本，不能替代上面的单版本检查。
