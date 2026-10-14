# S05 v7: full versus leveled compaction

Repeated immutable files preserve newest-first semantics but duplicate records and bytes. This checkpoint compares two deliberately small policies: merge every file, or merge only the oldest two files. It reports logical records, application-level file bytes, files read, and peak old-plus-new bytes.

## Pressure, break, and checkpoint

<!-- checkpoint: checkpoint.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory


def compact(files, strategy, output):
    selected = files if strategy == "full" else files[-2:]
    latest = {}
    logical_read = 0
    for path in selected:
        for line in path.read_text().splitlines():
            key, value = line.split("=", 1); logical_read += 1
            latest.setdefault(key, value)
    output.write_text("".join(f"{key}={value}\n" for key, value in sorted(latest.items())))
    bytes_read = sum(path.stat().st_size for path in selected)
    bytes_written = output.stat().st_size
    return {"logical_read": logical_read, "logical_written": len(latest), "bytes_read": bytes_read, "bytes_written": bytes_written, "files_read": len(selected), "peak_bytes": bytes_read + bytes_written}


with TemporaryDirectory() as folder:
    root = Path(folder)
    one = root / "one.sst"; two = root / "two.sst"; three = root / "three.sst"
    one.write_text("a=old\nb=stable\n"); two.write_text("a=middle\nc=latest\n"); three.write_text("a=new\nd=tail\n")
    full = compact([three, two, one], "full", root / "full.sst")
    leveled = compact([three, two, one], "leveled", root / "leveled.sst")
    assert full["logical_read"] == 6 and leveled["logical_read"] == 4
    assert full["files_read"] == 3 and leveled["files_read"] == 2
    assert full["bytes_written"] > 0 and full["peak_bytes"] >= full["bytes_read"]
    print({"full": full, "leveled": leveled})
```

Both policies are explicit and deterministic here because there are three input files. In a larger store, leveled selection would be scheduled by size/level rather than by this fixed slice. The counters describe logical application work and file lengths; they are not hardware write amplification or disk latency measurements.
