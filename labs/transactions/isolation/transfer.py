from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql


def transfer(
    conn: psycopg.Connection,
    source: int,
    target: int,
    amount: int,
    *,
    fail_after_debit: bool = False,
) -> None:
    """Transfer integer units; the caller supplies an idle autocommit connection."""
    if type(amount) is not int or amount <= 0:
        raise ValueError("amount must be a positive integer")
    if type(source) is not int or type(target) is not int or source == target:
        raise ValueError("source and target must be distinct integer IDs")
    if not conn.autocommit or conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
        raise ValueError("an idle autocommit connection is required")
    with conn.transaction():
        changed = conn.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s AND balance >= %s",
            (amount, source, amount),
        ).rowcount
        if changed != 1:
            raise ValueError("source missing or insufficient balance")
        if fail_after_debit:
            raise RuntimeError("injected failure after debit")
        if conn.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, target),
        ).rowcount != 1:
            raise ValueError("target missing")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer in a fresh disposable schema")
    parser.add_argument("--source", type=int, default=1)
    parser.add_argument("--target", type=int, default=2)
    parser.add_argument("--amount", type=int, default=30)
    parser.add_argument("--fail-after-debit", action="store_true")
    args = parser.parse_args()
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True, connect_timeout=5) as conn:
        schema = "t01_" + uuid4().hex
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        try:
            conn.execute(Path(__file__).with_name("schema.sql").read_text())
            try:
                transfer(conn, args.source, args.target, args.amount, fail_after_debit=args.fail_after_debit)
            finally:
                print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
