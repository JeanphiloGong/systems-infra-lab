from pathlib import Path
import os, re, subprocess, sys

GUIDES = Path(__file__).resolve().parents[3] / "tutorials/01-storage-engines/07-vacuum"

def fenced(version: int, module: str) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: labs/storage/vacuum/{module}.py -->"
    match = re.search(re.escape(marker) + r"\s*```python\n(.*?)```", text, re.S)
    assert match is not None
    return match.group(1)

def run_checkpoint(tmp_path: Path, version: int, module: str, args: list[str]) -> str:
    package = tmp_path / "labs/storage/vacuum"
    package.mkdir(parents=True, exist_ok=True)
    for parent in (tmp_path / "labs", tmp_path / "labs/storage", package):
        (parent / "__init__.py").write_text("")
    (package / "vacuum.py").write_text(fenced(0, "vacuum"))
    (package / f"{module}.py").write_text(fenced(version, module))
    result = subprocess.run([sys.executable, "-m", f"labs.storage.vacuum.{module}", *args], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)}, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stdout

def test_all_frozen_checkpoints_replay_against_real_postgres(tmp_path: Path) -> None:
    assert "logical rows: 1000" in run_checkpoint(tmp_path / "v0", 0, "vacuum", ["--rounds", "2"])
    assert run_checkpoint(tmp_path / "v1", 1, "reuse", []).strip().startswith("(")
    assert run_checkpoint(tmp_path / "v2", 2, "snapshot", []).strip() == "(0, 1000, 1000)"
    before, rewritten, count = (int(value.strip()) for value in run_checkpoint(tmp_path / "v3", 3, "full", []).strip()[1:-1].split(","))
    assert rewritten < before and count == 1000
    assert "'observed':" in run_checkpoint(tmp_path / "v4", 4, "automatic", ["--timeout", "0"])

def test_all_version_fences_exist() -> None:
    for version in range(5):
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        assert "```python" in text and "```bash" in text
