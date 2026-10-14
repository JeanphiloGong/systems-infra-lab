# S06 build evidence

Status: complete authored checkpoints v0-v4, awaiting independent review. Prior source-reference drafts have been replaced; no acceptance claim before review.

Increment checks:
- v0 initial missing rows module caused test collection failure; implemented fixed56-byte rows,2 tests passed.
- v1 missing columns module failed; implemented projection, aggregate4 passed.
- v2 missing dictionary module failed; implemented code0 None and dictionary/code bytes, aggregate6 passed.
- v3 missing batches module failed; implemented immutable batch descriptions and closed min/max skip, aggregate8 passed.
- v4 missing workloads module failed; implemented slot point reads and full-record update comparisons, aggregate9 passed.
- Added explicit negative amount, empty batch, invalid batch size and invalid update/no-mutation checks: `uv run pytest tests/storage/columnar/ -q`:11 passed.

Strict printed-source replay:
`uv run python tests/storage/columnar/replay_s06.py` exit0 for all5 versions. Each guide's marked full Python sources are extracted into a distinct temporary directory; PYTHONPATH is that directory, no evolving worktree injection. Nonempty files/checks required.

Observed metrics:
v0:2 rows112B/8field slots.
v1:same total with40B/4 projected slots, unused id/note files deleted before scan to prove no dependency.
v2:300 regions3600B plain ->22B dictionary+600B codes; decode None/Unicode preserved.
v3:one matching batch40B/1 batch, full160B/4, no-overlap0B/0. Multiple closed boundaries compared to reference. Overlap without match still reads and yields0.
v4:scan row112B/column40B; full point56B both,1vs4 reads; full update56B both,1vs4 writes. After update reconstructed orders and aggregate40 equal.

Boundaries: application bytes/operations only; batches created once and frozen in memory, files immutable. No stale statistics used after update: v4 updates separate raw layouts. No Parquet/vectorization/concurrency/WAL/atomic multi-file update claims. Directory publication/statistics persistence remain outside scope.
