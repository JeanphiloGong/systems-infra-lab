# S05 v0-v1 author evidence

Scope: MemTable v0 and single immutable SSTable v1 only. Future v2-v7 remain roadmap work; no complete-LSM claim.

RED v0: missing labs.storage.lsm module; GREEN1 passed0.02s. RED v1: missing sstable module; GREEN total8 passed0.12s. Final command `uv run python -m pytest tests/storage/lsm -q`: **11 passed in0.45s**.

Coverage: overwrite-in-memory keeps latest value; sorted snapshot independent of later put; UTF8/newline/quotes/backslashes/empty value roundtrip; no overwrite of existing file; fresh subprocess reopen; invalid record shape/duplicate/decreasing keys rejected; empty SSTable; invalid create input leaves no file. Actual Markdown checkpoint Python is extracted into temporary directories and executed, including fresh process reopening. All intermediate tutorial Python examples also execute.

Frozen API communicated to S04 author: MemTable.put/get/items; SSTable.create(Path,Mapping[str,str]); SSTable(Path).items() iterator sorted strict keys; get()->str|None. get scans entire file in this version; Bloom can skip file open on definite absence without changing results.

File create uses same-directory temporary file + os.link to refuse overwrite and publish complete bytes; no fsync means no power-loss durability claim. No multi-file manifest, tombstones, WAL, indexes or compaction introduced. Runtime additions are the two scenario data structures, no adapter/framework. Temporary file name removed in finally; only version code in docs, no duplicated source trees. No commits.

Independent review requested; not self-approved.

## v2-v3 continuation

Added VersionedStore with explicit caller-owned newest-first path order. v3 introduces a separate typed record schema over unchanged SSTable string payloads: ['value',text] vs ['delete']. No reserved string; v3 files are all produced by TombstoneStore.create and v2 raw files are not silently adapted. SSTable v1 source unchanged for S04 dependency.

Tests cover newest value, old-only key, new empty string, empty file set, persistent deletion, later put after deletion, empty/reserved/JSON-like strings, malformed tag and invalid input cleanup. Root also supplied test_s05_restart.py; author did not edit it.

Actual Markdown-derived v2/v3 checkpoints include SSTable dependency in full, run create and reopen in separate subprocesses with isolated cwd/PYTHONPATH. v2 priority-reversal patch is additionally replayed. Initial reversal test hit Python same-size/same-second bytecode cache, resolved by disabling bytecode writes in isolated replay subprocesses; application code unchanged.

Reviewer requested a visible v3 pressure break. Added executable v2-baseline omission script to v3 tutorial and replay test: a newer empty SSTable omits `k`, VersionedStore returns old value and prints `omission resurrects: old`; focused replay now **6 passed in0.97s**.

Final `uv run python -m pytest tests/storage/lsm -q`: **20 passed in1.09s**. No compaction/WAL/manifest or fsync guarantees added. v2/v3 submitted for independent review, not self-approved. No commits.

## v4 continuation

v2/v3 were subsequently independently accepted. v4 adds only `compaction.py`: caller supplies complete static newest-first file list and contiguous [start,stop) slice. First version per key wins; malformed tags fail before publication. Partial slices retain tombstones; suffix reaching oldest end may drop them. Output replaces same list position, no input deletion or manifest/WAL.

RED: test_s05_compaction.py import failed before implementation. Initial GREEN8 passed0.06s. Extended tests cover every contiguous interval among three files, outside older value resurrection risk, full removal, oldest suffix/newer priority, invalid ranges, shadowed bad tag, empty values and existing output refusal.

`uv run python -m pytest tests/storage/lsm/test_s05_compaction.py tests/storage/lsm/test_s05_compaction_replay.py -q`: **16 passed in0.39s**. Replay extracts actual tutorial's three complete Python sources into a clean tmp package. It runs the unsafe-delete-drop baseline (old value returns), then separate create/reopen subprocesses both proving partial has ['delete'], full has no record, logical results remain None and keep=new. No source path dependency.

v4 tutorial/plan complete and independently submitted for review. v0-v3 accepted source and guides unchanged. New abstraction only compact function with explicit file-list contract and demo main; no compatibility or framework layers, no temporary source artifacts. No commits.

v5 initial draft used RuntimeError and fence-presence checks; those did not satisfy process-crash/replay scope and were rejected. Superseding implementation now performs actual os._exit71/72 in separate publication processes starting from valid OLD manifest. Separate reader processes assert OLD after71 / NEW after72 plus stable old-only key and actual JSON file collection.

Validation rejects malformed/nonlist JSON, duplicate/missing/non-.sst/outside names and symlinks; validates parent before basename conversion. Removed unused NoReturn/redundant name check. Publication fsyncs immutable data and directory first, temp manifest before replace, directory after replace. Single writer local POSIX assumptions explicit; after-replace test is process termination before final directory sync, not power-loss proof. Inputs never deleted.

New test_s05_manifest_replay extracts all three complete printed sources to isolated package, executes actual tutorial CLI command sequence (translated uv interpreter invocation only), verifies real71/72 exits and fresh-reader JSON, and executes incomplete-JSON baseline. No worktree imports or fence-only acceptance. Focused command `uv run python -m pytest tests/storage/lsm/test_s05_manifest.py tests/storage/lsm/test_s05_manifest_replay.py -q`: **16 passed in1.27s**. Independent rereview requested; no self-acceptance.
