# Wave 06 transaction-plan quality evidence

Snapshot: 2026-10-14 UTC. Working directory: `/home/gong/date/2026/oct/systems-infra-lab`.

Repaired sample version plans:

- `tutorials/07-coordination/01-idempotency/v0..v4/plan.md` (D01)
- `tutorials/04-query/03-planner/v0..v3/plan.md` (Q03)
- `tutorials/09-recovery/01-backup/v0..v4/plan.md` (A01)
- `tutorials/08-dataflows/04-analytics/v0..v3/plan.md` (E04)

Each sample plan now states the prior gap, concrete pressure, deterministic naive break, one mechanism change, expected output, version fence, limitation, next pressure, and a version-specific replay or run command. The plans are standalone replacements for the generic sample text; tutorial bodies and implementations were not edited.

Audit performed: all 18 sample version plan paths exist. `find tutorials -name plan.md | wc -l` reports 233 plans in this untracked repository snapshot. No acceptance claim is made; reviewer follow-up is required before expanding the same treatment to the remaining R/C/D/Q/F/E/A plans.
