from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    term: int
    index: int
    command: dict[str, str]


class Node:
    def __init__(self, name: str, directory: Path) -> None:
        self.name = name
        self.path = directory / f"{name}.json"
        saved = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.current_term = int(saved.get("term", 0))
        self.voted_for = saved.get("voted_for")
        self.log = [Entry(**entry) for entry in saved.get("log", [])]
        self.commit_index = int(saved.get("commit_index", 0))
        self.last_applied = int(saved.get("last_applied", 0))
        self.state: dict[str, str] = dict(saved.get("state", {}))

    def persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        payload = {"term": self.current_term, "voted_for": self.voted_for,
                   "log": [entry.__dict__ for entry in self.log],
                   "commit_index": self.commit_index,
                   "last_applied": self.last_applied, "state": self.state}
        with temporary.open("w") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)

    def request_vote(self, term: int, candidate: str) -> bool:
        if term < self.current_term:
            return False
        if term > self.current_term:
            self.current_term, self.voted_for = term, None
        if self.voted_for not in (None, candidate):
            self.persist()
            return False
        self.voted_for = candidate
        self.persist()
        return True

    def append_command(self, command: dict[str, str], term: int | None = None) -> Entry:
        entry = Entry(term or self.current_term, len(self.log) + 1, dict(command))
        self.log.append(entry)
        self.persist()
        return entry

    def commit_to(self, index: int) -> None:
        if index < self.commit_index or index > len(self.log):
            raise ValueError("commit index must advance within the log")
        self.commit_index = index
        while self.last_applied < self.commit_index:
            entry = self.log[self.last_applied]
            if set(entry.command) != {"key", "value"}:
                raise ValueError("unsupported command")
            self.state[entry.command["key"]] = entry.command["value"]
            self.last_applied += 1
        self.persist()

    def append_entries(self, *, term: int, prev_log_index: int,
                       prev_log_term: int, entries: list[Entry],
                       leader_commit: int) -> bool:
        if term < self.current_term:
            return False
        if term > self.current_term:
            self.current_term, self.voted_for = term, None
        if prev_log_index and (prev_log_index > len(self.log) or
                               self.log[prev_log_index - 1].term != prev_log_term):
            self.persist()
            return False
        for incoming in entries:
            position = incoming.index - 1
            if position < len(self.log) and self.log[position].term != incoming.term:
                if position < self.commit_index:
                    raise ValueError("cannot overwrite committed entry")
                del self.log[position:]
            if position >= len(self.log):
                self.log.append(incoming)
        target = min(leader_commit, len(self.log))
        if target > self.commit_index:
            self.commit_to(target)
        else:
            self.persist()
        return True
