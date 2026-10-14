# C02 Author Evidence

Scope: `labs/consensus/leader_election/`, `tests/consensus/leader_election/`, and `tutorials/06-consensus/02-leader-election/`. The task specifies the directory `leader_election`; the roadmap refers to the same module as `election`. No progress ledger or other module was changed.

Implemented one fixed-membership sequential event simulator: node-owned persistent term/vote files, deterministic heartbeat timeouts and message partitions, majority election, trusted winner registration, and a resource that checks owner, term, and lease expiry before mutation.

## Actual Checks

```text
uv run pytest tests/consensus/leader_election/test_c02.py -q
9 passed in 1.43s

uv run python tests/consensus/leader_election/replay_c02.py
v0 replay ok: timeout_self_elected = [a, b, c]
v1 replay ok: term1_winner = a, term2_winner = b; delivered vote trace recorded
v2 replay ok: recovered_term = 7, recovered_vote = b, double_vote_rejected = true
v3 replay ok: old_write_rejected = true, value = successor, resource_term = 2
v4 replay ok: partition and GC retain old belief; restart clears it; all old writes rejected
```

Tests include all six candidate orderings, minority failure, stale vote/heartbeat rejection, the exact lease-expiry boundary, wrong-owner/current-term rejection, and restart restoration. v2 writer exits using `os._exit(71)` and the reader is a different process. v4 reconstructs a node from its saved state within the deterministic simulator; the true process interruption is independently verified by v2.

Each guide contains the full exact `model.py` and `experiments.py` source. Replay extracts both, overrides PYTHONPATH to the temporary directory, runs its module there, and inspects scenario output. The vote writer/reader subprocesses inherit that isolated directory. Assertions execute real per-node decisions and resource calls; no current-worktree implementation is loaded.

## Boundaries

This is election and authority fencing, not replicated-log consensus. Partitions and GC pauses use a deterministic message-delivery model, not real sockets. Single-thread event processing supplies atomicity inside each simulated service. Time is an explicitly shared monotonic test clock. The trusted resource does not restart during the lease/fencing experiments; production durable resource fencing, authenticated quorum certificates, lease renewal, and randomized election retries are not claimed.

New permanent teaching classes are Node, Election, and Resource. Removed the initial caller-supplied-vote-count draft, replacing it directly with node-owned voting; no adapters, compatibility paths, or temporary abstractions remain. Author verification is complete; independent review remains pending.
