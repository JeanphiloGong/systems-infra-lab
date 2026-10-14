# D04 tutorial plan

Scenario: an order reserves inventory, charges payment, then creates delivery. Invariant: each effect and compensation is deduplicated and each failure ends as completed, compensated, or manual.

1. v0 serial partial effects.
2. v1 persistent step state and restart.
3. v2 reverse idempotent compensation.
4. v3 bounded compensation retries and manual intervention.
5. v4 concurrent order keys and isolation limits.

All versions have complete source fences and strict replay.
