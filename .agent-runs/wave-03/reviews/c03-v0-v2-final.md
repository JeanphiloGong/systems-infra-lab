# C03 v0-v2 independent review

Verdict: PASS for the explicitly limited C03 v0-v2 scope in `docs/roadmap.md:416`. No v3-v8 capability is implied.

## Actual verification

Read the original roadmap, README, v0-v2 tutorials, `model.py`, `experiments.py`, and replay/tests. Ran:

- `uv run python -m pytest tests/consensus/raft -q`: **3 passed in 0.30s**.
- `uv run python tests/consensus/raft/replay_c03.py`: **C03 tutorial v0-v2 replay ok**.

Replay extracts each version's marked files into a fresh temporary package and executes them with only that temporary directory on PYTHONPATH. v0 additionally asserts the extracted model has no persistence or AppendEntries methods. v1 executes a real child process ending with `os._exit(71)`, then a fresh process reloads the JSON state. v2's extracted experiment performs a wrong-prefix rejection and conflicting-suffix replacement.

## Roadmap evidence

- v0 appends a term/indexed command, keeps uncommitted state out of the state machine, then applies committed entries in order. `commit_to` only advances within existing log bounds.
- v1 persists term/vote via temp-file write, flush/fsync and atomic replace. A child process exits after voting term4 for `b`; a fresh process restores `(term=4,vote=b)` and rejects candidate `c` in the same term, proving durable single-vote state across restart.
- v2 checks `prev_log_index`/`prev_log_term`, rejects a mismatched prefix, deletes an uncommitted conflicting suffix, appends the leader entry, advances commit and applies `mode=new`. The test also rejects overwriting an already committed entry.

## Explicit limits

This checkpoint is a deterministic single-process model and local JSON durability exercise. It does not implement majority replication, full elections, candidate log freshness, message loss/reordering, partition recovery, snapshots, dynamic membership or linearizable reads. The README and v2 text explicitly defer those roadmap versions. The v1 crash point is after the vote persistence call, not every possible persistence boundary; v2 has no crash/restart or network transport. Those are appropriate deferred boundaries, not hidden claims.

Review artifact only; no implementation abstraction or source cleanup added.
