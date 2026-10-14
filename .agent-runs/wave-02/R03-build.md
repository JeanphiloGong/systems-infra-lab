# R03 author evidence

Status: implemented; independent review required. Scope is labs/replication/multi_leader, tutorials/05-replication/03-multi-leader, tests/replication/multi_leader and this evidence. No commits or shared progress changes.

Read exact R03 roadmap before implementing. Applied from-scratch-tutorial-plan and from-scratch-tutorial-build; guides are Chinese with explicit previous-version pressure, complete source checkpoints, directly executable semantic checks and bounded simulation contracts.

- v0: discrete-event heap schedules actual simulated request, commit, replication and acknowledgment events. Success latency is finished-started; 0/7/40ms network input yields remote 2/16/82ms. Checks include a timeout followed by late commit/ack and a dropped partition request.
- v1: both writers confirm locally in 2ms. Fixed two-author vector clocks preserve concurrent (1,0)/(0,1) candidates after repair, rather than inventing one winner. Later explicit user write dominates the observed siblings. Delivery uses v0's actual message events.
- v2: deterministic order (wall timestamp, region, sequence) gives order-independent LWW for valid unique versions. A write confirmed at real simulated t=2 with +1000 offset defeats B's t=4 write. Tests check tie rules, duplicates, reversed delivery and a slow-clock write losing even locally.
- v3: state-based G-Counter with unique component ownership, componentwise max and summed reads. Checks all six permutations of three snapshots, repeated and reverse delivery, immutable old snapshots, invalid state/increment rejection and missing-latest-state convergence condition.
- v4: same two-request workload and inter-request pacing invokes real v0/v2 classes. Connected B observes A before writing; partitioned B cannot. Reports computed success/timeout latencies, success count, causally isolated acknowledged candidate values and actual lost conflicts after convergence. No throughput or production performance claim.

Verification: `uv run python -m pytest tests/replication/multi_leader -q` => **5 passed in 0.76s**. Each parametrized test extracts all printed sources AND the chapter's printed semantic checks, runs both entry point and checks in fresh subprocesses with isolated paths, and asserts exact fence/source equality. Five pytest cases contain the multiple explicit assertions printed in the tutorials.

Measured default outcomes: connected single [2,82]ms vs multi [2,2]ms; partition single 1/2 acknowledged with 100ms timeout, multi 2/2 acknowledged but loses A-profile after LWW convergence. These are simulated milliseconds computed from event timestamps, not wall-clock benchmarks.

Permanent teaching structures added: a minimal event scheduler and request timing record in v0, causal version metadata in v1, LWW versions in v2, and counter components in v3. Each is introduced by its learning requirement; no compatibility layers. Tests clean their temporary extraction directories; no servers or background sessions needed. Assumptions include stable A/B writer identities, no state reset, one scalar key (except counter), fixed delay, memory-only state and final delivery for convergence.
