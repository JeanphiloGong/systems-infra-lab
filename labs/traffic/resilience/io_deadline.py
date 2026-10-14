from __future__ import annotations

import json
import socket
from threading import Event, Thread
import time

from v2 import call


def experiment(budget_seconds: float = 0.05) -> dict[str, object]:
    if budget_seconds <= 0:
        raise ValueError("positive I/O budget required")
    stop = Event()
    accepted = Event()
    failures: list[str] = []
    attempts = 0
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(0.02)

        def serve() -> None:
            try:
                while not stop.is_set():
                    try:
                        peer, _ = listener.accept()
                    except socket.timeout:
                        continue
                    with peer:
                        accepted.set()
                        # Accept the connection but intentionally never send a reply.
                        stop.wait()
                    return
            except OSError as error:
                failures.append(type(error).__name__)

        worker = Thread(target=serve)
        worker.start()
        started = time.monotonic()
        expires = started + budget_seconds

        def remaining() -> float:
            seconds = expires - time.monotonic()
            if seconds <= 0:
                raise TimeoutError("absolute I/O deadline expired")
            return seconds

        def operation() -> bytes:
            nonlocal attempts
            attempts += 1
            with socket.socket() as client:
                # Set each native blocking operation's timeout from the SAME deadline.
                client.settimeout(remaining())
                client.connect(listener.getsockname())
                client.settimeout(remaining())
                return client.recv(1)

        try:
            try:
                call(operation, deadline=remaining(), base_delay=0.01)
            except TimeoutError:
                elapsed = time.monotonic() - started
            else:
                raise AssertionError("stalled server unexpectedly replied")
        finally:
            stop.set()
            worker.join(timeout=2)
        assert not worker.is_alive() and not failures
        assert accepted.is_set() and attempts == 1
        assert elapsed >= budget_seconds * 0.8
        return {"attempts": attempts, "timed_out": True, "elapsed_seconds": elapsed, "budget_seconds": budget_seconds, "thread_stopped": not worker.is_alive()}


if __name__ == "__main__":
    print(json.dumps(experiment()))
