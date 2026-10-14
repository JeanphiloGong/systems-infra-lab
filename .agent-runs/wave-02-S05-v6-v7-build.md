# S05 v6-v7 build evidence

Implemented v6 WAL recovery and Bloom negative-read filtering in `labs/storage/lsm/v6.py`, using the frozen manifest/SSTable/TombstoneStore boundaries and framed WAL records. Implemented v7 full versus two-file leveled compaction metrics in `labs/storage/lsm/v7.py`.

Tutorials and isolated replay:

- `tutorials/01-storage-engines/05-lsm/v6/tutorial.md`
- `tutorials/01-storage-engines/05-lsm/v7/tutorial.md`
- `tests/storage/lsm/replay_s05_v6_v7.py`

Verification:

```text
uv run pytest tests/storage/lsm -q
56 passed in 2.85s

uv run python tests/storage/lsm/replay_s05_v6_v7.py
v6 replay ok
v7 replay ok
```

The replay checkpoints are standalone temporary-directory scripts. v6 now appends a torn suffix, reopens and asserts exact truncation to the pre-torn byte offset, verifies WAL recovery, and finds a natural Bloom hash collision: the definite miss performs zero table reads while the false positive performs one. v7 uses three files: full reads three files while leveled reads two, with distinct logical/byte/space metrics. These are application-level counters, not physical I/O or production compaction benchmarks.
