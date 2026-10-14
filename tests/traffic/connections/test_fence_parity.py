from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
TARGETS = {
    0: ["direct.py"],
    1: ["pool.py"],
    2: ["pool_cleanup.py"],
    3: ["proxy.py", "session_boundary.py"],
}


def test_connection_fences_match_labs() -> None:
    for version, names in TARGETS.items():
        text = (ROOT / f"tutorials/01-storage-engines/07-connections/v{version}/tutorial.md").read_text()
        blocks = dict(re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)```", text, re.S))
        assert list(blocks) == names
        for name in names:
            assert blocks[name].rstrip() == (ROOT / "labs/traffic/connections" / name).read_text().rstrip()
