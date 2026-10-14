# P02 v0-v3 independent review

Verdict: not accepted yet.

The current `labs/partitioning/skew` implementation has useful deterministic
routing, request-vs-distinct-key counts, salted counter totals, and a discrete
queue model. Existing source tests pass and the current-source replay reports
all four versions. However, that replay copies current `labs` source rather
than the tutorial fences, so it does not prove that the printed checkpoints
are executable.

The v0-v3 tutorials repeat a minimal `skew.py` fence. v3 imports
`labs.partitioning.skew.queues`, but `queues.py` is not fenced in v3; the
replay therefore silently uses the repository implementation. The v3 printed
snippet only calls `simulate` and does not include the complete queue source
or isolated package dependency. Add complete, matching `skew.py` and
`queues.py` fences and replay both from a fresh temporary package. Assertions
must cover the roadmap's p99/capacity comparison: adding partitions cannot
split one hot key, salting reduces the hot queue, and a shared dispatcher
bottleneck limits capacity again.

No source or tutorial edits were made by the reviewer.
