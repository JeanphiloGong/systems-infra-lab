# D02 v1 计划：租约过期不会停止旧持有者

前置：同模块 v0 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：租约过期不会停止旧持有者。
- Naive：v0 的互斥没有故障后释放机制；只按时间换 owner 会允许暂停旧 owner 恢复执行。
- Break：固定 now=2，a.expires=1；改授 b.expires=3，保留 old_owner_paused。
- Change：引入逻辑时钟租约和过期后重新授予的轨迹；这一步暴露风险，不声称修复重叠。
- Check：old_owner_paused=True,new_owner=b,overlap_risk=True。
- Freeze：`tutorials/07-coordination/02-distributed-lock/v1/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：没有实际旧写入、资源端 fencing 或可靠分布式时钟。
- Next：v2 在资源端拒绝过期持有者的写入 token。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/07-coordination/02-distributed-lock/v1/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/coordination/locks/replay_d02.py`。它执行全部版本，不能替代上面的单版本检查。
