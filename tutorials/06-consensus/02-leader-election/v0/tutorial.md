# C02 v0：超时为什么会产生三个 leader

三个工作节点争用同一个写入口，六秒都没有收到心跳。最直接的做法是各自接管，但沉默只能说明没收到消息，不能证明别人停止工作。本版先实现这个错误：每个节点只有名字、最近心跳和 leader 判断，不提前引入任期、投票或租约。

## 1. 超时为什么会产生三个 leader

`timed_out` 只比较逻辑时钟；实验没有真实网络，不用 sleep 就能稳定得到反例。循环让三个节点同时自封，输出不是人为指定的结论，而是读取三个节点的 leader 字段。

将 `labs/consensus/leader_election/model.py` 替换为本版完整 checkpoint：

<!-- checkpoint: labs/consensus/leader_election/model.py -->

```python
class Node:
    def __init__(self, name, now=0):
        self.name = name
        self.last_heartbeat = now
        self.leader = False

    def timed_out(self, now, timeout=5):
        return now - self.last_heartbeat >= timeout


class Election:
    def __init__(self):
        self.nodes = {name: Node(name) for name in ("a", "b", "c")}
        self.now = 0
```

## 2. 用实际状态检验结果

保存下面的完整 `experiments.py`。每版保留已引入的检查，不使用 version 参数切换未来功能。

<!-- checkpoint: labs/consensus/leader_election/experiments.py -->

```python
from labs.consensus.leader_election.model import Election

cluster = Election()
cluster.now = 6
for node in cluster.nodes.values():
    if node.timed_out(cluster.now):
        node.leader = True
beliefs = [node.name for node in cluster.nodes.values() if node.leader]
assert beliefs == ["a", "b", "c"]
print({"timeout_self_elected": beliefs, "split_brain": len(beliefs) > 1})
```

从仓库根目录运行：

```bash
uv run python -m labs.consensus.leader_election.experiments
```

应输出 a/b/c 三个名字以及 split_brain=True。此处断言通过意味着成功复现错误，不能拿来服务真实写入。下一版将用投票替换“超时即授权”。
