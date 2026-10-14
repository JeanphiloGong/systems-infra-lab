# S02 v7 original experiment requirements recheck

Verdict: pass. This record supersedes earlier acceptance of a linear-array
comparison and post-hoc truncated-copy experiment, which did not prove the
original comparison and save-failure requirements.

The revised array path performs binary search and counts distinct logical
pages per query. Tree traversal counts root-to-leaf pages. Both use 16-byte
records, capacity 15 per 256-byte leaf/data page, and assert identical hit
results; counters are explicitly logical rather than physical I/O.

The failure child calls the real save() on an existing saved file. Linux
RLIMIT_FSIZE is set to one page and SIGXFSZ uses its default terminating
handler. Parent requires the exact negative signal exit code and 256-byte
partial file; load rejects the metadata/file-size mismatch. This is actual
interruption during save, with OS-specific limits disclosed, not truncation
of a successful copy or a claim of power-loss recovery.

Inspected printed experiments.py against source and tests. The replay now
executes the v7 printed experiment in a temporary directory using embedded
tree/page/experiment files.

Executed:

```text
uv run python tests/storage/bplus_tree/replay_s02.py
all v0-v7 passed
v7 probes=4 array_page_reads=26 tree_page_reads=12
uv run pytest tests/storage/bplus_tree -q
16 passed in 0.56s
```

Exact v7 tutorial SHA-256:
`ff576761dbd0c4c31a6d7d3245cd7092e37298c1873db7b8059a5eef97294f9b`.

No source/tutorial/test edits by reviewer.
