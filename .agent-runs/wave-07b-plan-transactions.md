# Wave 07b: D02 and Q01 version plans

Scope: `/home/gong/date/2026/oct/systems-infra-lab`, 2026-10-14. This batch changes exactly the following nine plans plus this evidence file. No tutorial bodies, implementation files, progress, index, or other modules were edited by this batch.

| Plan | Observed single-version output |
| --- | --- |
| `tutorials/07-coordination/02-distributed-lock/v0/plan.md` | winner=b, contenders=2; a is also a valid winner |
| `tutorials/07-coordination/02-distributed-lock/v1/plan.md` | old_owner_paused=True, new_owner=b, overlap_risk=True |
| `tutorials/07-coordination/02-distributed-lock/v2/plan.md` | stale_rejected=True, token=2 |
| `tutorials/07-coordination/02-distributed-lock/v3/plan.md` | stale_renew_rejected=True, current_owner=b, token=2, expires_at=5 |
| `tutorials/07-coordination/02-distributed-lock/v4/plan.md` | availability=unknown, safety_action=do not write, resource retains token=2/value=new |
| `tutorials/04-query/01-modeling/v0/plan.md` | inconsistent_rows=2 |
| `tutorials/04-query/01-modeling/v1/plan.md` | join=A. Lovelace/Widget/12, foreign_key_rejected=True |
| `tutorials/04-query/01-modeling/v2/plan.md` | read_joins=0, view_update_writes=1, stale_window=True |
| `tutorials/04-query/01-modeling/v3/plan.md` | normalized_read_ops=2, denormalized_read_ops=1, extra_write_ops=1, stale_read_model=True, snapshot_price=12 |

Verification: an audit loaded each plan, required all eight Pressure/Naive/Break/Change/Check/Freeze/Still-lacks/Next labels, checked referenced tutorial and replay paths, rejected the previous generic baseline phrases, extracted the exact single-version Python command printed in the plan, and ran that command with the uv interpreter. Result: 9/9 passed, each subprocess exited 0 with the outputs above. Each command extracted only its version's checkpoint.py into an automatically cleaned temporary directory. The module replay is separately labeled as all-version verification.

Specific scope corrections: D02 v3 proves renewal ownership only (its fence does not implement release). Q01 v1 models foreign-key rejection with an assertion after dictionary insertion, not database rollback. Q01 v3 declares a maintenance-write budget without performing the write; plans do not present it as measured throughput or completed maintenance.

No new runtime abstraction was added. Generic plan prose was replaced in place; no temporary helper files were retained. No commits or module-acceptance claims are made. Stop here for independent review.
