# S05 v6 plan

Add two durability/read boundaries to the frozen LSM model: framed, checksummed WAL records replay after restart, and a Bloom filter can reject definite misses before opening an SSTable. The checkpoint deliberately uses a small standalone model; it does not claim crash durability beyond the local fsync steps.


## Tutorial Increment

- **Pressure:** The high-frequency key updates and tombstones scenario makes the current checkpoint insufficient for the v6 requirement.
- **Naive:** Keep the previous version's simplest behavior and record what it cannot observe or protect.
- **Break:** An acknowledged update must survive a process restart, while a missing key should not force an SSTable scan. The small model below writes length-prefixed JSON records with a checksum, replays complete records, truncates a torn suffix, and uses a Bloom filter o
- **Change:** # S05 v6: WAL recovery and Bloom negative reads; implement only the behavior introduced by this version and retain the previous checkpoint contract.
- **Check:** Extract the complete source fence and run `uv run pytest tests/storage/lsm -q`; assert the version-specific result from the tutorial instead of checking only that the process exits.
- **Freeze:** Freeze the source fence, its caller, and the expected assertion together; the replay must run from a fresh temporary directory.
- **Still-lacks:** This remains a S05 LSM/compaction teaching model for high-frequency key updates and tombstones; it does not claim production durability, concurrency, or distributed behavior beyond the stated experiment.
- **Next:** Continue with v7 of S05 LSM/compaction, carrying forward the state and invariant rather than restarting from a disconnected example.

