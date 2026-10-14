"""A02 executable checkpoints; each crash is recovered in a fresh process."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from labs.recovery.checkpoint.store import Store


MODULE = 'labs.recovery.checkpoint.experiments'


def fill(store, start, end):
    for position in range(start, end + 1):
        amount = position % 101
        store.commit(position, {'alice': 100 - amount, 'bob': 100 + amount})


def fresh_recover(path):
    result = subprocess.run([sys.executable, '-m', MODULE, 'recover', str(path)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def snapshot_tail():
    with TemporaryDirectory() as folder:
        path = Path(folder)
        store = Store(path)
        fill(store, 1, 100)
        store.snapshot(100)
        assert len(list(path.glob('[0-9]*.wal'))) == 100
        fill(store, 101, 105)
        expected_bytes = sum((path / f'{i:020d}.wal').stat().st_size for i in range(101, 106))
        state, position, read_bytes = fresh_recover(path)
        assert state == {'alice': 96, 'bob': 104} and position == 105
        assert read_bytes == expected_bytes
        assert read_bytes < sum(p.stat().st_size for p in path.glob('[0-9]*.wal'))
        return dict(position=position, tail_transactions=5, bytes_read=read_bytes, expected_bytes=expected_bytes)


def publication():
    observed = {}
    faults = [('snapshot', 'before_replace', 71), ('snapshot', 'after_replace', 72),
              ('snapshot', 'after_directory_sync', 73), ('publish', 'before_replace', 71),
              ('publish', 'after_replace', 72), ('publish', 'after_directory_sync', 73),
              ('publish', 'after_first_log_delete', 74)]
    for operation, fault, code in faults:
        with TemporaryDirectory() as folder:
            path, store = Path(folder), Store(Path(folder))
            fill(store, 1, 5)
            if operation == 'publish':
                store.snapshot(5)
            process = subprocess.run([sys.executable, '-m', MODULE, 'crash', folder, operation, fault], timeout=10)
            assert process.returncode == code
            state, position, _ = fresh_recover(path)
            assert (state, position) == ({'alice': 95, 'bob': 105}, 5)
            observed[operation + ':' + fault] = code
    return observed


def generations():
    with TemporaryDirectory() as folder:
        path, store = Path(folder), Store(Path(folder))
        fill(store, 1, 10)
        store.snapshot(10)
        fill(store, 11, 20)
        store.snapshot(20)
        fill(store, 21, 25)
        store.publish([10, 20])
        latest = store.snapshot_path(20)
        intact = latest.read_bytes()
        latest.write_bytes(b'corrupt')
        result = fresh_recover(path)
        expected_bytes = sum((path / f'{i:020d}.wal').stat().st_size for i in range(11, 26))
        assert result == [{'alice': 75, 'bob': 125}, 25, expected_bytes]
        assert fresh_recover(path) == result
        missing = path / f'{11:020d}.wal'
        original = missing.read_bytes()
        missing.unlink()
        try:
            store.recover()
        except ValueError as error:
            assert 'missing' in str(error)
        else:
            raise AssertionError('fallback accepted missing required log')
        missing.write_bytes(original)
        older = store.snapshot_path(10)
        original_old = older.read_bytes()
        older.write_bytes(b'corrupt')
        try:
            store.recover()
        except ValueError as error:
            assert 'no usable recovery base' in str(error)
        else:
            raise AssertionError('corrupt snapshots silently reset state')
        older.write_bytes(original_old)
        latest.write_bytes(intact)
        fill(store, 26, 30)
        store.snapshot(30)
        store.publish([10, 20, 30])
        assert not older.exists()
        assert [int(p.stem) for p in sorted(path.glob('[0-9]*.wal'))] == list(range(21, 31))
        store.snapshot_path(30).write_bytes(b'corrupt')
        assert fresh_recover(path)[:2] == [{'alice': 70, 'bob': 130}, 30]
        store.commit(31, {'alice': 69, 'bob': 131})
        assert fresh_recover(path)[:2] == [{'alice': 69, 'bob': 131}, 31]

    exits = []
    for fault, code in [('before_replace', 71), ('after_replace', 72),
                        ('after_directory_sync', 73), ('after_first_log_delete', 74),
                        ('after_first_snapshot_delete', 75)]:
        with TemporaryDirectory() as folder:
            path, store = Path(folder), Store(Path(folder))
            for low, high in [(1, 10), (11, 20), (21, 30)]:
                fill(store, low, high)
                store.snapshot(high)
            process = subprocess.run([sys.executable, '-m', MODULE, 'crash', folder, 'rotate', fault], timeout=10)
            assert process.returncode == code
            assert fresh_recover(path)[:2] == [{'alice': 70, 'bob': 130}, 30]
            store.snapshot_path(30).write_bytes(b'corrupt')
            assert fresh_recover(path)[:2] == [{'alice': 70, 'bob': 130}, 30]
            exits.append(code)
    return dict(fallback_transactions=15, rotation_exits=exits, continued_position=31)


def main():
    arguments = sys.argv[1:]
    if arguments[0] == 'recover':
        print(json.dumps(Store(Path(arguments[1])).recover()))
    elif arguments[0] == 'crash':
        store = Store(Path(arguments[1]))
        operation, fault = arguments[2:]
        if operation == 'snapshot':
            store.snapshot(5, fault=fault)
        else:
            store.publish([10, 20, 30] if operation == 'rotate' else [5], fault=fault)
    else:
        functions = {'1': snapshot_tail, '2': publication, '3': generations}
        print(json.dumps(functions[arguments[0]]()))


if __name__ == '__main__':
    main()
