from pathlib import Path
import re, subprocess, sys

GUIDES = Path(__file__).resolve().parents[3] / "tutorials/02-traffic/03-retry"

def source(version: int) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    target = {
        0: "labs/traffic/resilience/v0.py",
        1: "labs/traffic/resilience/v1.py",
        2: "labs/traffic/resilience/v2.py",
    }[version]
    match = re.search(
        rf"<!-- checkpoint: {re.escape(target)} -->\s*\n" + chr(96) * 3 + r"python\n(.*?)" + chr(96) * 3,
        text,
        re.S,
    )
    assert match is not None
    return match.group(1)

def test_early_versions_have_their_own_boundaries(tmp_path: Path) -> None:
    for version in (0, 1, 2):
        path = tmp_path / f"v{version}.py"
        path.write_text(source(version))
        result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
    assert "class PermanentError" not in source(0)
    assert "deadline" not in source(0)
    assert "class PermanentError" in source(1)
    assert "random" not in source(1)
    assert "random" in source(2)
