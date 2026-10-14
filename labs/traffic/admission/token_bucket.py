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
