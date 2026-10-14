# D03 v4: timeout is not consensus

Scenario: one participant is `precommit` while another is only `ready`; a timeout shortcut cannot safely infer the global outcome.

Pressure/change: retain the v3 history and add a partition/timing model that records independent decisions.

Checkpoint: before states are `['precommit','ready']`; after recovery they are `['committed','aborted']`, demonstrating atomic commit assumptions are violated by timeout.

Limit: this is a counterexample, not a consensus implementation or failure detector. Later coordination topics cover quorum consensus.

Replay: `uv run pytest tests/coordination/commit -q`.
