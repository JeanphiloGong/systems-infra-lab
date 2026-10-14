from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import importlib.util

import pytest


ROOT = Path(__file__).resolve().parents[3]
GUIDES = ROOT / "tutorials/08-dataflows/01-cdc"
TARGETS = {version: ["common.py", f"v{version}.py"] for version in range(5)}


def lsn_number(position: str) -> int:
    high, low = position.split("/")
    return (int(high, 16) << 32) + int(low, 16)


def extract(version: int, destination: Path) -> Path:
    text = (GUIDES / f"v{version}/tutorial.md").read_text()
    blocks = re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)
    expected = [f"labs/dataflows/cdc/{name}" for name in TARGETS[version]]
    assert [path for path, _ in blocks] == expected
    package = destination / "labs/dataflows/cdc"
    package.mkdir(parents=True)
    for path, code in blocks:
        source = ROOT / path
        assert code.rstrip() == source.read_text().rstrip(), path
        (package / Path(path).name).write_text(code + "\n")
    (package / "__init__.py").write_text("")
    return package / f"v{version}.py"


@pytest.mark.parametrize("version", range(5))
def test_real_postgres_cdc_replay(version: int, tmp_path: Path) -> None:
    assert os.environ.get("E01_DATABASE_URL") == "postgresql://e01:e01_local_only@127.0.0.1:55450/e01", "Start infra/e01.compose.yaml and set E01_DATABASE_URL"
    script = extract(version, tmp_path)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(tmp_path / "labs/dataflows/cdc")}, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    if version == 0:
        assert output["inconsistent"]
    elif version == 1:
        assert output["contains_insert"] and output["contains_update"] and output["contains_delete"] and output["event_count"] >= 5
        positions = [lsn_number(value) for value in output["source_positions"]]
        assert positions == sorted(positions) and positions[0] > 0
        assert len(set(output["data_positions"])) == output["data_event_count"] == 3
        assert output["versions"] == list(range(1, output["event_count"] + 1))
        assert output["operations"] == ["INSERT", "UPDATE", "DELETE"]
        assert all(int(xid) > 0 for xid in output["xids"])
        assert output["event_keys"] == [f"{xid}:{position}:{operation}" for xid, position, operation in zip(output["xids"], output["data_positions"], output["operations"], strict=True)]
    elif version == 2:
        assert output["matches_source"]
        assert output["projection"] == {"1": "paid in full; customer's order", "2": "after-snapshot", "4": "new incarnation"}
        assert output["operations"] == ["UPDATE", "DELETE", "DELETE", "INSERT", "INSERT"]
        assert 0 < lsn_number(output["snapshot_cursor"]) < lsn_number(output["last_source_position"])
    elif version == 3:
        assert output["projection"] == [[1, "paid in full; customer's order"], [2, "after-snapshot"], [4, "new incarnation"]] and output["checkpoints"] == 1 and output["replay_safe"]
        assert lsn_number(output["source_position"]) > 0
        assert output["event_key"].endswith(f":{output['source_position']}:TRANSACTION")
        assert output["version"] == 7
        assert output["crash_before_commit_rolled_back"] and output["crash_after_commit_replayed"]
        assert output["fresh_processes"] == 3 and output["source_ack_after_commit"]
    else:
        assert output["events_replayed"] > 20000 and output["confirmed_advanced"] and output["retained_bytes"] > 0


def test_all_chapters_have_exact_python_fences() -> None:
    for version, names in TARGETS.items():
        text = (GUIDES / f"v{version}/tutorial.md").read_text()
        paths = [Path(path).name for path, _ in re.findall(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```", text, re.S)]
        assert paths == names


def test_decoder_preserves_real_postgres_values() -> None:
    spec = importlib.util.spec_from_file_location("e01_common", ROOT / "labs/dataflows/cdc/common.py")
    common = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = common
    spec.loader.exec_module(common)
    values = ["paid in full", "customer's order", "a\\b", "line\nbreak", "", None]
    with common.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute("CREATE TABLE orders(id int PRIMARY KEY,value text)")
        slot = "e01_decoder"
        conn.execute("SELECT * FROM pg_create_logical_replication_slot(%s,'test_decoding')", (slot,))
        try:
            for identifier, value in enumerate(values):
                conn.execute("INSERT INTO orders VALUES (%s,%s)", (identifier, value))
            events = common.read_events(conn, slot)
            assert [common.order_change(event) for event in events if event.operation == "INSERT"] == list(enumerate(values))
            bad = common.Event("bad", 1, "0/1", 1, "UPDATE", "table public.orders: UPDATE: unexpected layout")
            with pytest.raises(ValueError, match="unsupported"):
                common.order_change(bad)
        finally:
            conn.execute("SELECT pg_drop_replication_slot(%s)", (slot,))


def test_snapshot_cut_blocks_writer_then_captures_post_cut_change() -> None:
    spec = importlib.util.spec_from_file_location("e01_cut_common", ROOT / "labs/dataflows/cdc/common.py")
    common = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = common
    spec.loader.exec_module(common)
    with common.connect() as reader, common.connect() as writer:
        reader.execute("DROP TABLE IF EXISTS orders")
        reader.execute("CREATE TABLE orders(id int PRIMARY KEY,value text)")
        slot = "e01_cut"
        reader.execute("SELECT * FROM pg_create_logical_replication_slot(%s,'test_decoding')", (slot,))
        try:
            writer.execute("INSERT INTO orders VALUES (1,'before')")
            with reader.transaction():
                snapshot, cursor = common.snapshot_cut(reader, slot)
                assert snapshot == [(1, "before")]
                writer.execute("SET lock_timeout='100ms'")
                with pytest.raises(common.psycopg.errors.LockNotAvailable):
                    writer.execute("UPDATE orders SET value='after' WHERE id=1")
            writer.execute("UPDATE orders SET value='after' WHERE id=1")
            changes = common.read_events(reader, slot)
            assert [common.order_change(event) for event in changes if event.operation != "TRANSACTION"] == [(1, "after")]
            assert lsn_number(changes[-1].source_position) > lsn_number(cursor)
        finally:
            reader.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
