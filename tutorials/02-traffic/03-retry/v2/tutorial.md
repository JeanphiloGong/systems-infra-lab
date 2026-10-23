# F03 v2：实际总耗时、指数退避与 jitter

此前只累加计划 sleep 的实现会漏算操作本身耗时和睡眠超调。本章恢复一个贯穿请求的 monotonic 截止点：开始时记录 expires，每次调用前、失败之后以及成功之后检查时钟。下一次退避会达到截止点时，立即报 TimeoutError，不再启动下一轮。

默认 sleeper 是 time.sleep，真实执行退避。测试替换 sleeper 时必须同时注入同一条时间轴上的 clock；只记录 delay 而不推进时间不能验证 deadline。指数延迟为 base_delay * 2**(attempt-1)，再加均匀 jitter。max_attempts 用尽抛最后的 RetryableError；时间耗尽抛 TimeoutError；PermanentError 原样传播。

## 同步操作的硬边界

普通 Python 同步调用不能被这里的时钟检查抢占。操作卡住，函数也会卡住；必须在网络/工具边界配置实际 I/O 超时或取消机制。操作返回但超过 deadline 时，本实现拒绝迟到成功，抛 TimeoutError。这不意味着副作用没发生，不能据此盲目重试。deadline 是后续尝试的准入与返回结果策略，不是任意代码的硬运行上限。

下面是完整 checkpoint；源码之后的检查既用推进的假钟覆盖操作耗时/超调，也用真实默认 sleep 验证实际等待。

将下面的完整代码保存为 `labs/traffic/resilience/v2.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/traffic/resilience/v2.py -->

```python
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar



class RetryableError(Exception):
    """A failure that may succeed on a later attempt."""


class PermanentError(Exception):
    """A failure that must be returned without retrying."""

T = TypeVar("T")


