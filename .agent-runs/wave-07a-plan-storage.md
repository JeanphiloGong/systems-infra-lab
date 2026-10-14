# Wave 07a: R01/C01 plan revision

Modified only these nine version plans and this evidence record:

- tutorials/05-replication/01-leader-follower/v0/plan.md
- tutorials/05-replication/01-leader-follower/v1/plan.md
- tutorials/05-replication/01-leader-follower/v2/plan.md
- tutorials/05-replication/01-leader-follower/v3/plan.md
- tutorials/05-replication/01-leader-follower/v4/plan.md
- tutorials/06-consensus/01-cap-quorum/v0/plan.md
- tutorials/06-consensus/01-cap-quorum/v1/plan.md
- tutorials/06-consensus/01-cap-quorum/v2/plan.md
- tutorials/06-consensus/01-cap-quorum/v3/plan.md

Read current tutorial fences, implementation, behavior tests and extraction
runners. Applied from-scratch-tutorial-plan to replace generic task chains with
ordered failure/change/final-checkpoint tasks. Each file names its previous
checkpoint, exact behavior-test node, parameterized extraction-test node,
observable value or error, and remaining implementation limits.

R01 covers ordered application, delayed apply, read barriers, acknowledgement
positions, and interrupted catch-up. The plans explicitly identify restart()
as a no-op model and fail_before_replication() as a risk suffix, not real
process recovery or latency measurements.

C01 covers unknown outcome, the fixed lost-ack trace, explicit partition read
policies, and quorum set intersection. C01 v3 does not claim the missing
concurrent-history counterexample or a complete linearizability protocol.
Current extraction tests check successful execution, not expected stdout;
the plans distinguish that evidence from implementation behavior assertions.

Verification from /home/gong/date/2026/oct/systems-infra-lab:

```text
plans=9; required_fields=72; generic_phrases=0; broken_links=0
version-specific pytest commands: 18 passed
uv run pytest tests/replication/leader_follower tests/consensus/cap_quorum -q
20 passed
```

Field scan requires each of Pressure/Naive/Break/Change/Check/Freeze/Still-lacks/Next
as a bold label in every plan. Generic scan rejects the prior phrases
"establish the failure pressure", "最小模型只保留能触发压力的组件",
"本版只加入解决该压力", and "Keep the previous". Relative Markdown links
were resolved from each plan. Every `uv run pytest` command in the nine plans
was executed successfully, validating both file paths and pytest node selectors.

No other modules, accepted sample plans, progress, indexes, code, or tests were
changed in this batch. No commit created; independent review pending.
