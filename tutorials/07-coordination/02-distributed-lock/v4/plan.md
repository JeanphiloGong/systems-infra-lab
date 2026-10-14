# D02 v4 计划：联系不上锁服务时不能假定仍有写权限

前置：同模块 v3 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：联系不上锁服务时不能假定仍有写权限。
- Naive：v3 的 ownership 检查要求能查询服务；超时不是当前 lease 有效的证据。
- Break：service_available=False 固定触发 TimeoutError，资源初值 token=2,value=new。
- Change：把不确定结果显式转成 do not write，保留资源值。
- Check：availability=unknown,safety_action=do not write,resource={token:2,value:new}。
- Freeze：`tutorials/07-coordination/02-distributed-lock/v4/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：只是决策模型，没有真实网络检测、重试或端到端 fencing 协议。
- Next：后续分布式提交研究未知决策时为何必须阻塞。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/07-coordination/02-distributed-lock/v4/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/coordination/locks/replay_d02.py`。它执行全部版本，不能替代上面的单版本检查。
