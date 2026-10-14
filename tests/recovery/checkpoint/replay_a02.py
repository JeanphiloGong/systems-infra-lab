from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "tutorials/09-recovery/02-checkpoint"
FENCED = {
    "labs/storage/wal/framing.py",
    "labs/recovery/checkpoint/baseline.py",
    "labs/recovery/checkpoint/store.py",
}


def extract(version: int, directory: Path) -> None:
    text = (BASE / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```", text, re.S)
    assert {name for name, _ in blocks} == FENCED
    for name, code in blocks:
        assert code.rstrip() == (ROOT / name).read_text().rstrip()
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")


def run_probe(version: int) -> str:
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        extract(version, base)
        (base / "labs/storage/__init__.py").write_text("")
        (base / "labs/storage/wal/__init__.py").write_text("")
        (base / "labs/recovery/__init__.py").write_text("")
        (base / "labs/recovery/checkpoint/__init__.py").write_text("")
        probe = base / "probe.py"
        if version == 1:
            body = (
                "from pathlib import Path\n"
                "from labs.recovery.checkpoint.store import Store\n"
                "s=Store(Path('data'))\n"
                "for i in range(1,11): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "s.snapshot(10)\n"
                "for i in range(11,16): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "print(s.recover()[:2])\n"
            )
            expected = "({'alice': 85, 'bob': 115}, 15)"
        elif version == 2:
            body = (
                "from pathlib import Path\n"
                "from labs.recovery.checkpoint.store import Store\n"
                "p=Path('data'); s=Store(p)\n"
                "for i in range(1,6): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "s.snapshot(5); s.publish([5])\n"
                "print(len(list(p.glob('[0-9]*.wal'))), s.recover()[:2])\n"
            )
            expected = "0 ({'alice': 95, 'bob': 105}, 5)"
        else:
            body = (
                "from pathlib import Path\n"
                "from labs.recovery.checkpoint.store import Store\n"
                "p=Path('data'); s=Store(p)\n"
                "for i in range(1,11): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "s.snapshot(10)\n"
                "for i in range(11,21): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "s.snapshot(20)\n"
                "for i in range(21,26): s.commit(i, {'alice':100-i,'bob':100+i})\n"
                "s.publish([10,20]); s.snapshot_path(20).write_bytes(b'corrupt')\n"
                "print(s.recover()[:2])\n"
            )
            expected = "({'alice': 75, 'bob': 125}, 25)"
        probe.write_text(body)
        result = subprocess.run([sys.executable, str(probe)], cwd=base,
                                env={"PYTHONPATH": str(base)}, check=True,
                                capture_output=True, text=True)
        assert result.stdout.strip() == expected
        return result.stdout.strip()


def main() -> None:
    outputs = [run_probe(version) for version in (1, 2, 3)]
    print("A02 tutorial v1-v3 replay ok:", outputs)


if __name__ == "__main__":
    main()
