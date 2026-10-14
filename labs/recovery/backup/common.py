from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time
import uuid
from contextlib import contextmanager

import psycopg
from psycopg.conninfo import make_conninfo, conninfo_to_dict
from psycopg import sql


DSN = os.getenv("A01_DATABASE_URL", "postgresql://a01:a01_local_only@127.0.0.1:55452/a01")
ARCHIVE = Path("/tmp/a01-wal-archive")
ARCHIVE.mkdir(parents=True, exist_ok=True)
ARCHIVE.chmod(0o777)


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN, autocommit=True, connect_timeout=3)


@contextmanager
def independent_database(prefix: str):
    admin_dsn = make_conninfo(**{k: v for k, v in conninfo_to_dict(DSN).items() if k != "dbname"}, dbname="postgres")
    name = f"a01_restore_{prefix}_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    target_dsn = make_conninfo(**{k: v for k, v in conninfo_to_dict(DSN).items() if k != "dbname"}, dbname=name)
    try:
        yield target_dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def seed(conn: psycopg.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS accounts")
    conn.execute("CREATE TABLE accounts(id integer PRIMARY KEY, balance integer NOT NULL)")
    conn.execute("INSERT INTO accounts VALUES (1,100),(2,100)")


def command(*args: str) -> None:
    subprocess.run(args, check=True, env={**os.environ, "PGPASSWORD": "a01_local_only"}, capture_output=True, text=True)


def dump(path: Path, fmt: str = "custom") -> None:
    command("pg_dump", "--dbname=" + DSN, "--format=" + fmt, "--file=" + str(path), "--table=accounts")


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("docker", *args), check=check, capture_output=True, text=True)


def create_base_backup(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    command("pg_basebackup", "--dbname=" + DSN, "-D", str(base), "-Fp", "-Xs", "--checkpoint=fast")


def wait_archive(conn: psycopg.Connection) -> tuple[Path, str]:
    cluster = conn.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
    segment = conn.execute("SELECT pg_walfile_name(pg_current_wal_insert_lsn())").fetchone()[0]
    conn.execute("SELECT pg_switch_wal()")
    archive = ARCHIVE / cluster
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if (archive / segment).exists() and (archive / segment).stat().st_size == 16777216:
            return archive, segment
        time.sleep(0.1)
    raise RuntimeError(f"WAL not archived: {segment}")


def wal_segment_names(start_segment: str, end_segment: str) -> list[str]:
    prefix = start_segment[:8]
    start_number = int(start_segment[8:], 16)
    end_number = int(end_segment[8:], 16)
    if prefix != end_segment[:8] or end_number < start_number:
        raise RuntimeError(f"WAL interval crosses timeline or wraps segment numbering: {start_segment}..{end_segment}")
    return [prefix + f"{number:016X}" for number in range(start_number, end_number + 1)]


def wait_archived_segments(conn: psycopg.Connection, start_lsn: str, end_lsn: str) -> tuple[Path, list[str]]:
    cluster = conn.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
    start_segment = conn.execute("SELECT pg_walfile_name(%s::pg_lsn)", (start_lsn,)).fetchone()[0]
    end_segment = conn.execute("SELECT pg_walfile_name(%s::pg_lsn)", (end_lsn,)).fetchone()[0]
    archive = ARCHIVE / cluster
    names = wal_segment_names(start_segment, end_segment)
    conn.execute("SELECT pg_switch_wal()")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if all((archive / name).exists() and (archive / name).stat().st_size == 16777216 for name in names):
            return archive, names
        time.sleep(0.1)
    raise RuntimeError(f"WAL interval not archived: {names}")


def recover_at(base: Path, target: str, archive: Path, *, timeout: float = 12) -> tuple[bool, str]:
    (archive / "recovery_hba.conf").write_text("local all all trust\nhost all all all trust\n")
    docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
    (base / "recovery.signal").write_text("")
    (base / "postgresql.auto.conf").write_text(f"restore_command = 'cp /archive/%f %p'\nrecovery_target_time = '{target}'\n")
    name = "a01-recovery-" + uuid.uuid4().hex[:8]
    started = docker("run", "-d", "--name", name, "--network", "infra_default", "-v", f"{base}:/var/lib/postgresql/data", "-v", f"{archive}:/archive", "postgres:16.4", "postgres", "-D", "/var/lib/postgresql/data", "-c", "hba_file=/archive/recovery_hba.conf", check=False)
    if started.returncode != 0:
        return False, started.stderr
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = docker("exec", name, "pg_isready", "-U", "a01", check=False)
        if result.returncode == 0:
            result = docker("exec", name, "psql", "-U", "a01", "-d", "a01", "-At", "-c", "SELECT string_agg(id::text || ':' || balance::text, ',' ORDER BY id) FROM accounts WHERE pg_get_wal_replay_pause_state() = 'paused'", check=False)
            if result.returncode == 0 and result.stdout.strip():
                docker("rm", "-f", name, check=False)
                docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
                return True, result.stdout.strip()
        time.sleep(0.25)
    logs = docker("logs", name, check=False).stderr
    docker("rm", "-f", name, check=False)
    docker("run", "--rm", "-v", f"{base}:/x", "postgres:16.4", "chmod", "-R", "a+rwX", "/x")
    return False, logs
