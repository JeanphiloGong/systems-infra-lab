# S01 build evidence

Scope: tutorials/01-storage-engines/01-pages-and-locality v0-v4; final evolving source labs/storage/pages; tests/storage/pages. No Git commits. Early initial import failure used system Python 3.12; root configured uv project environment during work and final `uv run python --version` reports Python 3.14.0. Guides target Python 3.12+. Guides are Chinese and every version includes its full required source files. Older implementations live in tutorial checkpoints, not duplicate labs version directories.

## Per-version implementation evidence

- v0 RED: `uv run pytest tests/storage/pages/test_s01_pages.py -q` failed collection because labs module did not exist. Added scan/generator. Same command GREEN: 2 passed. First/last/missing byte counts, empty file and truncation covered.
- v1 RED: `uv run pytest tests/storage/pages/test_s01_pages.py -q` failed importing absent direct. Added dense-slot direct lookup. Same command GREEN: 4 passed. All 100 positions compared against scan, negative/outside slots and corrupt layout covered.
- v2 RED: `uv run pytest tests/storage/pages/test_s01_paged.py -q` failed importing absent paged module. Added PageReader. `uv run pytest tests/storage/pages/ -q` GREEN: 12 passed. Page sizes 1,7,8,10,16,4096, cross-page and partial final page covered.
- v3 RED: `uv run pytest tests/storage/pages/test_s01_workload.py -q` failed importing absent workload module. Added fixed-seed permutations and measurement. `uv run pytest tests/storage/pages/ -q` GREEN: 14 passed. Same request set, reproducibility, checksum, counts and latency ordering covered. Afterwards replaced literal record width with RECORD.size; v4 aggregate run verifies this edit.
- v4 RED: `uv run pytest tests/storage/pages/test_s01_cache.py -q` produced 4 failures because PageReader had no capacity argument. Added bounded LRU. `uv run pytest tests/storage/pages/ -q` GREEN: 18 passed. Eviction trace, reload correctness, cross-page with one cache slot, cold/warm and negative capacity covered.

## Complete tutorial replay

Command: `uv run python tests/storage/pages/replay_s01.py`.

Result: exit 0. The harness extracts marked complete files from each tutorial into a separate TemporaryDirectory, sets PYTHONPATH to that directory, and executes the printed Python check. No imports from final evolving source are needed.

- v0: one checkpoint file; `v0 ok`.
- v1: one checkpoint file; `v1 ok`.
- v2: two checkpoint files; `v2 ok`.
- v3: three checkpoint files; `v3 ok`. Both permutations: 32 requests, 32 file reads, 4 unique pages, 2048 bytes, checksum 4960.
- v4: three checkpoint files; `v4 ok`. Cold application cache: 4 file reads / 256 bytes. Warm application cache: 0 file reads / 0 bytes. Both return checksum 4960. Eviction and small-cache workload checks passed.

Timings were emitted but are deliberately not correctness assertions or hardware conclusions. OS cache was not cleared; application metrics count returned bytes and logical file read operations, not physical I/O. Immutable input is a stated prerequisite, not enforced synchronization. Cache bounds refer to stored page data; Python metadata and pages_seen statistics consume additional memory.

## Review

Independent reviewer approved v0; evidence in reviews/s01-v0.md. Independent reviewer also approved v1-v4 with no required fixes; exact document hashes and reasoning in reviews/s01-v1-v4.md. Reviewer separately extracted each version, executed printed checks, and inspected/ran the 18 final tests. Entire S01 v0-v4 accepted within its declared teaching scope.

## Structure and cleanup

One PageReader object introduced because repeated queries require shared counters and cache state; permanent within the teaching module. No adapter/compatibility layers. No temporary implementation folders remain. Temporary replay files are automatically removed. Final source retains scan and direct intentionally as measured comparison algorithms.
