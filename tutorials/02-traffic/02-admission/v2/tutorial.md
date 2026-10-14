# F02 v2: token bucket rate and burst admission

## Pressure

A bounded queue limits occupancy but still permits a caller to submit a burst instantly. A token bucket separates a long-term rate from a finite burst allowance.

## One change

<!-- checkpoint: token_bucket.py -->

```python
from threading import Lock


class TokenBucket:
    def __init__(self, rate, burst, clock):
        if rate <= 0 or burst < 1:
            raise ValueError("rate and burst must be positive")
        self.rate = rate
        self.capacity = float(burst)
        self.tokens = float(burst)
        self.last = clock()
        self.clock = clock
        self.lock = Lock()

    def allow(self, cost=1):
        if cost <= 0 or cost > self.capacity:
            raise ValueError("cost must be within bucket capacity")
        with self.lock:
            now = self.clock()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens < cost:
                return False
            self.tokens -= cost
            return True


if __name__ == "__main__":
    now = [0.0]
    bucket = TokenBucket(rate=2, burst=2, clock=lambda: now[0])
    burst = [bucket.allow(), bucket.allow(), bucket.allow()]
    now[0] = 0.5
    refill = bucket.allow()
    print({"burst": burst, "refill_after_half_second": refill})
```

## Break, check, freeze

The first two calls consume the configured burst; the third is rejected. Advancing the test clock by half a second restores one token at rate two per second. The bucket is thread-safe, but it does not promise fairness between callers; v3 addresses worker selection separately.
