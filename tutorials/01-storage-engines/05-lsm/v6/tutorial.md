# S05 v6: WAL recovery and Bloom negative reads

An acknowledged update must survive a process restart, while a missing key should not force an SSTable scan. The small model below writes length-prefixed JSON records with a checksum, replays complete records, truncates a torn suffix, and uses a Bloom filter only to reject definite misses. A false positive still performs the table lookup.

## Pressure, break, and checkpoint

<!-- checkpoint: checkpoint.py -->

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json, os, zlib

class Bloom:
    def __init__(self): self.bits = bytearray(16)
    def positions(self, key): return [sum(key.encode()) % 128, (sum(key.encode()) * 7 + 3) % 128]
    def add(self, key):
        for bit in self.positions(key): self.bits[bit // 8] |= 1 << (bit % 8)
    def might_contain(self, key): return all(self.bits[bit // 8] & (1 << (bit % 8)) for bit in self.positions(key))

class Store:
    def __init__(self, path):
        self.path, self.values, self.filter = path, {}, Bloom()
        if path.exists():
            raw, pos = path.read_bytes(), 0
            while pos + 12 <= len(raw):
                size = int.from_bytes(raw[pos:pos + 4], "big"); end = pos + 12 + size
                if end > len(raw): break
                payload = raw[pos + 8:pos + 8 + size]
                if int.from_bytes(raw[pos + 8 + size:end], "big") != zlib.crc32(payload): raise ValueError("checksum")
                key, value = json.loads(payload); self.values[key] = value; self.filter.add(key); pos = end
            if pos != len(raw):
                with path.open("r+b") as stream: stream.truncate(pos); stream.flush(); os.fsync(stream.fileno())
    def put(self, key, value):
        payload = json.dumps([key, value]).encode(); record = len(payload).to_bytes(4, "big") + (~len(payload) & 0xFFFFFFFF).to_bytes(4, "big") + payload + zlib.crc32(payload).to_bytes(4, "big")
        with self.path.open("ab") as stream: stream.write(record); stream.flush(); os.fsync(stream.fileno())
        self.values[key] = value; self.filter.add(key)
    def get(self, key):
        if not self.filter.might_contain(key): return None, 0
        return self.values.get(key), 1

with TemporaryDirectory() as folder:
    path = Path(folder) / "write.wal"; store = Store(path); store.put("k", "v"); store.put("empty", "")
    complete_size = path.stat().st_size
    with path.open("ab") as stream: stream.write(b"torn suffix")
    recovered = Store(path)
    assert recovered.get("k") == ("v", 1) and recovered.get("missing") == (None, 0)
    assert path.stat().st_size == complete_size
    false_positive = next(candidate for candidate in (f"candidate-{i}" for i in range(10000)) if candidate not in recovered.values and recovered.filter.might_contain(candidate))
    assert recovered.get(false_positive) == (None, 1)
    print({"recovered": recovered.get("k"), "definite_miss_reads": recovered.get("missing")[1], "false_positive_key": false_positive, "false_positive_reads": recovered.get(false_positive)[1], "truncated_to": complete_size})
```

Run the checkpoint and `uv run pytest tests/storage/lsm/test_s05_v6_v7.py -q`. The checksum and truncation checks are failure boundaries; Bloom statistics are logical table reads, not physical I/O. Freeze this as the WAL/filter baseline before comparing compaction policies.