def call(
    operation: Callable[[], T],
    max_attempts: int = 3,
    deadline: float = 1.0,
    base_delay: float = 0.01,
    jitter: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[T, int]:
    if max_attempts < 1 or deadline < 0 or base_delay < 0 or jitter < 0:
        raise ValueError("invalid retry policy")
    source = rng or random
    expires = clock() + deadline
    for attempt in range(1, max_attempts + 1):
        if clock() >= expires:
            raise TimeoutError("retry deadline exceeded")
        try:
            result = operation()
        except PermanentError:
            raise
        except RetryableError:
            if clock() >= expires:
                raise TimeoutError("retry deadline exceeded")
            if attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + source.uniform(0, jitter)
            if clock() + delay >= expires:
                raise TimeoutError("retry deadline exceeded")
            sleep(delay)
        else:
            if clock() >= expires:
                raise TimeoutError("operation completed after deadline")
            return result, attempt
    raise AssertionError("unreachable")


if __name__ == "__main__":
    print(call(lambda: "ok", rng=random.Random(7)))
```

## 可执行检查

```bash
uv run python labs/traffic/resilience/v2.py
```

<details>
<summary>可选：参考分支验证</summary>

以下命令只在 [reference 的独立工作区](../../../../docs/reference-checks.md) 执行，依赖其中的测试或重放脚本；不属于 main 当前版本的必做步骤。

```bash
uv run python -m pytest tests/traffic/retry -q
```

</details>

下面的检查由测试从本文提取到空目录执行，依赖同样来自本文。每个模拟客户端使用固定但不同的种子，比较无 jitter 的同时到达与有 jitter 的分散到达。这是共同起点、独立客户端的确定性模拟，不是吞吐压测。

<!-- check: check_v2.py -->

```python
import random
import time
from v2 import call, RetryableError, PermanentError

class Clock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now
    def sleep(self, delay):
        self.now += delay

def expect(error, operation):
    try:
        operation()
    except error:
        return
    raise AssertionError(f"expected {error}")

clock = Clock()
calls = []
def slow_failure():
    calls.append(clock())
    clock.sleep(0.06)
    raise RetryableError()
expect(TimeoutError, lambda: call(slow_failure, deadline=0.02, clock=clock, sleep=clock.sleep))
assert len(calls) == 1

clock = Clock()
calls = []
def late_success():
    calls.append(clock())
    clock.sleep(0.06)
    return "late"
expect(TimeoutError, lambda: call(late_success, deadline=0.02, clock=clock, sleep=clock.sleep))
assert len(calls) == 1

clock = Clock()
calls = []
def failing():
    calls.append(clock())
    raise RetryableError()
def oversleep(delay):
    clock.sleep(delay + 1)
expect(TimeoutError, lambda: call(failing, deadline=0.5, base_delay=0.01, clock=clock, sleep=oversleep))
assert len(calls) == 1
expect(TimeoutError, lambda: call(failing, deadline=0, clock=clock, sleep=clock.sleep))
assert len(calls) == 1

real_calls = []
def real_fail():
    real_calls.append(time.monotonic())
    raise RetryableError()
start = time.monotonic()
expect(RetryableError, lambda: call(real_fail, max_attempts=3, deadline=2, base_delay=0.01))
assert len(real_calls) == 3 and time.monotonic() - start >= 0.03
assert real_calls[1] - real_calls[0] >= 0.01
assert real_calls[2] - real_calls[1] >= 0.02

def arrivals(jitter):
    records = []
    for client in range(8):
        clock = Clock()
        attempts = []
        def operation():
            attempts.append(clock())
            raise RetryableError()
        expect(RetryableError, lambda: call(operation, max_attempts=3,
               deadline=10, base_delay=0.1, jitter=jitter,
               rng=random.Random(100 + client), clock=clock, sleep=clock.sleep))
        records.append(attempts)
    return records
plain, spread = arrivals(0), arrivals(0.1)
assert spread == arrivals(0.1)
assert len({row[1] for row in plain}) == 1
assert len({row[1] for row in spread}) == 8
assert all(0.1 <= row[1] <= 0.2 and 0.3 <= row[2] <= 0.5 for row in spread)

clock = Clock()
def permanent():
    raise PermanentError()
expect(PermanentError, lambda: call(permanent, clock=clock, sleep=clock.sleep))
print({"without_jitter": plain, "seeded_jitter": spread})
```

## 端到端 I/O 截止：停滞的本地 socket

上面的策略不能抢占任意函数；下面补一个真实可取消等待的操作。只在 127.0.0.1 随机端口启动服务器，接受连接后不发响应。客户端 connect 和 recv 每次阻塞前都从同一个绝对 expires 计算剩余时间，直接传给 socket.settimeout，不加通用适配器。call 得到的是剩余总预算，不是每次操作重新拥有完整 50ms。

socket 超时是 TimeoutError，直接穿透重试循环，所以停滞请求只调用一次。这里没有重试等待；前面的假钟与真实 sleep 检查已经覆盖退避占用总预算。若业务加入可重试错误，闭包的 expires 仍不重置，下一次操作只能使用真实剩余预算。

finally 通知服务器退出，join 确认线程结束；listener、peer、client 都由上下文关闭。实验没有外部网络请求或后台遗留服务。操作用系统 I/O 超时约束等待；操作系统调度仍可能让实际返回略晚于 50ms，因此这不是硬实时保证，更不是任意 Python 函数的强制终止。不要把宽松 CI 墙钟上限解读成精确截止误差。

将下面的完整代码保存为 `labs/traffic/resilience/io_deadline.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/traffic/resilience/io_deadline.py -->

```python
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
```

```bash
uv run python labs/traffic/resilience/io_deadline.py
```

预期 attempts=1、timed_out=true、thread_stopped=true，elapsed_seconds 接近 budget_seconds。测试从本章提取 v2.py 与 io_deadline.py，在子进程实测并检查宽松调度上限，避免把无界停滞伪装成成功。

