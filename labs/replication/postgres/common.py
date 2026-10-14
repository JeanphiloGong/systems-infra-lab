from __future__ import annotations

import time
from collections.abc import Callable

import psycopg


def connect(node: str) -> psycopg.Connection:
    ports = {"primary": 55440, "standby": 55441, "subscriber": 55442}
    return psycopg.connect(host="127.0.0.1", port=ports[node], dbname="r04", user="r04", password="r04_local_only", autocommit=True, connect_timeout=3)


def wait_for(check: Callable[[], bool], label: str, seconds: float = 60) -> None:
    expires = time.monotonic() + seconds
    while time.monotonic() < expires:
        if check():
            return
        time.sleep(0.05)
    raise TimeoutError(label)


def scalar(conn: psycopg.Connection, query: str) -> object:
    row = conn.execute(query).fetchone()
    return None if row is None else row[0]
