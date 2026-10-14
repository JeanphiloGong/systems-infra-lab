# F02 plan: admission control, rate limiting, and backpressure

One scenario drives the series: arrivals remain faster than a finite worker service rate. Each version changes one control boundary and measures the resulting queue, rejection, or distribution behavior.

| Version | Pressure | Change | Check |
| --- | --- | --- | --- |
| v0 | Unbounded arrivals hide overload in a growing queue | Plain queue and workers | Peak queue exceeds one |
| v1 | A queue must have a memory/in-flight bound | Bounded queue with wait timeout or rejection | Accepted plus rejected equals arrivals |
| v2 | Admission alone does not limit rate or bursts | Token bucket with rate and burst | Burst is accepted, refill is time based |
| v3 | One worker can become a hot path | Round-robin and least-in-flight policies | Dispatch counts expose policy behavior |
| v4 | A slow worker propagates delay to callers | End-to-end bounded queue and explicit overload result | Rejections and wait metrics stay observable |

The experiments use local threads and synthetic service delays. They model application scheduling and queue behavior; they do not claim network throughput, OS memory measurements, or production fairness guarantees.
