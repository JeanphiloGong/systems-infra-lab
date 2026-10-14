# D02 v3 计划：旧持有者不能续租新持有者的锁

前置：同模块 v2 检查点。本文只规划当前 tutorial 的可执行行为。

- Pressure：旧持有者不能续租新持有者的锁。
- Naive：v2 保护资源写，但 lease 操作若只用锁名，旧客户端仍可能修改新租约。
- Break：a 在 t=0 获 token=1 到 t=1；b 在 t=2 获 token=2；a 续租失败，b 以 ttl=3 续租。
- Change：renew 同时检查 owner、token 和未过期条件。
- Check：stale_renew_rejected=True,current_owner=b,token=2,expires_at=5。
- Freeze：`tutorials/07-coordination/02-distributed-lock/v3/tutorial.md` 中唯一的 `checkpoint.py` 完整围栏及上述观测；输出成功后交独立审核，不自动提交。
- Still-lacks：正文标题含 release，但该 fence 没有 release 方法；本版仅证明 renew。真实时间与持久 token 未覆盖。
- Next：v4 处理无法联系锁服务时是否继续写的决策。

从仓库根目录仅提取并执行本版围栏，临时目录退出后自动清理：

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import subprocess
import sys

document = Path("tutorials/07-coordination/02-distributed-lock/v3/tutorial.md").read_text()
match = re.search(r"<!-- checkpoint: checkpoint.py -->\n```python\n(.*?)\n```", document, re.S)
assert match is not None
with TemporaryDirectory() as directory:
    target = Path(directory) / "checkpoint.py"
    target.write_text(match.group(1) + "\n")
    subprocess.run([sys.executable, str(target)], cwd=directory, check=True)
PY
```

模块全量复核命令：`uv run python tests/coordination/locks/replay_d02.py`。它执行全部版本，不能替代上面的单版本检查。
