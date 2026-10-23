# C03 v0：日志追加与状态机提交分开

客户端设置 mode=safe，节点收到了命令，但还没决定它是否生效。如果 append 直接改 state，未提交内容会暴露给调用者。先压缩成一个节点、一条有序日志和一个字典状态机，不引入网络或选举。

## 1. 日志追加与状态机提交分开

`log` 按追加顺序保存命令，`commit` 表示已应用的连续前缀长度；`state` 只由 `apply` 更新。重复 apply 同一位置不重复应用，越过日志末尾被拒绝。append 返回的位置从 1 开始，与 Python 列表下标相差 1。

下面是本版的完整 `model.py` checkpoint；替换上一版同名文件，不创建 advanced.py。

<!-- checkpoint: labs/consensus/raft/model.py -->

```python
class Node:
    def __init__(self, name):
        self.name = name
        self.log = []
        self.commit = 0
        self.state = {}

    @property
    def last(self):
        return len(self.log)

    def append(self, key, value):
        self.log.append(dict(key=key, value=value))
        return self.last

    def apply(self, index):
        if index <= self.commit:
            return
        if index > self.last:
            raise ValueError('commit exceeds log')
        for position in range(self.commit + 1, index + 1):
            entry = self.log[position - 1]
            self.state[entry['key']] = entry['value']
        self.commit = index
```

## 2. 运行本版检查并保留旧行为

替换 `labs/consensus/raft/experiments.py`。各检查使用单独临时目录，数据和故障互不污染。

<!-- checkpoint: labs/consensus/raft/experiments.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import subprocess
import sys

from .model import Node

def state_machine(directory):
    node = Node('single')
    node.append('mode', 'safe')
    assert node.state == {} and node.commit == 0
    node.apply(1)
    node.apply(1)
    assert node.state == {'mode': 'safe'} and node.commit == 1
    try:
        node.apply(2)
    except ValueError:
        pass
    else:
        raise AssertionError('committed beyond log')
    return dict(commit_index=node.commit, state=node.state)


def run_all():
    results = {}
    with TemporaryDirectory() as folder:
        case = Path(folder) / "state_machine"
        case.mkdir()
        results["state_machine"] = state_machine(case)
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), sort_keys=True))
```

```bash
uv run python -m labs.consensus.raft.experiments
```

追加后 state={}、commit=0；apply(1) 后 mode=safe，重复应用不变，apply(2) 拒绝。此检查点尚无持久化，下一版加入选举。
