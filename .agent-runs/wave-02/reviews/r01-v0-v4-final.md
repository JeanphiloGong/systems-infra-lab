# R01 v0-v4 independent review

Verdict: pass against the original roadmap scope.

The five complete fences implement ordered leader logs and follower progress
that survives the modeled restart (v0), delayed follower application and
observable stale reads (v1), read-position barriers with timeout and a leader
read fallback (v2), asynchronous versus follower acknowledgment loss
boundaries (v3), and interrupted catch-up with duplicate-safe resume and gap
rejection (v4). The tutorials state that this is a teaching protocol without
automatic leader election and distinguish receipt, persistence, and apply
conditions.

The replay extracts exactly one fence per version into fresh scripts. Focused
tests cover all five semantics plus fence uniqueness.

```text
uv run pytest tests/replication/leader_follower -q
11 passed in 0.37s
uv run python tests/replication/leader_follower/replay_r01.py
all version checkpoint executions passed
```

No reviewer source or tutorial edits were made.
