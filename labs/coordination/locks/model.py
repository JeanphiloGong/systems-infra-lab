from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class Lease:
    owner: str
    token: int
    expires_at: float


class LockService:
    def __init__(self) -> None:
        self._lock = Lock(); self.lease: Lease | None = None; self.next_token = 0

    def acquire(self, owner: str, now: float, ttl: float) -> Lease | None:
        if ttl <= 0: raise ValueError("ttl must be positive")
        with self._lock:
            if self.lease is not None and self.lease.expires_at > now: return None
            self.next_token += 1; self.lease = Lease(owner, self.next_token, now + ttl); return self.lease

    def renew(self, owner: str, token: int, now: float, ttl: float) -> Lease:
        with self._lock:
            if self.lease is None or self.lease.owner != owner or self.lease.token != token or self.lease.expires_at <= now: raise ValueError("lease lost")
            self.lease = Lease(owner, token, now + ttl); return self.lease

    def release(self, owner: str, token: int) -> None:
        with self._lock:
            if self.lease is not None and (self.lease.owner, self.lease.token) == (owner, token): self.lease = None


class FencedResource:
    def __init__(self) -> None:
        self.token = 0; self.value = None

    def write(self, token: int, value: object) -> None:
        if token < self.token: raise ValueError("stale fencing token")
        self.token, self.value = token, value
