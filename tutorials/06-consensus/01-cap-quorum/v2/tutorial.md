# C01 v2: choose a partition policy

A store that requires linearizable reads can reject during a partition. A store that serves an old replica value remains available but gives up the linearizable read contract.

将下面的完整代码保存为 `labs/consensus/cap_quorum/v2.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/consensus/cap_quorum/v2.py -->

```python
from __future__ import annotations

from enum import Enum


class Policy(Enum):
    REJECT_ON_PARTITION = "reject_on_partition"
    SERVE_OLD_READ = "serve_old_read"


class PartitionedStore:
    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        self.partitioned = False
        self.value = "old"

    def write(self, value: str) -> str:
        if self.partitioned:
            return "unavailable"
        self.value = value
        return "committed"

    def read(self) -> str:
        if self.partitioned and self.policy is Policy.REJECT_ON_PARTITION:
            return "unavailable"
        return self.value


if __name__ == "__main__":
    store = PartitionedStore(Policy.REJECT_ON_PARTITION)
    store.partitioned = True
    print(store.read())
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/consensus/cap_quorum/v2.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
