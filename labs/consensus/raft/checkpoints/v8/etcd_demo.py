from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from .advanced_experiments import run


def port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        return connection.getsockname()[1]


def post(endpoint, route, body):
    request = urllib.request.Request(endpoint + route, json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
    # Local experiment must not route localhost through a user's HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=2) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result


def wait_until(check, seconds=20):
    deadline = time.monotonic() + seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, urllib.error.URLError, RuntimeError) as error:
            last_error = error
        time.sleep(0.1)
    raise RuntimeError(f'cluster condition timed out: {last_error}')


def run_etcd():
    binary = os.environ.get('ETCD_BINARY')
    if not binary or not Path(binary).is_file():
        raise RuntimeError('set ETCD_BINARY to an installed etcd v3.5.17 executable')
    version = subprocess.check_output([binary, '--version'], text=True, timeout=5)
    if 'etcd Version: 3.5.17' not in version:
        raise RuntimeError('this experiment is verified with etcd 3.5.17')
    with TemporaryDirectory() as folder:
        directory = Path(folder)
        clients = ['http://127.0.0.1:' + str(port()) for _ in range(3)]
        peers = ['http://127.0.0.1:' + str(port()) for _ in range(3)]
        initial = ','.join(f'n{i}={peers[i]}' for i in range(3))
        processes, streams = {}, []

        def start(index):
            stream = (directory / f'n{index}.log').open('a')
            streams.append(stream)
            processes[index] = subprocess.Popen([
                binary, '--name', f'n{index}', '--data-dir', str(directory / f'n{index}'),
                '--listen-client-urls', clients[index], '--advertise-client-urls', clients[index],
                '--listen-peer-urls', peers[index], '--initial-advertise-peer-urls', peers[index],
                '--initial-cluster', initial, '--initial-cluster-token', 'c03-local',
                '--initial-cluster-state', 'new', '--heartbeat-interval', '100',
                '--election-timeout', '1000', '--log-level', 'error',
            ], stdout=stream, stderr=subprocess.STDOUT)

        def status(index):
            return post(clients[index], '/v3/maintenance/status', {})

        key = base64.b64encode(b'c03/mode').decode()

        def put(index, value):
            return post(clients[index], '/v3/kv/put',
                        dict(key=key, value=base64.b64encode(value.encode()).decode()))

        def read(index):
            result = post(clients[index], '/v3/kv/range', dict(key=key))
            return base64.b64decode(result['kvs'][0]['value']).decode()

        try:
            for index in range(3):
                start(index)
            for index in range(3):
                wait_until(lambda index=index: status(index).get('leader', '0') != '0')
            first = status(0)
            leader_id = first['leader']
            leader = next(i for i in range(3) if status(i)['header']['member_id'] == leader_id)
            put(leader, 'before')
            for index in range(3):
                assert wait_until(lambda index=index: read(index) == 'before')
            processes[leader].kill()
            processes[leader].wait(timeout=5)
            survivors = [i for i in range(3) if i != leader]
            successor = wait_until(lambda: status(survivors[0]).get('leader') not in (None, '0', leader_id))
            assert successor
            put(survivors[0], 'after')
            assert read(survivors[1]) == 'after'
            start(leader)
            assert wait_until(lambda: read(leader) == 'after')
            # Stop two members and demonstrate that one node cannot acknowledge a write.
            for index in survivors:
                processes[index].kill()
                processes[index].wait(timeout=5)
            try:
                put(leader, 'without-quorum')
            except (OSError, urllib.error.URLError, RuntimeError):
                minority_rejected = True
            else:
                raise AssertionError('minority unexpectedly acknowledged write')
            return dict(engine='etcd-3.5.17', processes=3, killed_leader=leader,
                        recovered_value='after', minority_write_rejected=minority_rejected)
        finally:
            for process in processes.values():
                if process.poll() is None:
                    process.terminate()
            for process in processes.values():
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for stream in streams:
                stream.close()


def main():
    evidence = {str(version): run(version) for version in (1, 3, 4, 5, 6, 7)}
    evidence['etcd'] = run_etcd()
    print(json.dumps(evidence, sort_keys=True))


if __name__ == '__main__':
    main()
