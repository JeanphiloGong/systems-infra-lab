# Wave 07a Independent R01/C01 Review

Plan fidelity: **PASS** for all nine revised plans. Original implementation
scope: **REVISE** for R01 and C01; findings below remain unimplemented.

Read every plan and matched its behavior/check/limitations to tutorial fences,
implementation and named tests. Independently ran all 18 exact version-specific
pytest commands printed in the plans: 18/18 exited successfully. These are
nine extraction checks and nine implementation behavior checks, not eighteen
new end-to-end protocols. Extraction tests assert process success only; they
do not compare output or require exact source equality. Plans disclose this
limit. The added scenarios and per-version assertions are concrete rather than
generic boilerplate.

## Original-Scope Findings

1. **R01 v0 has no two-process replication or restart recovery.** Roadmap
   line 338 requires both. In `labs/replication/leader_follower/v0.py`, Leader
   and Follower are ordinary objects, and Follower.restart has only a docstring.
   Its passing test reuses the same object and memory. Add independent
   processes, durable position/state, and a fresh-process recovery check.
2. **R01 v3 does not measure confirmation latency or retained data after
   failure.** Roadmap line 341 requires those observations. write(FOLLOWER)
   calls apply synchronously in process, and fail_before_replication merely
   returns a log suffix. It neither injects failure nor restores a surviving
   replica. Measure the configured confirmation conditions, response times,
   and post-failure acknowledged data using the process protocol.
3. **R01 v4 checks only in-memory catch-up.** The follower survives between
   calls. catch_up slices away old entries, so the named repeated-delivery
   test never actually sends a duplicate into apply. Direct apply does have
   a duplicate-skip branch, but neither that branch nor restart from durable
   progress is established by the named checkpoint test. Add actual duplicate
   receipt plus independent stop/resume consistent with the v0 process model.
4. **C01 v3 lacks the required counterexample.** Roadmap line 399 requires a
   history showing R+W>N does not imply linearizability. Current code proves
   set intersection and picks the maximum tuple from all provided replicas;
   there is no write protocol, selected R response subset, operation history,
   or illegal read ordering. Showing R=W=1 can fail to intersect is not a
   counterexample under R+W>N. Add a concrete N=3,R=W=2 execution, such as a
   partially propagated write followed by ordered reads that observe new then
   old values, with assertions showing why no legal linearization exists.

Disclosure in Still-lacks is useful but cannot redefine these roadmap
requirements as optional follow-up work. Plan-fidelity PASS must not be used
to keep the affected implementation checkpoints accepted as complete.

Only this review record was added. No implementation, tutorial, plan,
progress/index or runtime abstraction was changed; no cleanup was performed.
