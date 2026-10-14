# D02 v2 计划：锁服务换主后资源仍可能接收旧写

前置：同模块 v1 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：锁服务换主后资源仍可能接收旧写。
- Naive：v1 只换 lease owner；旧客户端可能延迟发送写入，覆盖新值。
- Break：先用 new_token=2 写 value=new，再用 old_token=1 尝试写 old。
- Change：资源记住最高 fencing token，在资源写入点拒绝更小 token。
- Check：ValueError 被捕获，value 仍为 new；输出 stale_rejected=True,token=2。
- Freeze：`tutorials/07-coordination/02-distributed-lock/v2/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：资源状态和 token 都在内存，未证明持久单调 token 或外部存储原子校验。
- Next：v3 检查续租请求也必须属于当前 owner/token。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/07-coordination/02-distributed-lock/v2/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/coordination/locks/replay_d02.py`。它执行全部版本，不能替代上面的单版本检查。
