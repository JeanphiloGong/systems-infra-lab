# S05 v7 plan

Compare two explicit simplified compaction policies: full merge of all files and a two-file leveled merge. Measure logical records, file bytes read/written, files read, and peak old-plus-new bytes. These are application-level measurements, not physical disk I/O.


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v7 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** Repeated immutable files preserve newest-first semantics but duplicate records and bytes. This checkpoint compares two deliberately small policies: merge every file, or merge only the oldest two files. It reports logical records, application-level file bytes, 
- **Change:** # S05 v7: full versus leveled compaction; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with the module's final boundary, carrying forward the state and invariant rather than restarting from a disconnected example.

