from pathlib import Path
import re
import subprocess
import sys

import pytest


GUIDES = Path(__file__).resolve().parents[3] / "tutorials/02-traffic/03-retry"
TARGETS = {
    0: "labs/traffic/resilience/v0.py",
    1: "labs/traffic/resilience/v1.py",
    2: "labs/traffic/resilience/v2.py",
    3: "labs/traffic/resilience/breaker.py",
    4: "labs/traffic/resilience/budget.py",
}


def source(version: int) -> str:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    marker = f"<!-- checkpoint: {TARGETS[version]} -->"
    match = re.search(re.escape(marker) + r"\s*\n\`\`\`python\n(.*?)\`\`\`", text, re.S)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize("version", range(5))
def test_exact_checkpoint_executes(version: int, tmp_path: Path) -> None:
    target = tmp_path / f"v{version}.py"
    target.write_text(source(version))
    result = subprocess.run(
        [sys.executable, str(target)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr


def test_v0_records_immediate_retry_amplification(tmp_path: Path) -> None:
    target = tmp_path / "v0.py"
    target.write_text(source(0) + "\nprint(call(lambda: 'ok', 3))\n")
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "('ok', 1)" in result.stdout


def test_v1_and_v2_boundaries_are_distinct() -> None:
    assert "class PermanentError" in source(1)
    assert "random" not in source(1)
    assert "random" in source(2)
    assert "clock() + delay >= expires" in source(2)


def test_v1_deadline_uses_elapsed_clock(tmp_path: Path) -> None:
    target = tmp_path / "v1.py"
    target.write_text(
        source(1)
        + "\n"
        + "ticks = iter([0.0, 0.0, 1.1]); "
        + "op = lambda: (_ for _ in ()).throw(RetryableError()); "
        + "call(op, max_attempts=3, deadline=1.0, clock=lambda: next(ticks))\n"
    )
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "TimeoutError" in result.stderr


def test_v3_breaker_probe_is_bounded(tmp_path: Path) -> None:
    target = tmp_path / "breaker.py"
    target.write_text(
        source(3)
        + "\n"
        + "b = CircuitBreaker(1); b.failure(); b.recover(); "
        + "assert b.allow(); assert not b.allow(); b.success(); "
        + "assert b.state is State.CLOSED\n"
    )
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_v4_budget_captures_multiplication_and_cap(tmp_path: Path) -> None:
    target = tmp_path / "budget.py"
    target.write_text(
        source(4)
        + "\nassert amplification(None) == 27\n"
        + "assert amplification(10) == 10\n"
    )
    result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("version,name", [(2, "v2.py"), (4, "budget.py")])
def test_reopened_regressions_from_printed_checks(version: int, name: str, tmp_path: Path) -> None:
    import os

    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    code = source(version)
    root = GUIDES.parents[2]
    assert code.rstrip() == (root / TARGETS[version]).read_text().rstrip()
    (tmp_path / name).write_text(code)
    check = re.search(r"<!-- check: check_v\d.py -->\s*```python\n(.*?)```", text, re.S)
    assert check is not None
    script = tmp_path / "check.py"
    script.write_text(check.group(1))
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(tmp_path)},
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
