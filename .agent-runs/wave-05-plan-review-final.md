# Wave 05 version-plan review: REVISE

Coverage is complete: an independent count finds **196** `tutorials/**/vN/plan.md`
files, matching the roadmap's expected version paths. The author path checks
also verify all 109 newly requested files exist and include a Pressure marker.
P03's five plans are a strong example: each names the migration pressure,
break, one mechanism change, version-specific output, replay command, and
model boundary; its replay and test commands were reported passing.

The content gate is not complete. A scan finds all 109 newly added plans contain
the same generic template phrases (`最小模型只保留能触发压力的组件`,
`Pressure：establish the failure pressure`, and `Change：本版只加入解决该压力`)
in place of module-specific work. Sampling D01, Q03, A01, and E04 confirms
that the scenario/invariant are generic but the pressure, naive failure, break,
change, check, and acceptance output do not identify the actual idempotency,
query-planner, PITR, or FDW behavior in the corresponding tutorial. Their
replay command points at a suite, but the plan does not state the expected
version-specific observation or prove that the suite runs the extracted fence.
Some v3 plans also describe a generic restart/concurrency pressure unrelated to
the module's actual v3 behavior.

Decision: **REVISE**. Keep the 196-file coverage, but rewrite each templated
plan around the real scenario and current fenced code: name the prior-version
gap, deterministic naive break, single mechanism change, exact check/output,
freeze artifact, remaining limitation, next pressure, and an executable
version-specific replay path. Do not count a plan as complete solely because it
contains section labels or a generic pytest command. No plan files were edited
by this review.
