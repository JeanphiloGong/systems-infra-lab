import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from labs.transactions.locking.locking import lost_update, optimistic

def test_lost_update() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"],autocommit=True) as a, psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"],autocommit=True) as b:
        s="t03_"+uuid4().hex; a.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(s)))
        try:
            for c in (a,b): c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(s)))
            a.execute(Path("labs/transactions/locking/schema.sql").read_text()); assert lost_update(a,b)==(10,10,9)
        finally: a.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(s)))

def test_optimistic_conflict() -> None:
    with psycopg.connect(os.environ["SYSTEMS_LAB_DATABASE_URL"], autocommit=True) as c:
        s="t03_"+uuid4().hex; c.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(s)))
        try:
            c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(s)))
            c.execute(Path("labs/transactions/locking/schema.sql").read_text())
            assert optimistic(c) == (1, 0)
            assert c.execute("SELECT quantity,version FROM inventory WHERE id=1").fetchone() == (9,1)
        finally: c.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(s)))
