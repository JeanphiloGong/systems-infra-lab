# C01 v3: quorum intersection is not linearizability

上一版在分区时选择拒绝请求或返回旧值。现在三个副本使用 N=3、R=W=2：
写入收到两个确认才成功，读取收到两个响应就返回其中版本最大的值。
所有大小为二的读写集合都相交，但这是否足以保证一个线性一致寄存器？

先保留 `has_intersection` 的组合枚举，再让 `quorum_read` 的 `nodes` 参数表示
本次选中的响应副本。它只在这些响应中取最大版本；不暗中读取第三个节点，也不
将读到的新值写回。版本 0 表示初始 old，版本 1 表示唯一的新写入。

## 一次未完成写入与两次顺序读取

固定投递顺序，避免依赖线程抢占或随机延迟：

1. 写 new 被调用，仅 A 收到 `(1,new)`，还没有达到 W=2。
2. read1 查询 A/B，读到 new 并返回。
3. read1 返回之后才调用 read2；read2 查询 B/C，两者仍为 old，返回 old。
4. B 收到写入，写入收到第二个确认并成功返回。

这不是“不相交”造成的：A/B 与 B/C 相交于 B，完成写入的确认集合 A/B
也与每次读取相交。问题是交集节点在读取时还没有收到未完成写入。

若历史可线性化，read1 返回 new 要求唯一的写 new 排在 read1 前面。
read1 完成早于 read2 开始，强制 read1 排在 read2 前面。因此 write < read1 < read2；
没有其他写入时 read2 必须也返回 new。实际返回 old，产生矛盾。
写与读重叠允许选择写入的线性化位置，却不能同时满足这两个读取结果。

下面增加一个直接修改副本字典的确定性调度。它是消息交错的反例，不是实际网络
或通用线性一致性检查器；返回值来自两次真实 `quorum_read` 调用。

将下面的完整代码保存为 `labs/consensus/cap_quorum/v3.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/consensus/cap_quorum/v3.py -->

```python
from __future__ import annotations

import json
from itertools import combinations


def has_intersection(nodes: set[str], read_size: int, write_size: int) -> bool:
    if not 1 <= read_size <= len(nodes) or not 1 <= write_size <= len(nodes):
        raise ValueError("quorum sizes must fit the node set")
    reads = list(combinations(nodes, read_size))
    writes = list(combinations(nodes, write_size))
    return all(set(read) & set(write) for read in reads for write in writes)


def quorum_read(nodes: set[str], replicas: dict[str, tuple[int, str]], size: int) -> tuple[int, str] | None:
    if size < 1 or size > len(nodes):
        raise ValueError("invalid read quorum")
    observed = sorted((replicas[node] for node in nodes if node in replicas), reverse=True)
    if len(observed) < size:
        return None
    return observed[0]


def concurrent_history() -> dict[str, object]:
    nodes = {"a", "b", "c"}
    replicas = {node: (0, "old") for node in nodes}
    trace = ["invoke write(new)"]
    replicas["a"] = (1, "new")
    acknowledgements = {"a"}
    trace.append("deliver write to a")
    trace.append("invoke read1(a,b)")
    first = quorum_read({"a", "b"}, replicas, 2)
    assert first is not None
    trace.append(f"return read1({first[1]})")
    trace.append("invoke read2(b,c)")
    second = quorum_read({"b", "c"}, replicas, 2)
    assert second is not None
    trace.append(f"return read2({second[1]})")
    replicas["b"] = (1, "new")
    acknowledgements.add("b")
    trace.append("deliver write to b")
    assert len(acknowledgements) >= 2
    trace.append("return write(success)")
    return {
        "intersection": has_intersection(nodes, 2, 2),
        "read_quorums": [["a", "b"], ["b", "c"]],
        "reads": [first, second],
        "write_acks": len(acknowledgements),
        "trace": trace,
    }


if __name__ == "__main__":
    print(json.dumps(concurrent_history(), sort_keys=True))
```

## 重放与边界

从仓库根目录运行：

```bash
uv run python -m labs.consensus.cap_quorum.v3
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run pytest tests/consensus/cap_quorum -q
```

</details>

输出的 `intersection` 为 true、`reads` 为 `[[1,"new"],[0,"old"]]`，
最终 `write_acks` 为 2。`trace` 显示 read1 返回先于 read2 调用，写成功在两次读之后。
提取参考分支的历史测试还会从本章围栏启动独立脚本并核对这些观察，不仅检查退出码。

冻结的是相交性质和一条违反线性一致的历史，不是修复后的复制协议。这里没有
读写回、提交可见性或领导者日志。单写者原子寄存器可以采用带版本的 quorum
读写回协议，但不能因此宣称任意加入读修复都正确。下一专题 C02 研究领导权限，
C03 再引入复制日志和提交规则；集合大小只是这些协议的一部分。

