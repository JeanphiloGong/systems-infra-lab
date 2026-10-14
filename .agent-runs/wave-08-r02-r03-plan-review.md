# R02/R03 Independent Review

All ten revised plans: **PASS for current-code fidelity**. Independently ran
all 15 exact pytest selectors printed in those plans; all passed. Read the
per-version requirements, named methods, behavior tests and extraction paths.
Plans distinguish complete dependency extraction from repository-module tests
and disclose their evidence limits rather than calling output flags proof.

R03's extracted dependency files are checked against source; each checkpoint
runs both its printed entry and printed semantic-check file. Checks cover
simulated remote latency, delayed acknowledgements, partition conflicts,
vector-version merges, clock-skew LWW losses, duplicate/ordered counter state
merges and identical-workload topology comparison. No new blocking R03 scope
finding from this review; simulation and fixed-identity boundaries remain.

## R02 Original Scope: REVISE

These are implementation gaps, not permission to narrow the roadmap by
placing them in Still-lacks:

1. `consistency/v2.py` records no key or invocation/completion intervals and
   check_history ignores values. An independent probe appending
   ('read',1,'WRONG') after name=Ada returns True. Thus its version check
   cannot establish the roadmap's real-time linearizable history requirement.
   Add explicit histories and bad-history tests, including value correctness
   and real-time precedence, scoped to the declared small fixed-leader model.
2. `consistency/v4.py` keeps only the latest value. Probe: write Ada at version
   1, write Grace at 2, read snapshot_version=1 returns Read(None,1), not Ada.
   Add retained versions and repeated/multi-key snapshot checks before claiming
   the roadmap's snapshot-consistency comparison.
3. The same module returns early when a replica key is absent. Probe: partition,
   write Ada, then SESSION read with that returned write version produces
   Read(None,0), violating read-your-writes. With an existing old replica value,
   the fallback instead reads the leader directly despite partition. Probe:
   Ada at 1, partition, Grace at 2 returns Read(Grace,2). Declare whether the
   client can reach the leader under this partition model, and consistently
   implement fallback/wait/unavailable for missing and stale replicas. Test
   both, rather than claiming the general session boundary from one happy path.

R02 v0/v1 convergence/session and v3 key-local repair retain their existing
small-model evidence. The v2/v4 deficiencies require original-scope reopening;
honest plan limitations alone do not close them. No overall progress changed.

Only this review artifact was added. No source, plan, tutorial or index edited;
no abstraction or implementation cleanup was introduced.
