"""Add a post-snapshot write to the exact v2 experiment under review."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "labs/dataflows/cdc"))
from common import connect


original = (ROOT / "labs/dataflows/cdc/v2.py").read_text()
anchor = '        conn.execute("INSERT INTO orders VALUES (2,\'after-snapshot\')")'
assert original.count(anchor) == 1
for statement in (
    "UPDATE orders SET value='paid' WHERE id=1",
    "DELETE FROM orders WHERE id=1",
):
    source = original.replace(anchor, f"        conn.execute({statement!r})\n" + anchor)
    namespace = {"__name__": "review_probe"}
    exec(compile(source, "v2_with_concurrent_write.py", "exec"), namespace)
    result = namespace["experiment"]()
    with connect() as conn:
        expected = dict(conn.execute("SELECT id,value FROM orders").fetchall())
    assert result["projection"] != expected
    print({"write": statement, "actual": result["projection"], "source": expected})
