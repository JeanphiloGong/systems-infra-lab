# T02 author build evidence

Scope: MVCC/Snapshot Isolation/write skew v0-v3. Environment same disposable PostgreSQL16.14/Python3.14.0 and uv lock as T01. Database URL supplied through SYSTEMS_LAB_DATABASE_URL; each real experiment creates random t02_ schema and deletes only its own schema.

- v0 RED: snapshots module absent; GREEN 2 real PG tests passed in0.27s. Early SELECT true/true/false; BEGIN without early SELECT false/false/false.
- v1 RED: model module absent; GREEN2 passed in0.02s. Empty/before creation raises, old/new/future snapshots read proper committed bool. This is explicitly educational model, not PG implementation.
- v2 RED: write_skew module absent; GREEN1 passed in0.22s. Actual two overlapping RR txns see2/2 then commit disjoint false writes yielding0; final rows asserted.
- v3 RED: protected module absent; GREEN1 passed in0.23s. Shared guard UPDATE creates40001 on stale second snapshot; new transaction repeats guard update+count decision; result1/False/1 and final false/true rows.

Commands: `uv run python -m pytest tests/transactions/mvcc/test_t02_snapshots.py -q`, `test_t02_model.py`, `test_t02_write_skew.py`, `test_t02_protected.py` respectively, with environment set for PG cases.

Final replay command: `SYSTEMS_LAB_DATABASE_URL='postgresql://systems_lab:systems_lab_local_only@127.0.0.1:55432/systems_lab' uv run python -m pytest tests/transactions/mvcc -q`.
Result: **11 passed in2.05s**. test_t02_replay.py extracts actual Markdown SQL/Python complete code into tmp dirs and launches isolated subprocess per version. It asserts both v0 schedules, model output, write skew and guarded retry result. No sleep scheduling or fake isolation results.

Independent v0 review PASS in reviews/s03-v1-v2-t02-v0.md. v1-v3 submitted for review, not self-approved.

Reviewer requested precise patch boundaries: v2 and v3 intermediate replacements could leave obsolete previous assertions. Updated instructions to replace whole experiment region including old assertions; v3 now gives exact guard.sql initialization line. Runtime/final checkpoint code unchanged; reviewer will replay amended incremental instructions.

Added automated intermediate replay derived from actual T01v1 check script and actual T02v2/v3 code blocks. It replaces full documented experiment region and checks sequential baseline, write-skew patch, guard conflict, and full retry patch. `SYSTEMS_LAB_DATABASE_URL=... uv run python -m pytest tests/transactions/mvcc/test_t02_replay.py -k intermediate -q`: **4 passed,5 deselected in1.56s**. This is additional intermediate evidence, separate from final checkpoints. Current total T02 cases15.

Boundaries: guard protects only participating writers and one roster group; the experiment retries once because it schedules one conflict, not a general retry service. Full serializable isolation deferred T04; version GC deferred S07. No PostgreSQL internal tuple visibility claims.

Added direct experiment functions and typed main entrypoints, plus one pure visible() teaching function and test replay extraction. No adapter or runtime framework. Kept one current implementation per module, historical checkpoints embedded in prose. No commits. Temporary tutorial patches are restored by complete final checkpoints.
