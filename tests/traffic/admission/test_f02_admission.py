from __future__ import annotations

from labs.traffic.admission.balancer import LoadBalancer, Worker
from labs.traffic.admission.bounded import BoundedAdmission, run_bounded
from labs.traffic.admission.token_bucket import TokenBucket
from labs.traffic.admission.unbounded import observe


def test_unbounded_queue_grows_before_workers_catch_up() -> None:
    result = observe(total=20, workers=1, service_seconds=0.001)
    assert result.completed == 20
    assert result.peak_queue > 1


def test_bounded_admission_rejects_without_unbounded_work() -> None:
    result = run_bounded(total=50, capacity=2, workers=1, timeout=0)
    assert result.accepted + result.rejected == 50
    assert result.rejected > 0
    assert result.max_in_flight <= 3


def test_token_bucket_burst_then_refill() -> None:
    now = [0.0]
    bucket = TokenBucket(rate=2, burst=2, clock=lambda: now[0])
    assert bucket.allow() and bucket.allow()
    assert not bucket.allow()
    now[0] = 0.5
    assert bucket.allow()


def test_load_balancer_strategies_are_explicit() -> None:
    workers = [Worker("fast", 0.01), Worker("slow", 0.1)]
    rr = LoadBalancer(workers, "round_robin")
    least = LoadBalancer(workers, "least_inflight")
    assert rr.dispatch(100) == {"fast": 50, "slow": 50}
    counts = least.dispatch(100)
    assert counts["fast"] > counts["slow"] > 0
    assert max(least.latencies) < max(rr.latencies)


def test_failed_job_does_not_kill_worker() -> None:
    admission = BoundedAdmission(capacity=2, workers=1, service_seconds=0)
    def fail() -> None:
        raise RuntimeError("controlled job failure")
    assert admission.submit(fail, timeout=1) is not None
    assert admission.submit(lambda: None, timeout=1) is not None
    admission.close()
    assert admission.failed == admission.completed == 1
