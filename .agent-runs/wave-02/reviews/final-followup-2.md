# Wave 02 final follow-up 2

## Findings

- [revise] T04 v2 remains unbounded in the printed checkpoint: `retry_once`
  still uses `while True` and has no `max_retries` parameter. The prose now
  says `max_retries` limits attempts, but the fence contradicts it. The clean
  `--retry` command returns `(0, True)` and explicitly does not trigger a
  serialization failure; this is honest about the example but does not prove
  retry behavior. Fix the fence or narrow the prose further.

## Passes

- S02 v7 page-access and save-failure experiments now exist as a complete
  `experiments.py` fence. The fence imports the v7 tree/page files supplied in
  the same tutorial, compares array key comparisons with tree node visits,
  starts a child that writes half a page file and exits, then requires `load`
  to reject the partial file.
- `uv run python tests/storage/bplus_tree/replay_s02.py`: all v0-v7 replay
  checks passed.
- `uv run pytest tests/storage/bplus_tree -q`: 16 passed.
- `uv run python -m labs.storage.bplus_tree.experiments` produced
  `{"array_key_comparisons": 1519, "partial_bytes": 4992, "probes": 3,
  "tree_node_visits": 21}`.
- T04 printed v3 `--metrics` runs and emits measured `aborted`, `remaining`,
  and positive `elapsed_seconds`; T04 focused tests pass (3 tests).

## Verdict

S02 v7: pass for its now-supported experiment scope. T04 v3: pass. T04 v2:
revise pending the printed-code/prose mismatch and bounded retry fix. No other
new blockers found in this pass.
