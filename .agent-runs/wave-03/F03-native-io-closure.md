# F03 native-I/O deadline closure

Added io_deadline.py and its complete printed checkpoint in v2/tutorial.md. A real loopback TCP server accepts a connection and deliberately stalls its response. The client uses one absolute monotonic expires timestamp; before connect and recv it calls socket.settimeout with remaining time. The retry policy receives the remaining budget. Native TimeoutError is terminal, so no retry begins after the operation times out. No adapter or wrapper abstraction was added.

Direct observation: budget_seconds=0.05, elapsed_seconds=0.05046413489617407, attempts=1, timed_out=true, thread_stopped=true. finally signals the server, joins its thread, and context managers close listener/client/peer sockets.

`uv run python -m pytest tests/traffic/retry -q` => **19 passed in 0.92s**. New test extracts v2.py and io_deadline.py entirely from the tutorial, verifies source equality, runs a clean subprocess, parses actual timing/attempt/thread results, and enforces a loose <1s scheduling bound. Earlier tests still cover attempts+backoff accounting and sleep overshoot. The <1s CI limit is not advertised as a precise deadline guarantee.

The guide explicitly distinguishes native bounded I/O from arbitrary synchronous callable preemption. OS scheduling may delay return slightly; no hard-real-time or external-effect rollback guarantee is claimed. No commits, progress edits, persistent sockets or background threads. R04 work was paused for this repair.
