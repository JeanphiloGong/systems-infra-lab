"""Replay full tutorial sources against the explicitly started A03 stack."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]


def replay(version, live=False):
    text = (ROOT / f'tutorials/09-recovery/03-failover/v{version}/tutorial.md').read_text()
    blocks = [(name, source) for name, source in re.findall(r'<!-- checkpoint: ([^ ]+) -->\s*```[^\n]+\n(.*?)\n```', text, re.S)
              if name.startswith('labs/recovery/ha/patroni_probe.py') or name.startswith('infra/a03-patroni/')]
    assert len(blocks) == 5
    with TemporaryDirectory() as folder:
        base = Path(folder)
        for name, source in blocks:
            assert source.rstrip() == (ROOT / name).read_text().rstrip()
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source + '\n')
        if live:
            result = subprocess.run(
                [sys.executable, '-I', str(base / 'labs/recovery/ha/patroni_probe.py')],
                cwd=base, check=True, capture_output=True, text=True, timeout=360,
            )
            observed = json.loads(result.stdout)
            assert observed['old'] != observed['new']
            assert observed['acknowledged_lost'] == 0
            assert observed['old_process_alive'] is True
            assert observed['old_write_rejected'] is True
            assert observed['rejoin'] == 'basebackup via Patroni reinitialize'
            return {'version': version, 'live_executed': True, 'observed': observed}
        return {'source_files': len(blocks), 'live_required': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=int, choices=[2, 3, 4], required=True)
    parser.add_argument('--live', action='store_true',
                        help='Execute the extracted probe against the dedicated running A03 stack')
    args = parser.parse_args()
    print(json.dumps(replay(args.version, args.live), sort_keys=True))
