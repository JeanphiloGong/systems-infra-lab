# F04 authored checkpoints awaiting independent review

Replaced the previous sequential `Herd` draft and its mirror tests with actual asyncio experiments. Ownership: labs/traffic/herd, tests/traffic/herd, tutorials/02-traffic/04-herd and this evidence only. No commits or shared progress edits.

Read original roadmap F04 v0-v3 and applied from-scratch-tutorial-build. Each chapter has a version plan, natural Chinese explanation, complete current code plus dependencies, runnable assertions and next limitation. v1 deliberately retains direct-await cancellation behavior; v2 replaces it with cancellation isolation rather than silently showing the final abstraction first.

Actual verification:

`uv run pytest tests/traffic/herd -q`: **4 passed in 0.76s**. Each parametrized case verifies every printed dependency against source, extracts only those files to a fresh temporary directory, and executes a new interpreter there with isolated PYTHONPATH. The four cases execute all version-specific embedded assertions, not four trivial one-line examples.

`uv run python labs/traffic/herd/v3.py`: synchronized different-key20 calls/peak20; seeded jitter20 calls/peak8; SWR20 immediate stale replies/one blocked background fill; separate processes observed `[1,1]` origin calls, total2.

v0 measures actual Origin active/peak counts while twenty coroutine loads wait at an Event. v1 measures one same-key load and two distinct-key loads, verifies result propagation and pending cleanup. v2 independently checks cancelled first waiter, timed-out waiter, surviving peer success, failure fanout, origin timeout, explicit fill cancellation and successful new fill. v3 checks exact hard expiry blocks rather than returning stale, refresh failure does not extend stale allowance, and hard-miss failure propagates.

Timing boundaries: expiry scheduling/TTL are injected logical times; asyncio tasks, source timeout and waiter timeout execute on a real event loop. This is not load/latency benchmarking. The two-process example uses independent counters to show two fills across process-local registries; it is not a distributed cache implementation. Cancellation requires cooperative async loaders.

New permanent teaching structures are Origin measurement probe, per-key Flights, and TTL/SWR Cache. No compatibility adapter remains. Removed old model.py and old sequential tests; repository search found no remaining imports of them. All fill tasks are completed/cancelled and collected; v3 child processes exit after reporting results. No server or persistent artifact is left running.
