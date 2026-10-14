# S02 build evidence

Scope currently implemented: v0-v5. Final evolving source is `labs/storage/bplus_tree/`; tests are `tests/storage/bplus_tree/`; no duplicate version source directories and no commits.

- v0 RED: import failed before `array_index.py`; GREEN `uv run pytest tests/storage/bplus_tree/test_s02_v0.py -q`: 2 passed. Isolated printed checkpoint replay passed.
- v1 RED: import failed before `leaf.py`; GREEN `uv run pytest tests/storage/bplus_tree/test_s02_v1.py -q`: 2 passed. Capacity, duplicate overwrite, and invalid capacity covered.
- v2-v4 initial tree tests exposed two implementation bugs: equality needed `bisect_right` at internal separators, and recursive parent lookup needed to find the direct parent; both fixed before acceptance. Final `uv run pytest tests/storage/bplus_tree/test_s02_tree.py -q`: 2 passed, including 100 deterministic shuffled inserts with structural validation and range scan.
- v5 replaced the rejected all-items JSON wrapper with fixed 256-byte page records: metadata/root page, leaf/internal page IDs, leaf links, and per-page CRC32. `uv run pytest tests/storage/bplus_tree/ -q`: 10 passed, including topology-preserving reopen, signed values, truncation/extra-byte/checksum rejection, and no overwrite on encoding failure.

v6 now performs local leaf deletion with separator updates, sibling borrow, leaf merge, internal sibling borrow/merge, parent separator refresh, and root collapse. `uv run pytest tests/storage/bplus_tree/test_s02_delete.py -q`: 2 passed; tree/random tests remain passing. v7 summary docs are present; strict replay currently covers v0-v4 because v6/v7 still need complete standalone source fences.
