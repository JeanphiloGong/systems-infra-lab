# D02 v0 计划：两个竞争者同时获取锁

前置：模块总计划中的基础知识和 uv 环境。本文只规划当前 tutorial 的可执行行为。

- Pressure：两个竞争者同时获取锁。
- Naive：无原子领取时 a/b 都可能认为获锁；本版先建立原子竞争基线。
- Break：Barrier(2) 同时放行 a/b，用 acquire(False) 竞争同一 Lock。
- Change：只引入原子非阻塞 acquire；获胜者不释放，保证另一竞争者失败。
- Check：winner 属于 a/b，contenders=2，len(winners)=1；不能指定固定赢家。
- Freeze：`tutorials/07-coordination/02-distributed-lock/v0/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：进程内 threading.Lock，没有租约、网络或进程崩溃恢复。
- Next：v1 让锁过期，以暴露暂停旧持有者仍可能继续执行。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/07-coordination/02-distributed-lock/v0/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/coordination/locks/replay_d02.py`。它执行全部版本，不能替代上面的单版本检查。
