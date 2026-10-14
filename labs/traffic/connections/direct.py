from __future__ import annotations

import os
import time
from typing import Any

import psycopg


def connect_query(sql: str = "SELECT 1") -> tuple[Any, float]:
    """Open one session, execute one statement, and close the session."""
    started = time.perf_counter()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()[0]
    return result, time.perf_counter() - started


def connect_many(count: int) -> tuple[int, float]:
    if count < 1:
        raise ValueError("count must be positive")
    started = time.perf_counter()
    for _ in range(count):
        connect_query()
    return count, time.perf_counter() - started


def measure_once(sql: str = "SELECT 1") -> dict[str, float | Any]:
    started = time.perf_counter()
    connection = psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"])
    connected = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()[0]
        queried = time.perf_counter()
    finally:
        connection.close()
    return {"value": result, "connect_seconds": connected - started, "query_seconds": queried - connected, "total_seconds": queried - started}


if __name__ == "__main__":
    metrics = measure_once()
    count, total = connect_many(3)
    print({"metrics": metrics, "connections": count, "total_elapsed_seconds": total})
