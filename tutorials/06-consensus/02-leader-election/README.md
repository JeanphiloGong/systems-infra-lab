# C02: Leader Election

[v0](v0/tutorial.md) timeout split-brain, [v1](v1/tutorial.md) majority voting, [v2](v2/tutorial.md) durable votes, [v3](v3/tutorial.md) lease and resource fencing, [v4](v4/tutorial.md) failure recovery.

Source is in `labs/consensus/leader_election/`, following the task's directory choice. The roadmap labels the same module `election/`. These are deterministic experiments, not a deployed distributed lock service.

```bash
uv run pytest tests/consensus/leader_election -q
uv run python tests/consensus/leader_election/replay_c02.py
```
