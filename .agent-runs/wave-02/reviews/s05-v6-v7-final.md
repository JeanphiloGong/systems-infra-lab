# S05 v6-v7 final rereview

Verdict: pass, with one minor wording correction.

The v6 printed checkpoint now contains an actual bytearray Bloom bitset with
deterministic hash positions. It appends framed length/complement/payload/CRC
records, records the complete WAL size, appends a torn suffix, reopens, and
asserts exact truncation to the last valid frame. It verifies a definite miss
returns zero logical table reads and searches natural candidate keys until a
Bloom collision produces a false positive requiring one read. The isolated
replay executes this printed checkpoint rather than current repository source.

The v7 checkpoint seeds three files, compares full selection (6 logical records
from 3 files) with oldest-two leveled selection (4 records from 2 files), and
reports distinct file bytes, output bytes, and peak old-plus-new bytes. Its
counters are explicitly application-level rather than physical I/O claims.

Independent verification:

```text
uv run python tests/storage/lsm/replay_s05_v6_v7.py
v6 replay ok
v7 replay ok

uv run pytest tests/storage/lsm/test_s05_v6_v7.py -q
3 passed in 0.18s
```

The v7 prose still says the policies are deterministic "because there are two
input files" although the checkpoint correctly uses three files. Change that
sentence to "three input files"; it does not affect the executable behavior.

No reviewer implementation or tutorial edits were made.
