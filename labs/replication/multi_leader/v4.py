from __future__ import annotations

import json

from v0 import Network, SingleLeader
from v2 import MultiLeader


def experiment(topology: str, partitioned: bool, one_way_ms: int = 40) -> dict[str, object]:
    if topology not in {"single", "multi"}:
        raise ValueError("unknown topology")
    network = Network(one_way_ms)
    store = SingleLeader(network) if topology == "single" else MultiLeader(network)
    network.connected = not partitioned
    requests = [store.write("A", "A-profile")]
    # Same caller pacing for both topologies; connected B observes A first.
    network.run_until(network.now_ms + one_way_ms, lambda: False)
    requests.append(store.write("B", "B-profile"))
    successes = [request for request in requests if request.acknowledged_ms is not None and request.acknowledged_ms <= request.finished_ms]
    successful_delays = [request.latency_ms for request in successes]
    failures = [request.latency_ms for request in requests if request not in successes]
    # These writes are known to be causally isolated only in this partition schedule.
    conflicting_values = {request.value for request in successes} if partitioned and topology == "multi" else set()
    network.connected = True
    if isinstance(store, SingleLeader):
        store.replicate()
    else:
        store.synchronize()
    network.run_until(network.now_ms + 3 * one_way_ms + 2, lambda: False)
    if isinstance(store, SingleLeader):
        converged = store.values["A"] == store.values["B"]
        winner = store.values["A"][1]
    else:
        converged = store.values["A"] == store.values["B"]
        assert store.values["A"] is not None
        winner = store.values["A"].value
    assert converged
    return {
        "topology": topology, "partitioned": partitioned,
        "attempted": len(requests), "acknowledged": len(successes),
        "success_latency_ms": successful_delays, "timeout_latency_ms": failures,
        "mean_success_ms": sum(successful_delays) / len(successful_delays) if successes else None,
        "concurrent_candidates": len(conflicting_values),
        "discarded_conflict_values": sorted(conflicting_values - {winner}),
        "converged": converged, "winner": winner,
    }


if __name__ == "__main__":
    print(json.dumps([experiment(topology, partitioned) for partitioned in (False, True) for topology in ("single", "multi")], indent=2))
