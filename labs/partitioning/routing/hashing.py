from hashlib import sha256


def stable_hash(text: str) -> int:
    return int.from_bytes(sha256(text.encode("utf-8")).digest()[:8], "big")


def modulo_node(order_id: int, nodes: tuple[str, ...]) -> str:
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError("nodes must be nonempty and unique")
    return nodes[stable_hash(str(order_id)) % len(nodes)]
