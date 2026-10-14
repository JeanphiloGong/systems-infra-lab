import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from labs.storage.lsm.manifest import load, publish
from labs.storage.lsm.tombstones import TombstoneStore


@pytest.mark.parametrize("crash,status,expected", [("before_publish",71,"old"),("after_publish",72,"new")])
def test_real_process_exit_then_fresh_reader(tmp_path: Path, crash: str, status: int, expected: str) -> None:
    old = TombstoneStore.create(tmp_path / "old.sst", {"k":"old","stable":"yes"}).path
    new = TombstoneStore.create(tmp_path / "new.sst", {"k":"new"}).path
    publish(tmp_path, [old])
    command = [sys.executable, "-m", "labs.storage.lsm.manifest", str(tmp_path)]
    env = {**os.environ, "PYTHONPATH": str(Path.cwd())}
    dead = subprocess.run(command + ["--publish", "--crash", crash], env=env, capture_output=True, text=True, timeout=5)
    assert dead.returncode == status, dead.stderr
    read = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
    assert read.returncode == 0, read.stderr
    assert json.loads(read.stdout) == {"k":expected,"stable":"yes"}
    assert json.loads((tmp_path/"MANIFEST").read_text()) == (["old.sst"] if status==71 else ["new.sst","old.sst"])


@pytest.mark.parametrize("names", [None, {}, [3], [""], ["."], [".."], ["../out.sst"], ["/out.sst"], ["old.sst","old.sst"], ["missing.sst"], ["MANIFEST"]])
def test_load_rejects_invalid_collection(tmp_path: Path, names: object) -> None:
    TombstoneStore.create(tmp_path/"old.sst", {"k":"old"})
    (tmp_path/"MANIFEST").write_text(json.dumps(names))
    with pytest.raises(ValueError):
        load(tmp_path)


def test_publish_rejects_duplicate_missing_outside_and_symlink(tmp_path: Path) -> None:
    old = TombstoneStore.create(tmp_path/"old.sst", {"k":"old"}).path
    publish(tmp_path,[old])
    before = (tmp_path/"MANIFEST").read_bytes()
    link = tmp_path/"link.sst"
    link.symlink_to(old)
    for files in ([old,old], [tmp_path/"missing.sst"], [tmp_path/"../old.sst"], [link]):
        with pytest.raises(ValueError):
            publish(tmp_path,files)
        assert (tmp_path/"MANIFEST").read_bytes()==before
    assert load(tmp_path).get("k")=="old"


def test_empty_manifest_and_bad_json(tmp_path: Path) -> None:
    publish(tmp_path, [])
    assert load(tmp_path).get("k") is None
    (tmp_path/"MANIFEST").write_text("{broken")
    with pytest.raises(ValueError):
        load(tmp_path)
