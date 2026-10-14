from bisect import bisect_right


class RangeMap:
    def __init__(self, cuts: tuple[int, ...], nodes: tuple[str, ...]) -> None:
        if len(nodes) != len(cuts) + 1 or len(set(nodes)) != len(nodes):
            raise ValueError("one unique node is required per range")
        if any(left >= right for left, right in zip(cuts, cuts[1:])):
            raise ValueError("cuts must be strictly increasing")
        self.cuts = cuts
        self.nodes = nodes

    def node(self, order_id: int) -> str:
        return self.nodes[bisect_right(self.cuts, order_id)]

    def covering(self, start: int, stop: int) -> tuple[str, ...]:
        if start >= stop:
            return ()
        first = bisect_right(self.cuts, start)
        last = bisect_right(self.cuts, stop - 1)
        return self.nodes[first:last + 1]
