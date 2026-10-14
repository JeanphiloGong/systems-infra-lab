# C01 v3 counterexample author evidence

Added a deterministic pending write and two non-overlapping quorum reads.
N=3, R=W=2: deliver new to A; read A/B returns new; read B/C returns old;
deliver to B and acknowledge the write. No additional write can explain this
read inversion in a linearizable register. This is a scheduled history, not a
network benchmark or generic linearizability checker.

Before implementation the new behavior test failed with AttributeError for
concurrent_history. After implementation, exact tutorial fence parity and
extracted JSON checks plus behavior tests passed:

```text
uv run pytest tests/consensus/cap_quorum -q
10 passed in 0.22s
```

Updated v3 source, matching full tutorial fence, teaching derivation, plan,
behavior test and extraction assertions. No infrastructure started. Independent
review pending; no acceptance update or commit performed.
