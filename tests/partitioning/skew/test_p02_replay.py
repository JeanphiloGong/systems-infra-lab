from pathlib import Path
import os, re, subprocess, sys


GUIDES = Path(__file__).resolve().parents[3] / "tutorials/03-partitioning-scaling/02-skew"


def test_printed_skew_checkpoints_execute_isolated(tmp_path: Path) -> None:
    package = tmp_path / "labs/partitioning/skew"
    package.mkdir(parents=True)
    for parent in (tmp_path / "labs", tmp_path / "labs/partitioning", package):
        (parent / "__init__.py").write_text("")
    env = {**os.environ, "PYTHONPATH": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"}
    for version in range(4):
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        matches = re.findall(r"<!-- checkpoint: labs/partitioning/skew/skew.py -->\s*```python\n(.*?)```", text, re.S)
        assert matches
        (package / "skew.py").write_text(matches[-1])
        result = subprocess.run([sys.executable, "-m", "labs.partitioning.skew.skew", "--partitions", "4"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
        assert "uniform" in result.stdout and "skewed" in result.stdout
    text = (GUIDES / "v3/tutorial.md").read_text()
    matches = re.findall(r"<!-- checkpoint: labs/partitioning/skew/queues.py -->\s*```python\n(.*?)```", text, re.S)
    assert matches
    (package / "queues.py").write_text(matches[-1])
    result = subprocess.run([sys.executable, "-m", "labs.partitioning.skew.queues"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0 and '"p99"' in result.stdout and '"capacity_bound"' in result.stdout
