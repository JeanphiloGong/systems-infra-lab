# S05 v6-v7 independent review

Verdict: not accepted yet against the original roadmap scope.

Current source tests and the isolated tutorial scripts are green, but the
printed tutorials narrow the required experiments:

- v6 prints a standalone length/checksum WAL plus in-memory Bloom store. It
  does not integrate the frozen manifest/SSTable/TombstoneStore boundaries
  used by `labs/storage/lsm/v6.py`. Its prose mentions torn-suffix recovery,
  but the printed check never creates a torn frame, restarts, verifies
  truncation, or exercises a false-positive table read.
- v7 prints a standalone plain `key=value` compactor. With only two input
  files, `full` and `leveled` select exactly the same files and produce the
  same logical read/file counters; this does not demonstrate distinct
  compaction strategies or a meaningful read/write/space tradeoff. The
  current `labs/storage/lsm/v7.py` is a separate implementation and is not
  the code executed by the tutorial replay.

The current-source verification was:

```text
uv run pytest tests/storage/lsm -q
56 passed
uv run python tests/storage/lsm/replay_s05_v6_v7.py
v6 replay ok
v7 replay ok
```

Those results do not close the printed-checkpoint gaps above. No reviewer
source or tutorial edits were made.
