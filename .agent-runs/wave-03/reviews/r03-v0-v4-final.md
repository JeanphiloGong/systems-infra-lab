# R03 independent original-scope review

Verdict: PASS within the explicitly bounded simulation model against `docs/roadmap.md:362`. No blocking findings.

Read all v0-v4 source, tutorial prose and printed checks, replay implementation and original roadmap. Actually ran `uv run python -m pytest tests/replication/multi_leader -q`: **5 passed in 0.81s**. Each case extracts all printed dependencies and semantic checks, compares source fences byte-exact with implementation, and executes both entry point and checks in a temporary directory with isolated PYTHONPATH. Also directly ran `uv run python labs/replication/multi_leader/v4.py` and inspected its full report.

## Semantic evidence

- v0 uses a heap of timed request, commit, replication and acknowledgment callbacks. Request elapsed time is computed from event timestamps. Tests vary one-way delay 0/7/40 and observe remote 2/16/82 simulated ms. A 50ms timeout does not cancel a request that later commits at 82ms and acknowledges at 162ms. A request dropped during partition does not modify state.
- v1 preserves genuinely causally concurrent vectors (1,0)/(0,1) after partition repair. Merge computes the nondominated set, is duplicate-insensitive, and preserves both candidates. A subsequent user write observes both and generates (2,1), dominating both. Sequential simulator calls are correctly distinguished from causal observation.
- v2 orders unique valid versions by wall timestamp, region and sequence. The earlier real-event write at t=2 with timestamp1002 defeats the later write at t=4 with timestamp4. Reverse/duplicate delivery, ties and local loss under a slow clock are checked. Acknowledgment and retained-value guarantees are clearly distinguished.
- v3 uses componentwise maximum, not addition of received snapshots. All six orders of three snapshots plus duplicates/reverse delivery converge to components A3/B4 and sum7. Earlier snapshot remains unchanged after subsequent writes. Invalid received snapshots/increments are rejected before mutation. Latest-state delivery is explicitly necessary.
- v4 executes v0/v2 classes with the same workload and inter-request pacing, rather than assigning comparative latency constants. Connected B observes A before writing; partitioned B does not. Confirmed default results: single connected [2,82]ms, multi connected [2,2]ms; partitioned single 1/2 acknowledgments plus100ms timeout, partitioned multi2/2 but discards A-profile on convergence. Failed latencies are separate from successful means.

## Bounds

These are simulated event times, not real network benchmarks. Fixed A/B identities, valid unique versions, sequential writers, one scalar register, memory-only state, fixed delay and eventual explicit synchronization are assumed. No restart identity recovery, host durability, dynamic membership, throughput or tail-latency claim is established. G-Counter ownership is a trusted caller invariant, not authenticated access control. v4's conflict count is specific to its known isolated schedule and unique values, not a general detector. All these limits are made explicit in the tutorials.

Review artifact only; no implementation abstraction or source cleanup added.
