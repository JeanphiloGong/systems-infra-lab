"""Extract every tutorial dependency, then execute solely from that directory."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/08-dataflows/04-analytics"


def extract(version, directory):
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\s*```(?:python|yaml)\n(.*?)\n```", text, re.S)
    expected = {f"labs/dataflows/analytics/v{version}.py",
                "labs/dataflows/analytics/pg.py", "labs/dataflows/analytics/compose.yaml"}
    assert {path for path, _ in blocks} == expected and len(blocks) == 3
    for path, code in blocks:
        assert code + "\n" == (ROOT / path).read_text()
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code + "\n")


@pytest.mark.parametrize("version", range(4))
def test_complete_sources(version, tmp_path):
    extract(version, tmp_path)


@pytest.mark.postgres
@pytest.mark.parametrize("version", range(4))
def test_live_extracted_checkpoint(version, tmp_path):
    if os.getenv("E04_LIVE") != "1":
        pytest.skip("E04_LIVE=1 requires the dedicated systems-e04 Compose stack")
    extract(version, tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", f"labs.dataflows.analytics.v{version}"],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True, text=True, timeout=240,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0:
        assert output["batches"] == [["customers", "b1", 100, 100], ["orders", "b1", 100, 100]]
        assert output["report"] == [["C1", 10], ["C2", 20], ["C3", 30]]
    elif version == 1:
        assert output["corrected"] == output["replayed"] == [["C2-corrected", 55], ["C3", 30]]
        assert len(output["batches"]) == 4
    elif version == 2:
        assert sum(s["transferred"] for s in output["full"]) == 200
        assert sum(s["transferred"] for s in output["selective"]["sources"]) == 6
        assert sum(s["scanned"] for s in output["selective"]["sources"]) == 200
        assert len(output["selective"]["rows"]) == 3
    else:
        assert output["orphan_orders"] == [[1]]
        assert output["outage_sqlstate"] == "08001"
        assert output["connector_config_preserved"] is True
        assert output["warehouse_remote_rows_per_read"] == 0
        assert output["local_scan"] == 103
        assert output["caught_up_cutoffs"][-1] == ["orders", "b2", 101, 1]
