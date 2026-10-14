from __future__ import annotations

import json
from bisect import bisect_right
from pathlib import Path
import subprocess
import sys

from labs.storage.bplus_tree.page_file import PAGE_SIZE, load, save
from labs.storage.bplus_tree.tree import BPlusTree, Internal


def compare_accesses(keys: list[int], probes: list[int]) -> dict[str, int]:
    ordered = sorted(set(keys))
    array_pages = 0
    array_results = []
    for probe in probes:
        visited = set()
        low, high = 0, len(ordered)
        while low < high:
            middle = (low + high) // 2
            visited.add(middle // 15)
            if ordered[middle] < probe:
                low = middle + 1
            else:
                high = middle
        if low < len(ordered):
            visited.add(low // 15)
        array_results.append(low < len(ordered) and ordered[low] == probe)
        array_pages += len(visited)
    tree = BPlusTree[int](15, 20)
    for key in keys:
        tree.insert(key, key)
    tree_nodes = 0
    tree_results = []
    for probe in probes:
        node = tree.root
        while isinstance(node, Internal):
            tree_nodes += 1
            node = node.children[bisect_right(node.keys, probe)]
        tree_nodes += 1
        tree_results.append(any(key == probe for key, _ in node.items))
    assert array_results == tree_results
    return {
        "probes": len(probes),
        "array_page_reads": array_pages,
        "tree_page_reads": tree_nodes,
    }


def interrupted_save(path: Path) -> int:
    import signal

    tree = BPlusTree[int](3, 3)
    tree.insert(-1, -1)
    save(tree, path)
    child_code = """
import resource
import signal
import sys
from pathlib import Path
from labs.storage.bplus_tree.page_file import PAGE_SIZE, save
from labs.storage.bplus_tree.tree import BPlusTree

tree = BPlusTree[int](3, 3)
for key in range(40):
    tree.insert(key, key)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, (PAGE_SIZE, PAGE_SIZE))
signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
save(tree, Path(sys.argv[1]))
"""
    result = subprocess.run([sys.executable, "-c", child_code, str(path)], timeout=10)
    if result.returncode != -signal.SIGXFSZ:
        raise RuntimeError(f"save was not interrupted by file-size limit: {result.returncode}")
    assert path.stat().st_size == PAGE_SIZE
    try:
        load(path)
    except ValueError:
        return path.stat().st_size
    raise AssertionError("partial save was accepted")


def main() -> None:
    from tempfile import TemporaryDirectory

    report = compare_accesses(list(range(1000)), [17, 500, 999])
    with TemporaryDirectory() as directory:
        partial_bytes = interrupted_save(Path(directory) / "tree.pages")
    print(json.dumps({**report, "partial_bytes": partial_bytes}, sort_keys=True))


if __name__ == "__main__":
    main()
