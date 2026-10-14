"""Run against the dedicated infra/a03-patroni stack; mutate only its two nodes."""
import json
import subprocess
import time
import urllib.request

import psycopg

NETWORK = 'systems-a03-patroni_default'
PORTS = {'p1': 55461, 'p2': 55462}
REST = {'p1': 18081, 'p2': 18082}


def docker(*args):
    return subprocess.run(['docker', *args], text=True, capture_output=True, timeout=30)


def api(node, path='/patroni', payload=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f'http://127.0.0.1:{REST[node]}' + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=5) as response:
        body = response.read().decode()
    return json.loads(body) if path == '/patroni' else body


def wait(check, seconds=90):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (OSError, psycopg.Error) as exc:
            last = exc
        time.sleep(0.25)
    raise TimeoutError(str(last))


def sql(node, query, params=None):
    with psycopg.connect(host='127.0.0.1', port=PORTS[node], user='postgres',
                         password='postgres', dbname='postgres',
                         autocommit=True, connect_timeout=2) as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchall() if cursor.description else []


def run():
    old = next(node for node in PORTS if api(node)['role'] == 'primary')
    new = next(node for node in PORTS if node != old)
    sql(old, 'CREATE TABLE IF NOT EXISTS a03_live(id text PRIMARY KEY, value text)')
    key = str(time.time_ns())
    sql(old, 'INSERT INTO a03_live VALUES (%s,%s)', (key, 'acknowledged'))
    wait(lambda: sql(new, 'SELECT value FROM a03_live WHERE id=%s', (key,)) == [('acknowledged',)])
    # Async replication is deliberately caught up before failure; RPO zero is observed, not guaranteed.
    identifier = f'systems-a03-patroni-{old}-1'
    started = time.monotonic()
    disconnected = False
    retries = 0
    try:
        result = docker('network', 'disconnect', NETWORK, identifier)
        result.check_returncode()
        disconnected = True
        while True:
            retries += 1
            try:
                if api(new)['role'] == 'primary':
                    sql(new, 'INSERT INTO a03_live VALUES (%s,%s)', (key + '-new', 'after'))
                    break
            except (OSError, psycopg.Error):
                pass
            if time.monotonic() - started > 90:
                raise TimeoutError('automatic promotion')
            time.sleep(0.25)
        rto = time.monotonic() - started
        probe = docker('exec', '-e', 'PGPASSWORD=postgres', identifier,
                       'psql', '-h', '127.0.0.1', '-U', 'postgres', '-c',
                       "CREATE TABLE a03_forbidden(id int)")
        assert probe.returncode != 0, 'isolated old primary remains writable'
        assert docker('inspect', '-f', '{{.State.Running}}', identifier).stdout.strip() == 'true'
        retained = sql(new, 'SELECT value FROM a03_live WHERE id=%s', (key,))
        assert retained == [('acknowledged',)]
        docker('network', 'connect', '--alias', old, NETWORK, identifier).check_returncode()
        disconnected = False
        docker('restart', '-t', '5', identifier).check_returncode()
        wait(lambda: api(old))
        # Explicit rebuild is used instead of assuming divergent timelines can follow directly.
        api(old, '/reinitialize', {'force': True})
        wait(lambda: sql(old, 'SELECT pg_is_in_recovery()') == [(True,)])
        wait(lambda: sql(old, 'SELECT value FROM a03_live WHERE id=%s', (key + '-new',)) == [('after',)])
        switched = time.monotonic()
        api(new, '/switchover', {'leader': new, 'candidate': old})
        wait(lambda: api(old)['role'] == 'primary')
        sql(old, 'INSERT INTO a03_live VALUES (%s,%s)', (key + '-return', 'returned'))
        return dict(old=old, new=new, rto_seconds=round(rto, 3), acknowledged_lost=0,
                    client_attempts=retries, old_process_alive=True, old_write_rejected=True,
                    rejoin='basebackup via Patroni reinitialize',
                    cutback_seconds=round(time.monotonic() - switched, 3))
    finally:
        if disconnected:
            docker('network', 'connect', '--alias', old, NETWORK, identifier)


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))

