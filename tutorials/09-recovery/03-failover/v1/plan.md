# A03 v1: human promotion and stale clients

Scenario: an operator promotes a replica after primary failure, but existing clients may still target the old primary.

Pressure/change: add explicit promotion state and client target selection; do not claim measured promotion latency.

Checkpoint: model replay verifies the promoted writable target and documents that old-client fencing remains unverified.

Limit/next: no real HA supervisor. v2 uses Patroni detection and records RTO/RPO observations.

Replay: `uv run python tests/recovery/ha/replay_a03.py`.
