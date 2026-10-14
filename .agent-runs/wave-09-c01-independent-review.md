# C01 v3 Counterexample Review: PASS

Independently read the revised source, tutorial derivation, plan, behavior test
and extraction checks. Ran `uv run pytest tests/consensus/cap_quorum -q`:
**10 passed in 0.20s**. v3 extraction checks exact fence/source equality and
decodes the subprocess JSON to assert the read inversion and completed write.

The contradiction is valid under the declared register protocol:

- N=3 and R=W=2 establish intersecting read/write quorums.
- A receives version 1 while the only write is pending. read1 selects A/B,
  reads version 1 and returns new. This uses an actual quorum_read result.
- Only after read1 completes, read2 selects B/C and returns old/version 0.
- B then receives the write and the second acknowledgement completes it.
- For any legal sequential history, read1=new requires the unique write to
  precede read1. Real-time order requires read1 before read2. With no other
  write, read2 must then be new, contradicting its old result. Overlap of
  the pending write with both reads cannot remove this constraint.

The selected R-response subsets are now explicit; the counterexample does not
use disjoint read/write sets or R+W<=N. Tutorial prose explains the distinction
and accurately bounds the code as a deterministic message schedule, not a
network benchmark or general-purpose linearizability verifier.

This closes the C01 v3 counterexample gap in wave-07a-plan-review.md. It does
not close unrelated R01/R02 findings or add evidence for other modules.
No implementation or progress files were changed during this review; only this
record was added. No abstraction or implementation cleanup was introduced.
