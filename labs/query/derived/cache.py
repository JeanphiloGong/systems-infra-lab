from threading import Lock


class Cache:
    """One key, one process; a monotonic caller clock makes tests deterministic."""

    def __init__(self, clock, ttl=5):
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.clock, self.ttl = clock, ttl
        self.entry = None
        self.epoch = 0
        self.lock = Lock()
        self.hits = self.loads = self.rejected_fills = 0

    def invalidate(self):
        with self.lock:
            self.epoch += 1
            self.entry = None

    def get(self, loader, after_load=None, guarded=True):
        while True:
            with self.lock:
                if self.entry is not None and self.clock() < self.entry[1]:
                    self.hits += 1
                    return self.entry[0]
                epoch = self.epoch
            value = loader()
            self.loads += 1
            if after_load is not None:
                after_load()
                after_load = None
            with self.lock:
                if guarded and epoch != self.epoch:
                    self.rejected_fills += 1
                    continue
                self.entry = (value, self.clock() + self.ttl)
                return value
