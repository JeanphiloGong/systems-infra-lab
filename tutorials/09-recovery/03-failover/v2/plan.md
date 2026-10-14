# A03 v2: Patroni detects and promotes

Scenario: a Patroni/PostgreSQL cluster detects a failed primary and promotes a survivor; acknowledged writes must be checked against the recovered service.

Pressure/change: run the real Docker probe and record `rto_seconds`, client attempts, and acknowledged loss; isolate the old container and assert it is still running but cannot write.

Checkpoint: probe subprocess returns the expected failure for the isolated old primary, retained acknowledged rows equal `[('acknowledged',)]`, and output includes the measured fields.

Limit: RPO=0 applies only to pre-replicated samples; detection and Docker timings are environment-specific. v3 focuses on selective network isolation.

Replay: `uv run python -m labs.recovery.ha.patroni_probe` and `uv run pytest tests/recovery/ha -q`.

External limit: requires Docker Compose and Patroni images.
