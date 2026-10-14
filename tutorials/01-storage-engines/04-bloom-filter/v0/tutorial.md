# S04 v0：不存在的键也会把每个文件读一遍

查询商品编号 missing，三个只读文件都没有它，服务却依次打开了三次文件。先别加入概率结构：我们需要一个结果正确、成本可见的基线，之后才能证明过滤器没有改变答案。

本篇把文件简化成 UTF-8 TSV，每行一对键值，用制表符分隔；键和值不含换行，键不含制表符。文件在实验期间不可变。多个文件出现相同键时以路径列表中最先找到的值为准，本文不模拟版本号或删除标记。

## 1. 先记录负查询发生的代价

query_files 接收路径列表和键，返回 (值或 None, 已读取文件数)。对一个文件调用一次 read_text 就把 reads 加一；空文件也算一次。扫描每一行，找到后立即返回。这个计数是应用发出的全文件读取，不是磁盘实际 I/O，因为 OS 可能缓存文件。

新建 labs/storage/bloom/baseline.py，以下是完整检查点：

<!-- checkpoint: labs/storage/bloom/baseline.py -->
```python
from pathlib import Path


def query_files(paths: list[Path], key: str) -> tuple[str | None, int]:
    reads = 0
    for path in paths:
        reads += 1
        for line in path.read_text().splitlines():
            stored_key, value = line.split("\t", 1)
            if stored_key == key:
                return value, reads
    return None, reads
```

## 2. 用同一批文件比较命中和缺失

三个文件各有一个不同键。查询首个文件的键读取一次，最后一个文件的键读取三次，缺失键也读取三次。只检查查询值看不出这种成本差异，因此检查必须同时断言 reads。

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from labs.storage.bloom.baseline import query_files

with TemporaryDirectory() as directory:
    paths = [Path(directory) / f"t{i}.tsv" for i in range(3)]
    for index, path in enumerate(paths):
        path.write_text(f"key-{index}\tvalue-{index}\n")
    assert query_files(paths, "key-0") == ("value-0", 1)
    assert query_files(paths, "key-2") == ("value-2", 3)
    assert query_files(paths, "missing") == (None, 3)
    assert query_files([], "missing") == (None, 0)
    paths[0].write_text("")
    assert query_files(paths[:1], "missing") == (None, 1)
print("v0: first=1 last=3 absent=3 empty-list=0 empty-file=1")
PY
```

预期打印这些计数。格式损坏和文件不存在会抛原始异常，本篇不把 I/O 故障当成查无此键。

现在得到负查询的参考结果。下一篇的目标不是缓存值，而是在读文件前用少量位回答“这个键肯定不在这里吗”。若只能回答“可能在”，仍必须读取真实数据。

