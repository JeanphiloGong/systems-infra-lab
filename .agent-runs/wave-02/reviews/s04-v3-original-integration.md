# S04 v3 original-scope review

Verdict: pass against the original `docs/roadmap.md` S04 v3 scope. No required
fixes found.

The checkpoint integrates the Bloom filter directly with the frozen S05 v1
immutable SSTable. The filter is built by scanning every key in the actual
table, so the caller cannot supply an incomplete key list. A negative filter
answer returns `(None, 0)` without opening the table; a possible answer calls
the real `SSTable.get`, including forced false positives. The guide preserves
empty-string values and Unicode keys, reopens the same file, and states the
immutable-file lifetime and the absence of persisted filters, updates, deletes,
and multi-version visibility.

The printed checkpoint computes a 302-request baseline, performs a separate
one-scan filter build, compares all 102 real keys plus 200 absent keys against
the original SSTable, and asserts reduced query scans. It then uses
`bits=1, hashes=1` to force a false positive and asserts that the missing key
still reaches the SSTable. The focused tests additionally monkeypatch
`Path.open` to count actual file opens and cover omitted-key regression,
empty values, Unicode, and reopen behavior.

Executed independently:

```text
uv run python tests/storage/bloom/replay_s04.py
v0 replay ok
v1 replay ok
v2 replay ok
v3 replay ok

uv run pytest tests/storage/bloom -q
9 passed in 0.28s
```

The replay extracts the printed checkpoint files into a temporary directory,
sets `PYTHONPATH` to that directory, and executes each version. v3 embeds the
same SSTable and Bloom filter source as the frozen dependencies; normalized
content matches exactly (the raw hash differs only because a Markdown fence
omits the final newline). The v3 tutorial SHA-256 is
`2dc553b621b6aee0a980d7fac1d7a45a3e2545634430b71839b74961449fbd4a`.

This accepts S04 v3 only. It does not imply that later LSM integration,
tombstone handling, persisted filters, or deletion semantics are complete.
