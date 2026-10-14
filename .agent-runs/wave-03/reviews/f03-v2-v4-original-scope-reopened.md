# F03 v2/v4 original-scope re-audit

Verdict: REOPEN. Earlier acceptance does not establish the original `docs/roadmap.md:572` elapsed-time and executed layered-budget requirements.

## Findings

1. **High: v2 loses the elapsed-time deadline.** `labs/traffic/resilience/v2.py:30` initializes a synthetic elapsed counter; line 41 advances it only by scheduled delay. Operation duration and sleep overshoot never count, and successful calls return without a deadline check. A real reproduction using an operation that sleeps 60ms, fails once, then sleeps 60ms and succeeds returned `('late success', 2)` after **0.120641s** under a **0.02s** deadline. The second attempt should never have started. Preserve v1's monotonic deadline, check remaining time before retries/sleep and after work, and make operation timeout/cancellation responsibility explicit. Arbitrary synchronous operations cannot be forcibly bounded by a clock check alone.

2. **High: default v2 backoff does not wait.** `labs/traffic/resilience/v2.py:24` defaults sleep to a no-op. A real always-failing operation with three attempts and base_delay=0.2 performed all three calls in **0.000064s**, despite 0.6s scheduled waits. This cannot demonstrate spreading actual retry arrivals. Use real sleep by default, with an explicit advancing fake clock/sleeper only for deterministic tests. Add fixed-seed multi-client arrival evidence rather than just accepting a Random parameter.

3. **High: v4 does not execute layered retries or enforce a budget.** `labs/traffic/resilience/budget.py:4` computes a power and line 18 takes min(power,total). No operation is invoked, no budget is consumed, no exhausted call is rejected, and no budget is shared across nested callers. Tests assert 27 and 10 from these arithmetic functions. That verifies a formula, not roadmap v4's composed-call execution. Execute three nested retry layers against an instrumented failing leaf; observe 27 leaf calls without sharing and at most 10 with a single shared consumable budget. Assert terminal exhaustion prevents further leaf calls, and successful early completion does not consume unused attempts.

The v2 and v4 printed tutorial fences contain the same faulty semantics. These findings come from source inspection and actual v2 timing reproduction, not inference from green tests. No new implementation or tests were added by this review.

Repair acceptance requires extracted tutorial execution proving elapsed-time accounting including operation duration, actual/injected advancing sleep, fixed-seed retry distribution comparison, and measured nested leaf invocations. Distinguish a policy deadline from hard cancellation guarantees.

Review artifact only; no abstraction added and no source cleanup performed.
