# P02 v0-v3 rereview

Verdict: mostly repaired, but not accepted yet.

The tutorials now include complete `skew.py` fences for v0-v3 and a complete
`queues.py` fence in v3. The strict replay extracts those fences into a fresh
package, runs the routing module for every version, and executes the queue
module with assertions that its output contains p99 and capacity fields.

```text
uv run pytest tests/partitioning/skew -q
10 passed in 0.52s
uv run pytest tests/partitioning/skew/test_p02_replay.py -q
1 passed in 0.50s
```

One original-scope gap remains in the printed v3 checkpoint: its example only
asserts `report["total"] == 1000` for the salted workload and prints the
report. It does not assert or compare the required cases: unsalted hot-key
p99 remains high after adding partitions, salting reduces p99 and increases
capacity, and the shared dispatcher bottleneck reduces the capacity bound
again. Those comparisons exist only in repository tests against current
source. Add the semantic assertions to the printed v3 checkpoint and replay
them from the extracted fences before acceptance.

No reviewer implementation or tutorial edits were made.
