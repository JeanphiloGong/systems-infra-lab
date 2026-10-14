from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass
class Record:
    fingerprint: str
    state: str
    response: str | None = None


class IdempotencyStore:
    def __init__(self, retention: int = 3) -> None:
        if retention < 1:
            raise ValueError("retention must be positive")
        self.retention = retention
        self.records: dict[str, Record] = {}
        self.age: dict[str, int] = {}
        self.tick = 0
        self.next_id = 1

    def _fingerprint(self, payload: dict[str, str]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()

    def begin(self, key: str, payload: dict[str, str]) -> Record:
        fingerprint = self._fingerprint(payload)
        existing = self.records.get(key)
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise ValueError("request key reused with different payload")
            if existing.state == "processing":
                raise RuntimeError("request is still processing")
            return existing
        record = Record(fingerprint, "processing")
        self.records[key] = record
        self.age[key] = self.tick
        return record

    def complete(self, key: str, response: str) -> str:
        record = self.records[key]
        record.state, record.response = "completed", response
        return response

    def create(self, key: str, payload: dict[str, str]) -> str:
        record = self.begin(key, payload)
        if record.state == "completed":
            assert record.response is not None
            return record.response
        response = f"order-{self.next_id}"
        self.next_id += 1
        return self.complete(key, response)

    def advance(self) -> None:
        self.tick += 1
        self.records = {key: record for key, record in self.records.items() if self.tick - self.age[key] <= self.retention}
        self.age = {key: self.age[key] for key in self.records}


if __name__ == "__main__":
    store = IdempotencyStore()
    print(store.create("request-1", {"customer": "ada"}))
    print(store.create("request-1", {"customer": "ada"}))
