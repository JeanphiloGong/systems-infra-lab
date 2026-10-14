import json
from bisect import bisect_left

from labs.partitioning.routing.hashing import stable_hash


class HashRing:
    def __init__(self, nodes: tuple[str, ...], virtual_nodes: int = 64) -> None:
        if not nodes or len(set(nodes)) != len(nodes) or virtual_nodes < 1:
            raise ValueError("unique nodes and positive virtual_nodes required")
        entries = sorted(
            (stable_hash(json.dumps([node, index], separators=(",", ":"))), node)
            for node in nodes
            for index in range(virtual_nodes)
        )
        self.points = tuple(point for point, _ in entries)
        self.owners = tuple(node for _, node in entries)
        if len(set(self.points)) != len(self.points):
            raise ValueError("ring point collision; change node configuration")

    def owner_at(self, position: int) -> str:
        index = bisect_left(self.points, position) % len(self.points)
        return self.owners[index]

    def node(self, order_id: int) -> str:
        return self.owner_at(stable_hash(str(order_id)))
