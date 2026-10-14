from __future__ import annotations

from pathlib import Path
from struct import Struct
import zlib

from labs.storage.bplus_tree.tree import BPlusTree, Internal, Leaf

PAGE_SIZE = 256
META = Struct("<8s6I")
HEAD = Struct("<BII")
PAIR = Struct("<qq")
KEY = Struct("<q")
ID = Struct("<I")
MAGIC = b"BPLUS001"


def checked_page(body: bytes) -> bytes:
    if len(body) > PAGE_SIZE - ID.size:
        raise ValueError("page capacity exceeds encoded page size")
    padded = body.ljust(PAGE_SIZE - ID.size, b"\0")
    return padded + ID.pack(zlib.crc32(padded))


def save(tree: BPlusTree[int], path: Path) -> None:
    tree.validate()
    if HEAD.size + tree.leaf_capacity * PAIR.size > PAGE_SIZE - ID.size:
        raise ValueError("leaf capacity exceeds encoded page size")
    if HEAD.size + tree.internal_capacity * ID.size + (tree.internal_capacity - 1) * KEY.size > PAGE_SIZE - ID.size:
        raise ValueError("internal capacity exceeds encoded page size")
    nodes: list[Leaf[int] | Internal[int]] = [tree.root]
    for node in nodes:
        if isinstance(node, Internal):
            nodes.extend(node.children)
    ids = {id(node): index + 1 for index, node in enumerate(nodes)}
    pages = [checked_page(META.pack(
        MAGIC, 1, tree.leaf_capacity, tree.internal_capacity,
        ids[id(tree.root)], len(nodes), tree.height,
    ))]
    for node in nodes:
        if isinstance(node, Leaf):
            body = HEAD.pack(1, len(node.items), ids[id(node.next)] if node.next else 0)
            for key, value in node.items:
                if any(type(number) is not int or not -(2**63) <= number < 2**63 for number in (key, value)):
                    raise ValueError("page codec requires signed 64-bit integer keys and values")
                body += PAIR.pack(key, value)
        else:
            body = HEAD.pack(2, len(node.children), 0)
            body += b"".join(ID.pack(ids[id(child)]) for child in node.children)
            body += b"".join(KEY.pack(key) for key in node.keys)
        pages.append(checked_page(body))
    with path.open("wb") as target:
        for page in pages:
            target.write(page)


def load(path: Path) -> BPlusTree[int]:
    data = path.read_bytes()
    if not data or len(data) % PAGE_SIZE:
        raise ValueError("truncated page file")
    pages = [data[offset:offset + PAGE_SIZE] for offset in range(0, len(data), PAGE_SIZE)]
    for page in pages:
        if zlib.crc32(page[:-ID.size]) != ID.unpack_from(page, PAGE_SIZE - ID.size)[0]:
            raise ValueError("page checksum mismatch")
    magic, version, leaf_cap, internal_cap, root_id, count, height = META.unpack_from(pages[0])
    if magic != MAGIC or version != 1 or count != len(pages) - 1 or not 1 <= root_id <= count:
        raise ValueError("invalid root metadata")
    if not 2 <= leaf_cap <= 15 or not 3 <= internal_cap <= 20:
        raise ValueError("invalid encoded capacities")
    tree = BPlusTree[int](leaf_cap, internal_cap)
    nodes: dict[int, Leaf[int] | Internal[int]] = {}
    links: dict[int, list[int]] = {}
    next_ids: dict[int, int] = {}
    for page_id, page in enumerate(pages[1:], 1):
        kind, size, next_id = HEAD.unpack_from(page)
        if kind == 1 and size <= leaf_cap:
            items = [PAIR.unpack_from(page, HEAD.size + index * PAIR.size) for index in range(size)]
            nodes[page_id] = Leaf(items)
            next_ids[page_id] = next_id
        elif kind == 2 and 2 <= size <= internal_cap and next_id == 0:
            children = [ID.unpack_from(page, HEAD.size + index * ID.size)[0] for index in range(size)]
            keys = [KEY.unpack_from(page, HEAD.size + size * ID.size + index * KEY.size)[0] for index in range(size - 1)]
            nodes[page_id] = Internal(keys)
            links[page_id] = children
        else:
            raise ValueError("invalid page header")
    seen: set[int] = set()

    def connect(page_id: int) -> Leaf[int] | Internal[int]:
        if page_id not in nodes or page_id in seen:
            raise ValueError("invalid or repeated child page")
        seen.add(page_id)
        node = nodes[page_id]
        if isinstance(node, Internal):
            node.children = [connect(child) for child in links[page_id]]
        return node

    tree.root = connect(root_id)
    if len(seen) != count:
        raise ValueError("unreachable page")
    for page_id, next_id in next_ids.items():
        node = nodes[page_id]
        assert isinstance(node, Leaf)
        if next_id:
            next_node = nodes.get(next_id)
            if not isinstance(next_node, Leaf):
                raise ValueError("leaf link is not a leaf")
            node.next = next_node
    tree.height = height
    try:
        tree.validate()
    except (AssertionError, IndexError) as error:
        raise ValueError("invalid tree topology") from error
    return tree
