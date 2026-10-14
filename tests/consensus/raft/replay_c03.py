from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'tutorials/06-consensus/03-raft'


def verify(version, observed):
    if version == 0:
        assert observed == dict(commit_index=1, state={'mode': 'safe'})
    elif version == 1:
        assert observed['simultaneous_candidates'] == 3 and observed['elected_term'] == 2
        assert observed['restart_vote'] == 'a' and observed['restart_exit'] == 74
    elif version == 2:
        assert observed == dict(repaired_term=3, state={'mode': 'new'})
    elif version == 3:
        assert observed == dict(old_term_commit=0, current_term_commit=2, durable_lengths=[2, 2, 2])
    elif version == 4:
        assert observed == dict(stale_candidate_votes=1, winner='b', preserved='committed')
    elif version == 5:
        assert len(observed) == 12
        assert {value['exit'] for value in observed.values()} == {71, 72, 73}
        assert observed['commit:before_replace']['commit'] == 0
        assert observed['commit:after_directory_sync']['commit'] == 1
    elif version == 6:
        assert observed['final_commit'] == 2 and observed['dropped'] >= 1
        assert observed['state'] == {'stable': 'yes', 'mode': 'successor'}
    elif version == 7:
        assert observed == dict(base=2, last=3, commit=3, snapshot={'x': '2'}, state={'x': '3'})
    elif version == 8:
        for inner in (1, 3, 4, 5, 6, 7):
            verify(inner, observed[str(inner)])
        assert observed['etcd']['engine'] == 'etcd-3.5.17'
        assert observed['etcd']['processes'] == 3
        assert observed['etcd']['recovered_value'] == 'after'
        assert observed['etcd']['minority_write_rejected']


def replay(version):
    document = (BASE / f'v{version}/tutorial.md').read_text()
    files = re.findall(r'<!-- checkpoint: ([^ ]+) -->\s*```python\n(.*?)\n```', document, re.S)
    assert len(files) == (3 if version == 8 else 2)
    with TemporaryDirectory() as folder:
        directory = Path(folder)
        for name, code in files:
            target = directory / name
            assert target.resolve().is_relative_to(directory)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code + '\n')
            if version == 8:
                assert (ROOT / name).read_text().rstrip() + '\n' == code.rstrip() + '\n', f'source drift: {name}'
        if version == 0:
            source = (directory / files[0][0]).read_text()
            assert 'persist' not in source and 'append_entries' not in source
        if version == 1:
            source = (directory / files[0][0]).read_text()
            assert 'def tick' in source and 'def persist' in source
            assert 'def append(' not in source and 'def compact(' not in source
        environment = dict(os.environ, PYTHONPATH=str(directory))
        module = 'etcd_demo' if version == 8 else ('experiments' if version in (0, 2) else 'advanced_experiments')
        result = subprocess.run([sys.executable, '-m', 'labs.consensus.raft.' + module],
                                cwd=directory, env=environment, check=True, capture_output=True,
                                text=True, timeout=120)
        observed = json.loads(result.stdout)
        verify(version, observed)
        return observed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=int, choices=range(9))
    args = parser.parse_args()
    for version in range(9) if args.version is None else [args.version]:
        print(f'v{version} replay ok: {json.dumps(replay(version), sort_keys=True)}')

