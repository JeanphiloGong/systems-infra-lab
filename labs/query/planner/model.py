from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stats:
    rows: int
    distinct: int
    correlation: float = 0.0

    def selectivity(self, value_count: int = 1) -> float:
        return min(1.0, value_count / max(1, self.distinct))


def choose(stats: Stats, value_count: int = 1) -> tuple[str, float]:
    selectivity = stats.selectivity(value_count)
    seq_cost = float(stats.rows)
    index_cost = 2.0 + stats.rows * selectivity
    return ("index", index_cost) if index_cost < seq_cost else ("seq", seq_cost)


def estimate_join(left: Stats, right: Stats, correlated: bool = False) -> float:
    independent = left.rows * right.rows / max(left.distinct, right.distinct)
    return independent * (2.0 if correlated else 1.0)
