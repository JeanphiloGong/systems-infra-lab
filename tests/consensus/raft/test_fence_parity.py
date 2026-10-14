from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]


def test_v1_v8_fences_match_historical_checkpoint_sources() -> None:
    for version in range(1, 9):
        text = (ROOT / f"tutorials/06-consensus/03-raft/v{version}/tutorial.md").read_text()
        blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```", text, re.S)
        assert len(blocks) == (3 if version == 8 else 2)
        for name, code in blocks:
            snapshot = ROOT / "labs/consensus/raft/checkpoints" / f"v{version}" / Path(name).name
            assert snapshot.exists()
            assert code.rstrip() == snapshot.read_text().rstrip()
