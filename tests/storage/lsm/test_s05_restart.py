import json
import os
from pathlib import Path
import subprocess
import sys

from labs.storage.lsm.tombstones import TombstoneStore


def test_deleted_record_and_arbitrary_strings_survive_new_process(tmp_path: Path) -> None:
    old = tmp_path / "old.sst"
    new = tmp_path / "new.sst"
    TombstoneStore.create(old, {"deleted": "stale", "retained": "old"})
    TombstoneStore.create(new, {
        "deleted": None,
        "empty": "",
        "sentinel": "__TOMBSTONE__",
        "json": '["delete"]',
    })
    program = """
import json
from pathlib import Path
import sys
from labs.storage.lsm.tombstones import TombstoneStore

store = TombstoneStore([Path(sys.argv[1]), Path(sys.argv[2])])
keys = ['deleted', 'retained', 'empty', 'sentinel', 'json', 'absent']
print(json.dumps([store.get(key) for key in keys]))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(new), str(old)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3])},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [None, "old", "", "__TOMBSTONE__", '["delete"]', None]
