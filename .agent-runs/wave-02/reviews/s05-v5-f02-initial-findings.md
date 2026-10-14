# Original-scope review: S05 v5 and F02

Verdict: not accepted. These findings refer to the initial submitted drafts.

- S05 v5 injects RuntimeError in the current process and catches it in tests.
  The original roadmap requires process termination before/after publication
  and reopening from the old or new complete file set. The CLI creates files
  and publishes the new manifest immediately, so it does not establish a prior
  manifest for the before-publication crash case. Its replay test only checks
  strings/fence presence. Required correction: real child termination at both
  boundaries starting from an old manifest, fresh restart, complete printed
  dependencies, and execution of extracted checkpoints.
- F02 bounded worker lets job exceptions escape, killing the worker. A live
  subprocess with one failing job, a subsequent job, and close() exceeded a
  two-second timeout: queue.join cannot finish after the only worker dies.
- F02 in-flight counters decrement at dequeue, excluding active jobs, while
  incrementing before admission includes rejected and waiting submissions.
  They do not measure accepted queued plus executing work.
- F02 balancer is serial: it increments a worker, sleeps, and decrements before
  considering the next request. Every least-inflight choice therefore sees a
  tie. Reproduction with slow first and fast second workers assigned all four
  jobs to slow. Original v3/v4 require overlapping work and slow-worker impact.
- F02 v0 measures queue count only, omitting original memory and waiting-delay
  measurements. v4 uses identical service times, zero-timeout rejection, and
  wait sample count only: no degraded single worker, tail latency comparison,
  or slower upstream producer demonstrating propagated backpressure.

No reviewer source edits were made. These findings were sent to root/authors.
