from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
TARGETS = ["unbounded.py", "bounded.py", "token_bucket.py", "balancer.py", "backpressure.py"]


def test_admission_fences_match_labs() -> None:
    for version, name in enumerate(TARGETS):
        text = (ROOT / f"tutorials/02-traffic/02-admission/v{version}/tutorial.md").read_text()
        match = re.search(rf"<!-- checkpoint: {re.escape(name)} -->\n\n```python\n(.*?)```", text, re.S)
        assert match is not None
        assert match.group(1).rstrip() == (ROOT / "labs/traffic/admission" / name).read_text().rstrip()
