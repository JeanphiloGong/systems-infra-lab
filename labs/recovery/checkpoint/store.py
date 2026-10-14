"""Paused single writer: CRC snapshots, retained generations and immutable WAL."""
from __future__ import annotations

import os
from pathlib import Path

from labs.recovery.checkpoint.baseline import commit as commit_segment
from labs.recovery.checkpoint.baseline import replay
from labs.storage.wal.framing import decode, encode


INITIAL = {"alice": 100, "bob": 100}


def valid_state(state):
    return (isinstance(state, dict) and set(state) == set(INITIAL)
            and all(type(value) is int and value >= 0 for value in state.values())
            and sum(state.values()) == 200)


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def sync_directory(self):
        descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def atomic(self, path, record, fault=None):
        temporary = path.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            stream.write(encode(record))
            stream.flush()
            os.fsync(stream.fileno())
        if fault == 'before_replace':
            os._exit(71)
        os.replace(temporary, path)
        if fault == 'after_replace':
            os._exit(72)
        self.sync_directory()
        if fault == 'after_directory_sync':
            os._exit(73)

    def record(self, path):
        rows, _, incomplete = decode(path.read_bytes())
        if incomplete or len(rows) != 1:
            raise ValueError('invalid metadata frame')
        return rows[0]

    def manifest(self):
        path = self.directory / 'manifest.wal'
        if not path.exists():
            return None
        record = self.record(path)
        positions = record.get('snapshots')
        required = record.get('required_through')
        if (record.get('format') != 1 or not isinstance(positions, list) or not positions
                or any(type(n) is not int or n < 0 for n in positions)
                or positions != sorted(set(positions)) or type(required) is not int
                or required < positions[-1]):
            raise ValueError('invalid manifest')
        return record

    def snapshot_path(self, position):
        return self.directory / f'snapshot-{position:020d}.wal'

    def read_snapshot(self, position):
        record = self.record(self.snapshot_path(position))
        if record.get('format') != 1 or record.get('position') != position or not valid_state(record.get('state')):
            raise ValueError('invalid snapshot')
        return record['state']

    def tail(self, state, position, required):
        byte_count = 0
        for path in sorted(self.directory.glob('[0-9]*.wal')):
            try:
                number = int(path.stem)
            except ValueError:
                raise ValueError('invalid segment name') from None
            if number <= position:
                continue
            if path.name != f'{position + 1:020d}.wal':
                raise ValueError('required log segment is missing')
            data = path.read_bytes()
            rows, _, incomplete = decode(data)
            if (incomplete or len(rows) != 3
                    or any(row.get('tx') != str(number) for row in rows)
                    or [row.get('kind') for row in rows] != ['set', 'set', 'commit']
                    or {row.get('key') for row in rows[:2]} != set(INITIAL)):
                raise ValueError('invalid published transaction')
            state, _ = replay(rows)
            if not valid_state(state):
                raise ValueError('invalid balance')
            position = number
            byte_count += len(data)
        if position < required:
            raise ValueError('required log segment is missing')
        return dict(state), position, byte_count

    def recover(self):
        manifest = self.manifest()
        if manifest is None:
            return self.tail(dict(INITIAL), 0, 0)
        failures = []
        for position in reversed(manifest['snapshots']):
            try:
                state = self.read_snapshot(position)
                return self.tail(state, position, manifest['required_through'])
            except (ValueError, OSError) as error:
                failures.append(str(error))
        raise ValueError('no usable recovery base: ' + '; '.join(failures))

    def commit(self, position, state):
        if type(position) is not int or not valid_state(state):
            raise ValueError('invalid committed state')
        _, last, _ = self.recover()
        if position != last + 1:
            raise ValueError('commit position must be next')
        commit_segment(self.directory, position, state)

    def snapshot(self, position, *, fault=None):
        state, recovered, _ = self.recover()
        if type(position) is not int or position != recovered:
            raise ValueError('snapshot position must equal recovered prefix')
        self.atomic(self.snapshot_path(position), dict(format=1, position=position, state=state), fault)
        previous = self.manifest()
        positions = sorted(set((previous['snapshots'] if previous else []) + [position]))
        # Publishing this pointer makes v1 recovery use the snapshot; logs stay intact.
        self.atomic(self.directory / 'manifest.wal', dict(format=1, snapshots=positions, required_through=position))

    def publish(self, positions, *, fault=None, keep=2):
        if (type(keep) is not int or keep < 1 or not positions
                or any(type(n) is not int or n < 0 for n in positions)
                or positions != sorted(set(positions))):
            raise ValueError('invalid retained generations')
        selected = positions[-keep:]
        current, tip, _ = self.recover()
        # Every retained base must independently recover the SAME full prefix.
        for position in selected:
            state = self.read_snapshot(position)
            result, end, _ = self.tail(state, position, tip)
            if end != tip or result != current:
                raise ValueError('snapshot does not match durable history')
        self.atomic(self.directory / 'manifest.wal', dict(format=1, snapshots=selected, required_through=tip), fault)
        for path in sorted(self.directory.glob('[0-9]*.wal')):
            if int(path.stem) <= selected[0]:
                path.unlink()
                if fault == 'after_first_log_delete':
                    os._exit(74)
        self.sync_directory()
        for path in sorted(self.directory.glob('snapshot-*.wal')):
            if path not in [self.snapshot_path(n) for n in selected]:
                path.unlink()
                if fault == 'after_first_snapshot_delete':
                    os._exit(75)
        self.sync_directory()
