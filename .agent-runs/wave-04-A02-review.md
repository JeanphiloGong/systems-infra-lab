# A02 v1-v3 independent review

Verdict: **REOPENED**. The earlier pass below was too broad; it is superseded
by the concrete failures in `wave-04-A02-reopened.md`. v1-v3 are not accepted.

## Verification

`uv run pytest tests/recovery -q` returned **11 passed in 2.36s** and
`uv run python tests/recovery/checkpoint/replay_a02.py` printed `A02 tutorial
v1-v3 replay ok`. The replay extracts each complete `store.py` fence into a
fresh package, checks exact source parity and executes it with a new interpreter.

v1 verifies a snapshot at the exact recovered position and suffix continuation.
v2 publishes a checksummed manifest atomically, injects exits before replace,
after replace and after directory sync, then recovers with a fresh Store before
reclaiming the prefix. v3 keeps two generations, falls back when the newest
snapshot is corrupt, and rejects recovery when the fallback's required log
segment is missing. Snapshot state and absolute positions remain aligned; the
scope explicitly remains a paused single writer and does not claim ARIES or
concurrent snapshot guarantees.

No blocking findings. A02 v1-v3 are accepted.
