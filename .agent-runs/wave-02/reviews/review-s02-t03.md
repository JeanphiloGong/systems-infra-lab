# Wave 02 S02/T03 review

## Findings

- [revise] S02 v5 tutorial: it points readers to `labs/storage/bplus_tree/page_file.py` and asks them to run pytest, but contains no complete checkpoint code fence or exact incremental code changes. The review standard requires the final meaningful step to be an assembled, reader-visible checkpoint; a source link plus tests is not independently replayable tutorial code. Required change: include the complete `page_file.py` checkpoint (or an explicitly complete generated source artifact) and a command that runs the document's own code, then replay it in isolation.

No blocking correctness findings remain for S02 v0-v4 or T03 v0-v4 after the
authors' revisions. Earlier S02 separator-routing and recursive-parent bugs
were fixed; earlier T03 setup and partial-checkpoint defects were fixed.

## Verdicts

- S02 v0-v4: pass.
- S02 v5: revise; not accepted pending a complete checkpoint.
- T03 v0-v4: pass.

## Exact document hashes

| Version | SHA-256 |
| --- | --- |
| S02 v0 | `f8704e84ba00163a34d40938ad5ad2b0f3416034be5cca7c41f186b79bddd267` |
| S02 v1 | `d67cd8e4f09ba9f3d63c89314c42b0338768f3863ff4a67db1084ee1c2e5773b` |
| S02 v2 | `d6a940720ad46d42ff8d18a1401e75d68e4232d6fe3ef7da8c508a4b2b93f073` |
| S02 v3 | `5b5deacaf4c081908f22c5f5b4aa61b111eaa0006bb522326e57230736ae45e3` |
| S02 v4 | `fb70b202cccb9965d97e6ca5da55f2967dd01f4ec10c35895d3ce83b0859e680` |
| S02 v5 | `b6c0eedc4064dd657d61cee3d431b2be7e2ea10fc4dc4f62bc86d59979421b73` |
| T03 v0 | `92b1c4ccad9c54454fe6f5e463e01c5706f3bc605860bb8bc902a7ef021f2006` |
| T03 v1 | `05edc9376801dffeb6cae15523b5cabe6c8c4a3966a16582e316d3ceead6b221` |
| T03 v2 | `76e08e59861d23d99a6437c5874d5169977e85461c106afc89cf99c66f9e6ff0` |
| T03 v3 | `88bf41142ba1098221e2252abcb309dc99f25ded7811f550a0815d17c6da1cd9` |
| T03 v4 | `cdd7c8ce7b3d2b97e35a44ff7dd9054949649d69324be51306a24e884cf94554` |

## Verification

Extracted and replayed the S02 v0-v4 printed checkpoints in temporary
directories. Observed `v0 ordered reference ok`, `v1 leaf capacity ok`, `v2
leaf splits and bounded root ok`, `v3 recursive splits ok`, and the v4
inclusive scan checks. The repaired v2 code routes separator equality right,
and v3 survives randomized recursive splits.

For T03, extracted full v0-v4 checkpoints. Against isolated PostgreSQL,
observed `(10,10,9)`, `(1,0)`, row-lock final quantity 8, real deadlock output
`(1,8,8)` plus ordered `(8,8)`, and the isolated escalation model output
`records_before=3 records_after=1 unrelated_row_blocked=True`.
Focused tests currently pass: `uv run pytest tests/storage/bplus_tree -q`
reports 10 passed; `SYSTEMS_LAB_DATABASE_URL=... uv run pytest
tests/transactions/locking -q` reports 6 passed.

No accepted Wave 01 files were changed. S02 v5 remains open solely for the
tutorial checkpoint/evidence gap.
