# A03 high-availability review: REVISE

The deterministic model suite passes (`uv run pytest -q tests/recovery/ha`:
5 passed, 2 skipped), and `replay_patroni.py --version 2/3/4` verifies all five
Patroni source fences exactly in isolated temporary directories. The supplied
live Patroni evidence documents promotion, old-primary write rejection,
reinitialize, and cutback with the stated RPO/RTO limits.

The versioned replay claim is incomplete. `tests/recovery/ha/replay_a03.py`
extracts and executes only versions 0 and 1; its `__main__` loop is
`for version in range(2)`. Versions 2, 3, and 4 are covered only by the
separate source-presence script, which does not execute their behavior. This
does not prove the version-specific timeout promotion, fencing, rejoin, and
cutback paths from the tutorial fences. The author evidence says “v0-v4 replay”
but the checked-in runner contradicts that claim.

Follow-up: the author changed the runner to execute all five model versions;
the independent rerun now passes v0-v4. This closes the model replay gap only.
The Patroni extraction runner still only checks source equality and reports
live_required; it does not run the extracted live probe against the dedicated
stack. The supplied live execution used the repository module, which is useful
evidence but does not close the requested extracted-live replay contract.

Decision: **REVISE**. Execute the extracted Patroni implementation against the
explicitly started disposable stack and retain observed promotion, fencing,
rejoin, cutback, and cleanup evidence. Model replay must remain labeled as
model evidence. v2-v4 live tutorial checkpoints remain unaccepted.

## Extracted Live Repair and Teaching Review

The revised replay_patroni.py now extracts the five exact live source/config
fences, launches the temporary patroni_probe.py using `python -I`, sets cwd to
the temporary directory, and asserts decoded behavior. This closes the prior
source-only runner defect. Root independently reports v2 live execution:
old p1, new p2, acknowledged_lost=0, old_process_alive=true,
old_write_rejected=true, basebackup rejoin, RTO=23.218s, cutback=2.099s.
v3/v4 and final cleanup are pending root evidence at this review snapshot.

The added module and version plans, plus the revised v0-v4 prose, close the
tutorial-completeness findings:

- v2, v3, and v4 now state that the live probe is shared while each chapter
  selects a distinct failure pressure, expected observation, and limitation.
- v2 explains ttl/loop_wait/retry_timeout, false-positive conditions and the
  fencing tradeoff; v3 covers network isolation versus process state; v4
  covers reinitialize, rejoin, and cutback boundaries.
- v0/v1 now define RTO/RPO measurement windows, manual promotion, client
  routing, and operator fencing responsibility.
- A03 module plan and all five version plans now provide verifiable tasks,
  prerequisites, fences, and checkpoint observations.

No live stack was mutated by this review, avoiding interference with root's
sequential live runs. No implementation changes were made.

Decision: **PASS**, based on the extracted-live evidence in
`.agent-runs/wave-05-A03-extracted-live.md` plus the independently reviewed
plan and prose revisions. The live evidence is not re-run in this review.

Root subsequently completed extracted live executions for v2, v3, and v4 and
cleanup; exact observations are recorded in
`.agent-runs/wave-05-A03-extracted-live.md`. The extracted-live execution gap
is closed for all three versions. The teaching-completeness findings above
remain REVISE; they are not resolved by repeated successful live runs.
