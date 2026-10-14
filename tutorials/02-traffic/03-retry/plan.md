# F03 tutorial plan

The learning scenario is a dependency that fails briefly while many clients are active. The implementation grows one pressure at a time, preserving the invariant that attempts and elapsed retry time stay bounded.

1. v0: immediate retry and an attempt counter; verify amplification.
2. v1: retryable versus permanent exceptions and a total deadline; verify permanent failures escape and deadline exhaustion stops.
3. v2: exponential delay plus jitter; inject a seeded random source and a sleep recorder to verify a reproducible distribution.
4. v3: closed/open/half-open circuit breaker; verify threshold opening, rejection while open, one half-open probe, and recovery.
5. v4: execute three nested retry layers against an instrumented leaf; observe 27 actual calls, then cap calls at 10 with one consumable shared budget. Verify exhaustion is terminal, early success preserves unused tokens, and permanent failures and elapsed deadlines cross all layers without retry.

Every version has one full source fence marked with its exact target path. The replay test extracts that fence into a temporary file and executes it, so the tutorial cannot drift from the runnable checkpoint.

