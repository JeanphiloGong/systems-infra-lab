# D03 v3: make pre-commit visible

Scenario: both participants report ready, then coordinator announces precommit before final commit.

Pressure/change: add the precommit phase and record every participant state transition.

Checkpoint: history is exactly `[['ready','ready'], ['precommit','precommit'], ['committed','committed']]`.

Limit/next: this remains a blocking fixed-membership protocol and does not solve consensus or network partitions. v4 constructs a timeout counterexample.

Replay: `uv run pytest tests/coordination/commit -q`.
