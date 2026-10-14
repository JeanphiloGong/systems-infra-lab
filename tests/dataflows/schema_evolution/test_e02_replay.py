from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/08-dataflows/02-schema-evolution"
TARGETS = {version: ["common.py", f"v{version}.py"] for version in range(4)}


def extract(version: int, destination: Path) -> Path:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    expected = [f"labs/dataflows/schema_evolution/{name}" for name in TARGETS[version]]
    assert [path for path, _ in blocks] == expected
    package = destination / "labs/dataflows/schema_evolution"
    package.mkdir(parents=True)
    for path, code in blocks:
        source = ROOT / path
        assert code.rstrip() == source.read_text().rstrip(), path
        (package / Path(path).name).write_text(code + "\n")
    (package / "__init__.py").write_text("")
    return package / f"v{version}.py"


@pytest.mark.parametrize("version", range(4))
def test_real_postgres_schema_evolution(version: int, tmp_path: Path) -> None:
    assert os.environ.get("E02_DATABASE_URL") == "postgresql://e02:e02_local_only@127.0.0.1:55451/e02"
    script = extract(version, tmp_path)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path / "labs/dataflows/schema_evolution")}, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0:
        assert output["rename_breaks_old_client"]
        assert output["old_write_sqlstate"] == output["populated_ddl_sqlstate"] == "23502"
    elif version == 1:
        assert output["additive"] and output["dual_write"]
        assert output["fallback"] == "Ada"
        assert output["old_insert_new_read"] == output["old_update_new_read"] == "Grace"
        assert output["new_write_old_read"] == output["naive_stale"] == "Ada Lovelace"
        assert output["new_insert_old_read"] == "Linus"
        assert output["event_matrix"]["new->old"] == "rejected"
        assert len(output["event_matrix"]) == 6
    elif version == 2:
        assert output["resumable"] and output["process_failure_recovered"] and output["uncommitted_batch_rolled_back"] and output["fresh_repeat_zero_work"]
        assert output["first_batch"] == 2 and output["checkpoint"] == 2 and output["resume_batch"] == 2 and output["remaining"] == 0 and output["repeat_batch"] == 0
        assert output["protected"] == "Protected by new client"
        repeated = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                                  env={**os.environ, "PYTHONPATH": str(script.parent)},
                                  capture_output=True, text=True, timeout=60)
        assert repeated.returncode == 0, repeated.stderr
        assert json.loads(repeated.stdout) == output
    else:
        assert output["not_null"] and output["old_client_rejected"] and output["cleanup_complete"]
        assert output["write_rejections"] == ["23502"] * 3
        assert output["event_rejections"] == ["rejected"] * 4
        assert output["final_event"] == "Linus" and output["new_rows"] == 3
    import psycopg
    with psycopg.connect(os.environ["E02_DATABASE_URL"]) as conn:
        assert conn.execute("SELECT to_regclass('profiles'), to_regclass('schema_backfill_checkpoint'), to_regclass('migration_clients')").fetchone() == (None, None, None)


def test_event_contract_without_database(tmp_path: Path) -> None:
    transition = extract(1, tmp_path / "transition")
    final = extract(3, tmp_path / "final")
    env = {key: value for key, value in os.environ.items() if key != "E02_DATABASE_URL"}
    for script, expression in (
        (transition, "assert m['event_matrix']()['old->new'] == 'Ada'"),
        (final, "assert m['read_event']({'full_name':'Grace'}) == 'Grace'\ntry: m['read_event']({'name':'Grace'})\nexcept KeyError: pass\nelse: raise AssertionError('legacy event accepted')"),
    ):
        code = "import runpy\nm=runpy.run_path(" + repr(str(script)) + ")\n" + expression
        result = subprocess.run([sys.executable, "-c", code], cwd=script.parent,
                                env={**env, "PYTHONPATH": str(script.parent)},
                                text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr


def test_all_chapters_have_exact_python_fences() -> None:
    for version, names in TARGETS.items():
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        paths = [Path(path).name for path, _ in re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)]
        assert paths == names
