# C02 v0-v4 independent review

Verdict: PASS within the explicit fixed-membership sequential simulator.
Reviewed against docs/roadmap.md C02 v0-v4, including its non-consensus boundary.

- v0 executes heartbeat timeout self-election during isolation and produces
  multiple leader beliefs; it does not pretend this grants resource authority.
- v1 calls each node's vote decision, records delivered requests, and requires
  majority ownership before activation. All six candidate permutations have
  one winner per term; isolated minority cannot activate the resource.
- v2 flushes/fsyncs vote data, atomically replaces it, fsyncs the directory,
  and only then replies. A writer subprocess votes in term 7 and exits via
  os._exit(71); a separate reader restores term/vote and rejects a different
  candidate in the same term and stale-term requests.
- v3 rejects writes exactly at lease expiry and after a successor activation.
  The former leader still believes it is leader, yet cannot mutate the value.
- v4 compares message isolation, GC pause modeled as message suspension, and
  restart reconstruction. After healing, even a former leader that learns
  the current term cannot write because the resource also checks owner.

Independent verification:

```text
uv run pytest tests/consensus/leader_election -q
9 passed in 1.41s
uv run python tests/consensus/leader_election/replay_c02.py
all v0-v4 passed; v2 child exit/recovery asserted
```

Each guide embeds both complete model.py and experiments.py. All ten fences
match the current files exactly, including trailing newline. Replay extracts
both into a temporary directory, replaces PYTHONPATH, runs there, and makes
its vote subprocesses inherit that isolated package. No current source is
copied into the replay directory.

Limits are material and explicitly documented: trusted registration of quorum
winners, shared test clock, sequential events, fixed membership, no resource
restart, no replicated log, no authenticated quorum certificate. The tests
prove the shown histories, not production election safety under arbitrary
concurrency or power loss.

Frozen tutorial SHA-256:

```text
v0 37bb7df7605edbac633e582aabbe5c8f7e739ee0e56afe2c175d94dc63c2e21c
v1 a3ff078c809fe8c237d5fa60298bfe339a4e8832b54565ee081e8640f5badce4
v2 6203da497cd8a4f5880f0acea6172a037282515b97a1c4bf4613e6d5f8f74bda
v3 814385f882f2e00b0c6cd43b4b4b8f79bd5aaed21acb439dfca984143fef89a2
v4 79113d96769b750f651eac9fd61412c4adee18926431f0dc34bc4046757ea3c1
```

Reviewer edited review artifacts only; no new code abstraction or cleanup.
